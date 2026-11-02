"""
Reviews Router — Fake Review Detection (Live + Individual Scan)
"""
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import get_db
from db_models import ReviewModel, ReviewAnalysisModel, ReviewAlertModel

router = APIRouter()


# ── Synthetic review generator (used for initial seeding) ────────────────────

def generate_synthetic_reviews(count=1000):
    normal_texts = [
        "Good product, works as described. Delivery was on time.",
        "Decent quality for the price. Would consider buying again.",
        "Works well, nothing extraordinary but does the job fine.",
        "Satisfied with purchase. Packaging was good, arrived safely.",
        "Nice quality overall. Minor issue with sizing but manageable.",
    ]
    fake_texts = [
        "Best best best!!! Everyone should buy this immediately!!!",
        "AMAZING DEAL! Buy now!!! Limited time offer!",
        "Cheap cheap cheap!!! Such a bargain, can't believe the price!!!",
        "UNBELIEVABLE QUALITY!!! Totally worth it, buy now!!!",
        "MUST BUY!!! Telling all friends and family to get this!!!",
    ]
    spam_texts = [
        "Click link in bio for 50% discount code now!",
        "Win a gift card at our website! Limited time offer!",
        "Free money here! Register now to claim your reward!",
        "Discount here: bit.ly/fakeoffer — sign up today!",
        "Get paid to write reviews! DM us for easy money!",
    ]
    bot_text = "This is a great product, I recommend it to everyone."
    company_texts = [
        "Our product is the best! Superior to all competitors!",
        "Industry leading performance, nothing comes close to this!",
        "Company certified excellence! Award winning product here!",
        "Number one brand in the world, no competition whatsoever!",
        "Trust our brand! Hundreds of verified happy customers daily!",
    ]

    reviews = []
    for i in range(count):
        user_id = f"USR_{random.randint(1, 1000):06d}"
        product_id = f"PROD_{random.randint(1, 500):05d}"
        rating = random.randint(1, 5)
        type_choice = random.choices(
            ["NORMAL", "FAKE", "SPAM", "BOT", "COMPANY_FAKE"],
            weights=[55, 15, 12, 10, 8]
        )[0]
        if type_choice == "NORMAL":
            text = random.choice(normal_texts)
        elif type_choice == "FAKE":
            text = random.choice(fake_texts)
        elif type_choice == "SPAM":
            text = random.choice(spam_texts)
        elif type_choice == "BOT":
            text = bot_text
        else:
            text = random.choice(company_texts)

        reviews.append(ReviewModel(
            user_id=user_id,
            product_id=product_id,
            review_text=text,
            rating=rating,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        ))
    return reviews


# ── Shared classify helper ────────────────────────────────────────────────────

def _classify(text: str, text_counts: dict) -> dict:
    tl = text.strip().lower()

    if text_counts.get(tl, 0) > 3:
        return dict(status="BOT", score=round(random.uniform(88.0, 99.0), 2),
                    reason=f"Identical text posted {text_counts[tl]}× — mass bot activity",
                    detail="Automated bot reviewer posting identical reviews across many products")

    spam_kw = ["link", "bit.ly", "click link", "free money", "gift card",
               "discount here", "offer now", "earn $", "get paid",
               "promo code", "win a", "register now"]
    hits = [k for k in spam_kw if k in tl]
    if hits:
        return dict(status="SPAM", score=round(random.uniform(78.0, 95.0), 2),
                    reason=f"Spam signals: {', '.join(hits[:3])}",
                    detail="Spam campaign — external links or promotional solicitations detected")

    company_kw = ["best best", "buy now", "number one brand", "amazing deal",
                  "unbelievable quality", "our product", "company certified",
                  "industry leading", "superior to", "award winning",
                  "exclusive deal", "trust our brand", "verified happy"]
    chits = [k for k in company_kw if k in tl]
    if chits or (text.count("!") > 4 and any(w in tl for w in ["best", "buy", "amazing", "deal"])):
        return dict(status="COMPANY_FAKE", score=round(random.uniform(72.0, 92.0), 2),
                    reason=f"Brand-manipulation: {', '.join(chits[:2]) if chits else 'excessive promotional language'}",
                    detail="Company-planted fake review — written by brand to inflate ratings or bash rivals")

    fake_kw = ["cheap cheap", "love love", "must buy", "incredible deal",
               "totally changed", "mind blowing", "cannot believe"]
    fhits = [k for k in fake_kw if k in tl]
    excl = text.count("!")
    if fhits or excl > 2:
        enthusiasm = ', '.join(fhits[:2]) if fhits else f'{excl} exclamation marks'
        return dict(status="FAKE", score=round(random.uniform(62.0, 88.0), 2),
                    reason=f"Unnatural enthusiasm: {enthusiasm}",
                    detail="Paid or incentivised fake review — manufactured sentiment patterns detected")

    return dict(status="NORMAL", score=round(random.uniform(4.0, 22.0), 2),
                reason="No suspicious signals detected",
                detail="Genuine customer review — language consistent with authentic feedback")


# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/live")
async def get_live_review_alerts(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str = Query(None, description="Filter: BOT, COMPANY_FAKE, SPAM, FAKE"),
    min_score: float = Query(0.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Live-polled review alerts — newest first (mirrors /api/alerts/ pattern)."""
    q = select(ReviewAlertModel).order_by(ReviewAlertModel.created_at.desc())
    if status:
        q = q.where(ReviewAlertModel.status == status.upper())
    if min_score > 0:
        q = q.where(ReviewAlertModel.risk_score >= min_score)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    alerts = result.scalars().all()

    return [
        {
            "id": a.id,
            "review_id": a.review_id,
            "user_id": a.user_id,
            "product_id": a.product_id,
            "review_text": a.review_text,
            "risk_score": a.risk_score,
            "status": a.status,
            "reason": a.reason,
            "detail": a.detail,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@router.get("/live/summary")
async def get_live_review_summary(db: AsyncSession = Depends(get_db)):
    """Summary counts for the Review Analyzer header cards."""
    total    = (await db.execute(select(func.count(ReviewAlertModel.id)))).scalar() or 0
    bot      = (await db.execute(select(func.count(ReviewAlertModel.id)).where(ReviewAlertModel.status == "BOT"))).scalar() or 0
    company  = (await db.execute(select(func.count(ReviewAlertModel.id)).where(ReviewAlertModel.status == "COMPANY_FAKE"))).scalar() or 0
    spam     = (await db.execute(select(func.count(ReviewAlertModel.id)).where(ReviewAlertModel.status == "SPAM"))).scalar() or 0
    fake     = (await db.execute(select(func.count(ReviewAlertModel.id)).where(ReviewAlertModel.status == "FAKE"))).scalar() or 0
    return {"total": total, "bot": bot, "company_fake": company, "spam": spam, "fake": fake}


@router.patch("/live/{alert_id}/resolve")
async def resolve_review_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a review alert as resolved."""
    result = await db.execute(select(ReviewAlertModel).where(ReviewAlertModel.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        return {"error": "Alert not found"}
    alert.is_resolved = True
    await db.commit()
    return {"status": "resolved", "id": alert_id}


@router.post("/scan/{review_id}")
async def scan_single_review(review_id: int, db: AsyncSession = Depends(get_db)):
    """Individually scan a specific review by ID."""
    result = await db.execute(select(ReviewModel).where(ReviewModel.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        return {"error": "Review not found"}

    # Simple text count for this single scan
    sample = await db.execute(select(ReviewModel.review_text).limit(300))
    text_counts: dict = {}
    for t in sample.scalars().all():
        k = t.strip().lower()
        text_counts[k] = text_counts.get(k, 0) + 1

    res = _classify(review.review_text, text_counts)

    # Upsert analysis record
    db.add(ReviewAnalysisModel(
        review_id=review.id,
        risk_score=res["score"],
        status=res["status"],
        created_at=datetime.utcnow(),
    ))

    if res["status"] != "NORMAL":
        db.add(ReviewAlertModel(
            review_id=review.id,
            user_id=review.user_id or "UNKNOWN",
            product_id=review.product_id or "UNKNOWN",
            review_text=review.review_text,
            risk_score=res["score"],
            status=res["status"],
            reason=res["reason"],
            detail=res["detail"],
            is_resolved=False,
            created_at=datetime.utcnow(),
        ))

    await db.commit()
    return {
        "review_id": review_id,
        "status": res["status"],
        "risk_score": res["score"],
        "reason": res["reason"],
        "detail": res["detail"],
    }


@router.post("/scan")
async def scan_all_reviews(db: AsyncSession = Depends(get_db)):
    """Full dataset scan (legacy button — kept for compatibility)."""
    from sqlalchemy import delete
    await db.execute(delete(ReviewAnalysisModel))

    result = await db.execute(select(func.count(ReviewModel.id)))
    count = result.scalar() or 0
    if count == 0:
        reviews = generate_synthetic_reviews(1000)
        db.add_all(reviews)
        await db.flush()

    stmt = select(ReviewModel)
    reviews_result = await db.execute(stmt)
    all_reviews = reviews_result.scalars().all()

    text_counts: dict = {}
    for r in all_reviews:
        t = r.review_text.strip().lower()
        text_counts[t] = text_counts.get(t, 0) + 1

    analysis_records = []
    for r in all_reviews:
        res = _classify(r.review_text, text_counts)
        analysis_records.append(ReviewAnalysisModel(
            review_id=r.id,
            risk_score=res["score"],
            status=res["status"]
        ))
    db.add_all(analysis_records)
    await db.commit()
    return {"message": f"Scanned {len(all_reviews)} reviews."}


@router.get("/analyzed")
async def get_analyzed_reviews(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ReviewAnalysisModel, ReviewModel)
        .join(ReviewModel, ReviewAnalysisModel.review_id == ReviewModel.id)
        .order_by(desc(ReviewAnalysisModel.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "review_id": row.ReviewModel.id,
            "user_id": row.ReviewModel.user_id,
            "product_id": row.ReviewModel.product_id,
            "risk_score": row.ReviewAnalysisModel.risk_score,
            "status": row.ReviewAnalysisModel.status,
            "text_preview": row.ReviewModel.review_text[:100] + "..." if len(row.ReviewModel.review_text) > 100 else row.ReviewModel.review_text
        }
        for row in rows
    ]


@router.get("/stats")
async def get_review_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(ReviewAnalysisModel))).scalar() or 0
    fake  = (await db.execute(select(func.count()).select_from(ReviewAnalysisModel).where(ReviewAnalysisModel.status == 'FAKE'))).scalar() or 0
    spam  = (await db.execute(select(func.count()).select_from(ReviewAnalysisModel).where(ReviewAnalysisModel.status == 'SPAM'))).scalar() or 0
    bot   = (await db.execute(select(func.count()).select_from(ReviewAnalysisModel).where(ReviewAnalysisModel.status == 'BOT'))).scalar() or 0
    cfake = (await db.execute(select(func.count()).select_from(ReviewAnalysisModel).where(ReviewAnalysisModel.status == 'COMPANY_FAKE'))).scalar() or 0
    return {"total_reviews": total, "fake_reviews": fake, "spam_reviews": spam, "bot_reviews": bot, "company_fake_reviews": cfake}
