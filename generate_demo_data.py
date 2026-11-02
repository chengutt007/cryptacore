"""
Large Demo Dataset Generator for Crypta Core AI
Generates: 800 users, 4000 orders, 500+ returns, logins, devices
Includes 30+ high-risk users with realistic fraud patterns.

Usage:
  python generate_demo_data.py
"""
import asyncio
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add backend to path
BACKEND = Path(__file__).parent / "cryptacoreAi" / "backend"
if not BACKEND.exists():
    # Also try direct sibling
    BACKEND = Path(__file__).parent / "backend"
if not BACKEND.exists():
    BACKEND = Path(__file__).parent
print(f"[*] Using backend path: {BACKEND}")
sys.path.insert(0, str(BACKEND))
import os
os.chdir(str(BACKEND))  # ensure relative DB paths resolve correctly

from database import engine, Base, AsyncSessionLocal
from db_models import (
    UserModel, OrderModel, ReturnedItemModel,
    LoginHistoryModel, DeviceHistoryModel, FraudAlertModel,
    FlaggedUsersModel
)
from sqlalchemy import select, delete

# ─── Config ──────────────────────────────────────────────────────────────────
NUM_USERS          = 800
NUM_ORDERS         = 4000        # ~5 orders per user on average
NUM_RETURNS_TARGET = 500         # minimum returns
NUM_HIGH_RISK      = 30          # users specifically crafted as high-risk

LOCATIONS = ["New York, USA", "London, UK", "Tokyo, JP", "Berlin, DE",
             "Mumbai, IN", "Sydney, AU", "Toronto, CA", "Dubai, UAE",
             "Singapore, SG", "Paris, FR"]

DEVICE_TYPES   = ["mobile", "desktop", "tablet"]
OS_LIST        = ["iOS", "Android", "macOS", "Windows", "Linux"]
BROWSERS       = ["Chrome", "Safari", "Firefox", "Edge", "Brave"]

RETURN_REASONS = [
    "Size too small", "Damaged on arrival", "Changed mind",
    "Better price found", "Wrong item delivered", "Not as described",
    "Quality not as expected", "Duplicate purchase",
]

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "crypto", "bank_transfer"]

# ─── Fraud pattern helpers ────────────────────────────────────────────────────

def high_risk_profile(i: int) -> dict:
    """Return user-level stats for a high-risk synthetic user."""
    pattern = i % 5
    now = datetime.utcnow()
    if pattern == 0:
        # Extreme return abuser
        return dict(account_age_days=random.randint(30, 90), orders=random.randint(40, 80),
                    returns_pct=random.uniform(0.75, 0.95), logins_per_day=random.uniform(1, 3),
                    ip_changes=random.randint(1, 4), device_changes=random.randint(1, 3),
                    promo_abuse=random.randint(0, 2), discount=random.uniform(50, 300))
    elif pattern == 1:
        # Login bomber / suspicious behavior
        return dict(account_age_days=random.randint(10, 45), orders=random.randint(10, 25),
                    returns_pct=random.uniform(0.2, 0.5), logins_per_day=random.uniform(20, 60),
                    ip_changes=random.randint(10, 25), device_changes=random.randint(5, 12),
                    promo_abuse=random.randint(3, 8), discount=random.uniform(100, 500))
    elif pattern == 2:
        # New account + bulk orders (fraud ring)
        return dict(account_age_days=random.randint(3, 15), orders=random.randint(50, 100),
                    returns_pct=random.uniform(0.6, 0.9), logins_per_day=random.uniform(5, 15),
                    ip_changes=random.randint(5, 15), device_changes=random.randint(3, 8),
                    promo_abuse=random.randint(5, 15), discount=random.uniform(200, 800))
    elif pattern == 3:
        # Refund abuser with many disputes
        return dict(account_age_days=random.randint(60, 200), orders=random.randint(30, 60),
                    returns_pct=random.uniform(0.7, 0.85), logins_per_day=random.uniform(2, 8),
                    ip_changes=random.randint(3, 10), device_changes=random.randint(2, 6),
                    promo_abuse=random.randint(5, 12), discount=random.uniform(300, 1000))
    else:
        # VPN / geo-hopper
        return dict(account_age_days=random.randint(20, 60), orders=random.randint(15, 40),
                    returns_pct=random.uniform(0.4, 0.7), logins_per_day=random.uniform(8, 25),
                    ip_changes=random.randint(15, 30), device_changes=random.randint(4, 10),
                    promo_abuse=random.randint(2, 6), discount=random.uniform(100, 400))


