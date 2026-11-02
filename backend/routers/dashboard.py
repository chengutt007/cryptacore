"""
Dashboard Router — Summary stats and suspicious orders
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database import get_db
from db_models import UserModel, ReviewModel, OrderModel, FraudAlertModel, ReviewAnalysisModel

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    total_users = (await db.execute(func.count(UserModel.id).select())).scalar() or 0
    flagged_users = (await db.execute(
        select(func.count(UserModel.id)).where(UserModel.crypta_risk_score >= 70)
    )).scalar() or 0

    total_reviews = (await db.execute(func.count(ReviewAnalysisModel.id).select())).scalar() or 0
    fake_reviews = (await db.execute(
        select(func.count(ReviewAnalysisModel.id)).where(ReviewAnalysisModel.status == "FAKE")
    )).scalar() or 0

    total_orders = (await db.execute(func.count(OrderModel.id).select())).scalar() or 0
    suspicious_orders = (await db.execute(
        select(func.count(OrderModel.id)).where(OrderModel.fraud_risk_score >= 70)
    )).scalar() or 0

    avg_risk_result = await db.execute(select(func.avg(UserModel.crypta_risk_score)))
    avg_risk = float(avg_risk_result.scalar() or 0)

    alerts_today = (await db.execute(
        select(func.count(FraudAlertModel.id))
        .where(FraudAlertModel.created_at >= today_start)
    )).scalar() or 0

    # Fraud type breakdown
    fraud_counts = {}
    for fraud_type in ["FAKE_REVIEW", "RETURN_FRAUD", "SUSPICIOUS_BEHAVIOR", "PAYMENT_FRAUD", "PRICING_ANOMALY", "INVENTORY_MISMATCH"]:
        count = (await db.execute(
            select(func.count(FraudAlertModel.id))
            .where(FraudAlertModel.fraud_type == fraud_type)
        )).scalar() or 0
        fraud_counts[fraud_type] = count

    return {
        "total_users_analyzed": total_users,
        "flagged_users": flagged_users,
        "total_reviews_analyzed": total_reviews,
        "fake_reviews_detected": fake_reviews,
        "total_orders_analyzed": total_orders,
        "suspicious_orders": suspicious_orders,
        "avg_crypta_risk_score": round(avg_risk, 1),
        "alerts_today": alerts_today,
        "fraud_breakdown": fraud_counts,
    }


@router.get("/orders/suspicious")
async def get_suspicious_orders(
    limit: int = 50,
    min_score: float = 55.0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OrderModel)
        .where(OrderModel.fraud_risk_score >= min_score)
        .order_by(OrderModel.fraud_risk_score.desc())
        .limit(limit)
    )
    orders = result.scalars().all()
    return [
        {
            "order_id": o.order_id,
            "user_id": o.user_id,
            "amount": o.amount,
            "fraud_risk_score": o.fraud_risk_score,
            "payment_fraud_score": o.payment_fraud_score,
            "is_returned": o.is_returned,
            "is_suspicious": o.is_suspicious,
            "created_at": o.created_at,
        }
        for o in orders
    ]


@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    import json
    result = await db.execute(
        select(FraudAlertModel)
        .order_by(FraudAlertModel.created_at.desc())
        .limit(limit)
    )
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "fraud_type": a.fraud_type,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "explanation": json.loads(a.explanation) if a.explanation else [],
            "is_resolved": a.is_resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]
