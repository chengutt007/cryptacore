"""
Crypta Core AI — FastAPI Application Entry Point
"""
import sys
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

# Add ml/ to sys.path for model imports
ML_PATH = Path(__file__).parent.parent / "ml"
sys.path.insert(0, str(ML_PATH))

from database import engine, Base, AsyncSessionLocal
from db_models import UserModel
from routers import reviews, returns, users, payments, dashboard, pricing, alerts
from config import settings
from risk_score import analyze_user_risk
import fraud_scanner
import review_scanner

# ──────────────────────────────────────────────
# Model registry (loaded once at startup)
# ──────────────────────────────────────────────
from models_registry import ModelRegistry
registry = ModelRegistry()


async def seed_users_from_dataset():
    """Seed users and related data from synthetic dataset"""
    import random
    from datetime import datetime, timedelta
    from db_models import LoginHistoryModel, DeviceHistoryModel, OrderModel, ReturnedItemModel
    
    data_dir = Path(__file__).parent.parent / "ml" / "training_data"
    behavior_file = data_dir / "live_users.csv"   # production users — different seed from training data
    
    if not behavior_file.exists():
        print("[WARN] User behavior dataset not found, skipping seed")
        return 0
    
    df = pd.read_csv(behavior_file)
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(UserModel))
        if existing.scalars().first():
            print(f"[*] Users already seeded.")
            return 0
        
        users_created = 0
        print("[*] Seeding database with granular user data...")
        
        for idx, row in df.iterrows():
            user_id = f"USR_{idx:06d}"
            user = UserModel(
                user_id=user_id,
                email=f"user_{idx}@example.com",
                account_age_days=int(row.get("account_age_days", 365)),
                total_orders=random.randint(5, 100),
                total_returns=int(row.get("total_returns", 0)),
                total_refunded_amount=float(row.get("refund_total_amount", 0)),
                total_discount_amount=random.uniform(10, 500),
                promo_abuse_count=int(row.get("promo_abuse_count", 0)),
                ip_changes_30d=int(row.get("ip_changes_30d", 0)),
                device_changes_30d=int(row.get("device_changes_30d", 0)),
                login_frequency_per_day=float(row.get("login_frequency_per_day", 1.0)),
                crypta_risk_score=0.0,
                risk_level="LOW",
                is_flagged=False,
            )
            session.add(user)
            
            # Seed Logins
            num_logins = min(10, int(user.login_frequency_per_day * 7))
            for l_idx in range(num_logins):
                login = LoginHistoryModel(
                    user_id=user_id,
                    login_time=datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
                    ip_address=f"192.168.1.{random.randint(1, 254)}",
                    device_id=f"DEV_{idx:04d}_{random.randint(1, 3)}",
                    location=random.choice(["New York, USA", "London, UK", "Tokyo, JP", "Berlin, DE", "Mumbai, IN"]),
                    is_suspicious=(user.ip_changes_30d > 5)
                )
                session.add(login)
            
            # Seed Devices
            num_devices = max(1, user.device_changes_30d // 2)
            for d_idx in range(num_devices):
                device = DeviceHistoryModel(
                    user_id=user_id,
                    device_id=f"DEV_{idx:04d}_{d_idx}",
                    device_type=random.choice(["mobile", "desktop", "tablet"]),
                    os=random.choice(["iOS", "Android", "macOS", "Windows", "Linux"]),
                    browser=random.choice(["Chrome", "Safari", "Firefox", "Edge"]),
                    last_used=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    is_new_device=(d_idx > 0)
                )
                session.add(device)
            
            # Seed Orders
            num_orders = min(15, user.total_orders)
            for o_idx in range(num_orders):
                order_id = f"ORD_{idx:04d}_{o_idx}"
                order = OrderModel(
                    order_id=order_id,
                    user_id=user_id,
                    amount=random.uniform(20, 1000),
                    fraud_risk_score=random.uniform(0, 40) if user.crypta_risk_score < 50 else random.uniform(30, 95),
                    is_returned=(o_idx < user.total_returns),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))
                )
                session.add(order)
                
                # Seed Returns
                if order.is_returned:
                    ret = ReturnedItemModel(
                        return_id=f"RET_{idx:04d}_{o_idx}",
                        order_item_id=random.randint(1000, 9999), # Mock ID
                        product_id=f"PROD_{random.randint(0, 299):05d}",
                        user_id=user_id,
                        order_id=order_id,
                        return_reason=random.choice(["Size too small", "Damaged on arrival", "Changed mind", "Better price found"]),
                        item_condition="GOOD" if random.random() > 0.1 else "DAMAGED",
                        refund_amount=order.amount * 0.9,
                        created_at=order.created_at + timedelta(days=random.randint(1, 14))
                    )
                    session.add(ret)

            users_created += 1
            if users_created % 200 == 0:
                await session.flush()
        
        await session.commit()
        return users_created