def normal_profile() -> dict:
    """Return user-level stats for a normal synthetic user."""
    r = random.random()
    if r < 0.6:
        # Low-risk buyer
        return dict(account_age_days=random.randint(180, 1800), orders=random.randint(3, 20),
                    returns_pct=random.uniform(0.0, 0.15), logins_per_day=random.uniform(0.1, 1.5),
                    ip_changes=random.randint(0, 2), device_changes=random.randint(0, 1),
                    promo_abuse=0, discount=random.uniform(0, 100))
    elif r < 0.85:
        # Medium risk
        return dict(account_age_days=random.randint(60, 365), orders=random.randint(10, 40),
                    returns_pct=random.uniform(0.1, 0.35), logins_per_day=random.uniform(1, 5),
                    ip_changes=random.randint(1, 5), device_changes=random.randint(0, 3),
                    promo_abuse=random.randint(0, 2), discount=random.uniform(10, 200))
    else:
        # Borderline
        return dict(account_age_days=random.randint(30, 120), orders=random.randint(20, 50),
                    returns_pct=random.uniform(0.3, 0.55), logins_per_day=random.uniform(3, 10),
                    ip_changes=random.randint(3, 8), device_changes=random.randint(2, 5),
                    promo_abuse=random.randint(1, 4), discount=random.uniform(50, 300))


# ─── Main seeder ─────────────────────────────────────────────────────────────

async def wipe_existing():
    async with AsyncSessionLocal() as s:
        for Model in [FraudAlertModel, FlaggedUsersModel, ReturnedItemModel,
                      LoginHistoryModel, DeviceHistoryModel, OrderModel, UserModel]:
            await s.execute(delete(Model))
        await s.commit()
    print("[OK] Wiped existing data")