async def seed_reviews_if_empty():
    from routers.reviews import generate_synthetic_reviews
    from db_models import ReviewModel
    from sqlalchemy import select, func
    async with AsyncSessionLocal() as session:
        count = await session.execute(select(func.count(ReviewModel.id)))
        if count.scalar() == 0:
            print("[*] Seeding 1000 reviews...")
            reviews = generate_synthetic_reviews(1000)
            session.add_all(reviews)
            await session.commit()
            print("[OK] Reviews seeded")

async def analyze_all_users_startup():
    """Analyze all users at startup using centralized risk logic"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel.user_id))
            user_ids = result.scalars().all()
            
        if not user_ids:
            print("[WARN] No users to analyze")
            return
            
        print(f"[*] Analyzing {len(user_ids)} users in the background...")
        
        flagged_count = 0
        for uid in user_ids:
            async with AsyncSessionLocal() as session:
                risk = await analyze_user_risk(uid, registry, session)
                if risk and risk.get("crypta_risk_score", 0) >= 70:
                    flagged_count += 1
                await session.commit()
            await asyncio.sleep(0.01)  # Yield to event loop to avoid locking
            
        print(f"[OK] Analysis complete: {flagged_count} flagged users")
    except Exception as e:
        print(f"[ERROR] Background analysis failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables + load ML models + seed users + analyze
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    registry.load_all()
    
    # Seed users from dataset
    seeded = await seed_users_from_dataset()
    if seeded > 0:
        print(f"[OK] Seeded {seeded} users from dataset")
    
    # Seed reviews
    await seed_reviews_if_empty()
    
    # Analyze all users in the background
    asyncio.create_task(analyze_all_users_startup())
    
    # Start background fraud scanner (runs every 3 seconds)
    scanner_task = asyncio.create_task(fraud_scanner.run_scanner())
    print("[OK] Background fraud scanner started")

    # Start background review scanner (runs every 3 seconds, 3-5 reviews/cycle)
    review_scanner_task = asyncio.create_task(review_scanner.run_review_scanner())
    print("[OK] Background review scanner started")
    
    print("[OK] Crypta Core AI backend ready")
    yield
    # Shutdown: cancel scanners gracefully
    scanner_task.cancel()
    review_scanner_task.cancel()
    for t in (scanner_task, review_scanner_task):
        try:
            await t
        except asyncio.CancelledError:
            pass
    await engine.dispose()


app = FastAPI(
    title="Crypta Core AI",
    description="AI-powered fraud detection for e-commerce",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose registry to routers via app state
app.state.registry = registry

# Mount routers
app.include_router(reviews.router, prefix="/api/reviews", tags=["Fake Review Detection"])
app.include_router(returns.router, prefix="/api/returns", tags=["Return Fraud"])
app.include_router(users.router, prefix="/api/users", tags=["User Risk"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payment Fraud"])
app.include_router(pricing.router, prefix="/api/pricing", tags=["Pricing & Inventory Intelligence"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Fraud Alerts"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Crypta Core AI",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "models_loaded": registry.is_ready()}