async def generate():
    now = datetime.utcnow()

    users_data   = []
    orders_data  = []
    returns_data = []
    logins_data  = []
    devices_data = []

    # ── Mark first NUM_HIGH_RISK users as high-risk ──────────────────────────
    high_risk_ids = set(range(0, NUM_HIGH_RISK))  # indices 0..29

    total_returns_generated = 0

    # Pre-generate base IPs for ip-change simulation
    def rand_ip():
        return f"{random.randint(10,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    order_counter = 0   # global order index for distributing 4000 orders

    for i in range(NUM_USERS):
        user_id = f"USR_{i+1:04d}"
        is_high = i in high_risk_ids
        p = high_risk_profile(i) if is_high else normal_profile()

        created_at = now - timedelta(days=p["account_age_days"] + random.randint(0, 30))

        total_orders_for_user = max(1, int(p["orders"]))

        # Distribute 4000 orders proportionally, minimum 1 per user
        # We spread more orders to high-risk users
        orders_alloc = max(1, min(
            int(4000 * total_orders_for_user / max(
                sum(high_risk_profile(j)["orders"] if j in high_risk_ids else normal_profile()["orders"]
                    for j in range(NUM_USERS)) / 4000, 1)),
            total_orders_for_user
        ))

        returns_for_user = int(total_orders_for_user * p["returns_pct"])

        total_refunded = 0.0
        user_orders = []

        # Orders
        for o_idx in range(total_orders_for_user):
            order_id = f"ORD_{i+1:04d}_{o_idx:03d}"
            is_ret = o_idx < returns_for_user
            amount = round(random.uniform(20, 800), 2)
            fraud_score = random.uniform(60, 98) if is_high else random.uniform(0, 40)

            o_created = created_at + timedelta(
                days=random.randint(0, max(1, p["account_age_days"] - 5)),
                hours=random.randint(0, 23)
            )
            orders_data.append({
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "discount_amount": round(random.uniform(0, 50), 2),
                "promo_code": f"PROMO{random.randint(1,10)}" if random.random() < 0.3 else None,
                "payment_method": random.choice(PAYMENT_METHODS),
                "is_returned": is_ret,
                "fraud_risk_score": round(fraud_score, 1),
                "payment_fraud_score": round(random.uniform(0, 30), 1),
                "pricing_fraud_score": round(random.uniform(0, 20), 1),
                "is_suspicious": fraud_score >= 70,
                "created_at": o_created,
            })
            user_orders.append((order_id, amount, o_created, is_ret))

        # Returns
        returned_orders = user_orders[:returns_for_user]
        for r_idx, (order_id, amount, o_created, _) in enumerate(returned_orders):
            days_to_ret = random.randint(1, 30)
            refund_amt = round(amount * random.uniform(0.7, 1.0), 2)
            total_refunded += refund_amt
            returns_data.append({
                "return_id": f"RET_{i+1:04d}_{r_idx:03d}",
                "order_item_id": random.randint(1000, 99999),
                "product_id": f"PROD_{random.randint(0, 299):05d}",
                "user_id": user_id,
                "order_id": order_id,
                "return_reason": random.choice(RETURN_REASONS),
                "item_condition": random.choices(
                    ["GOOD", "DAMAGED", "MISSING_PARTS"],
                    weights=[0.6, 0.3, 0.1] if is_high else [0.85, 0.1, 0.05]
                )[0],
                "refund_amount": refund_amt,
                "restocking_flag": True,
                "days_to_return": days_to_ret,
                "created_at": o_created + timedelta(days=days_to_ret),
                "processed_at": o_created + timedelta(days=days_to_ret + 1),
            })
            total_returns_generated += 1

        # Logins
        base_ip = rand_ip()
        num_logins = max(1, int(p["logins_per_day"] * min(p["account_age_days"], 30)))
        num_logins = min(num_logins, 80)  # cap per user for DB size

        seen_ips = [base_ip]
        for l_idx in range(num_logins):
            # High-risk users switch IPs more
            if is_high and l_idx % max(1, num_logins // max(1, p["ip_changes"])) == 0:
                base_ip = rand_ip()
                seen_ips.append(base_ip)

            logins_data.append({
                "user_id": user_id,
                "login_time": now - timedelta(
                    hours=random.randint(1, min(p["account_age_days"] * 24, 8760))
                ),
                "ip_address": base_ip,
                "device_id": f"DEV_{i+1:04d}_{random.randint(1, max(1, p['device_changes']))}",
                "location": random.choice(LOCATIONS) if is_high else random.choices(
                    LOCATIONS, weights=[5, 2, 1, 1, 1, 1, 1, 1, 1, 1]
                )[0],
                "is_suspicious": is_high and (len(seen_ips) > 3),
            })

        # Devices
        num_devices = max(1, int(p["device_changes"]) + 1)
        for d_idx in range(num_devices):
            devices_data.append({
                "user_id": user_id,
                "device_id": f"DEV_{i+1:04d}_{d_idx}",
                "device_type": random.choice(DEVICE_TYPES),
                "os": random.choice(OS_LIST),
                "browser": random.choice(BROWSERS),
                "last_used": now - timedelta(days=random.randint(0, min(30, p["account_age_days"]))),
                "is_new_device": (d_idx > 0),
            })

        users_data.append({
            "user_id": user_id,
            "email": f"user_{i+1}@demo.cryptacore.ai",
            "account_age_days": p["account_age_days"],
            "total_orders": total_orders_for_user,
            "total_returns": returns_for_user,
            "total_refunded_amount": round(total_refunded, 2),
            "total_discount_amount": round(p["discount"], 2),
            "promo_abuse_count": p["promo_abuse"],
            "ip_changes_30d": min(len(seen_ips) - 1, p["ip_changes"]),
            "device_changes_30d": max(0, num_devices - 1),
            "login_frequency_per_day": round(p["logins_per_day"], 3),
            "crypta_risk_score": 0.0,
            "risk_level": "LOW",
            "is_flagged": False,
            "created_at": created_at,
            "last_analyzed": now,
        })

    # ── Extra passes to hit 4000 orders ─────────────────────────────────────
    while len(orders_data) < NUM_ORDERS:
        i = random.randint(0, NUM_USERS - 1)
        user_id = f"USR_{i+1:04d}"
        extra_idx = len(orders_data)
        amount = round(random.uniform(20, 600), 2)
        orders_data.append({
            "order_id": f"ORD_X{extra_idx:06d}",
            "user_id": user_id,
            "amount": amount,
            "discount_amount": 0.0,
            "promo_code": None,
            "payment_method": random.choice(PAYMENT_METHODS),
            "is_returned": False,
            "fraud_risk_score": round(random.uniform(0, 50), 1),
            "payment_fraud_score": 0.0,
            "pricing_fraud_score": 0.0,
            "is_suspicious": False,
            "created_at": now - timedelta(days=random.randint(0, 180)),
        })

    print(f"[*] Users: {len(users_data)}, Orders: {len(orders_data)}, "
          f"Returns: {len(returns_data)}, Logins: {len(logins_data)}, Devices: {len(devices_data)}")

    return users_data, orders_data, returns_data, logins_data, devices_data


async def commit_batch(session, models, batch_size=500):
    for i in range(0, len(models), batch_size):
        for m in models[i:i+batch_size]:
            session.add(m)
        await session.flush()
    await session.commit()


async def seed_all():
    print("[*] Creating DB tables if not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("[*] Wiping old data...")
    await wipe_existing()

    print("[*] Generating synthetic data...")
    users_data, orders_data, returns_data, logins_data, devices_data = await generate()

    async with AsyncSessionLocal() as s:
        print("[*] Inserting users...")
        user_models = [UserModel(**u) for u in users_data]
        await commit_batch(s, user_models)

        print("[*] Inserting orders...")
        order_models = [OrderModel(**o) for o in orders_data]
        await commit_batch(s, order_models)

        print("[*] Inserting returns...")
        return_models = [ReturnedItemModel(**r) for r in returns_data]
        await commit_batch(s, return_models)

        print("[*] Inserting logins...")
        login_models = [LoginHistoryModel(**l) for l in logins_data]
        await commit_batch(s, login_models)

        print("[*] Inserting devices...")
        device_models = [DeviceHistoryModel(**d) for d in devices_data]
        await commit_batch(s, device_models)

    print(f"[OK] Seeded {len(users_data)} users, {len(orders_data)} orders, "
          f"{len(returns_data)} returns, {len(logins_data)} logins, {len(devices_data)} devices")
    print(f"[OK] High-risk users: USR_0001 to USR_{NUM_HIGH_RISK:04d}")


if __name__ == "__main__":
    asyncio.run(seed_all())
