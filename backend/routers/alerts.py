"""
Fraud Alerts Router — GET /api/alerts
Queries fraud_alerts table and exposes paginated, filterable alerts.
"""
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from db_models import FraudAlertModel, UserModel

router = APIRouter()


@router.get("/")
async def get_all_alerts(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    alert_type: str = Query(None, description="Filter by alert type"),
    min_score: float = Query(0.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Return paginated fraud alerts, newest first.
    Optionally filter by alert_type and min_score.
    """
    q = select(FraudAlertModel).order_by(FraudAlertModel.created_at.desc())

    if alert_type:
        q = q.where(FraudAlertModel.fraud_type == alert_type)
    if min_score > 0:
        q = q.where(FraudAlertModel.risk_score >= min_score)

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    alerts = result.scalars().all()

    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "alert_type": a.fraud_type,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "message": _format_message(a),
            "is_resolved": a.is_resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@router.get("/summary")
async def get_alert_summary(db: AsyncSession = Depends(get_db)):
    """Quick counts for the Fraud Alerts page header."""
    total = (await db.execute(select(func.count(FraudAlertModel.id)))).scalar() or 0
    high_risk = (await db.execute(
        select(func.count(FraudAlertModel.id))
        .where(FraudAlertModel.risk_score >= 80)
    )).scalar() or 0
    return_fraud = (await db.execute(
        select(func.count(FraudAlertModel.id))
        .where(FraudAlertModel.fraud_type == "RETURN_FRAUD")
    )).scalar() or 0
    suspicious = (await db.execute(
        select(func.count(FraudAlertModel.id))
        .where(FraudAlertModel.fraud_type == "SUSPICIOUS_BEHAVIOR")
    )).scalar() or 0

    return {
        "total": total,
        "high_risk": high_risk,
        "return_fraud": return_fraud,
        "suspicious_behavior": suspicious,
    }


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as resolved."""
    result = await db.execute(
        select(FraudAlertModel).where(FraudAlertModel.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        return {"error": "Alert not found"}
    alert.is_resolved = True
    await db.commit()
    return {"status": "resolved", "id": alert_id}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _format_message(a: FraudAlertModel) -> str:
    """Generate a human-readable one-line message for this alert."""
    type_msgs = {
        "RETURN_FRAUD":        f"High return rate detected — score {a.risk_score:.0f}/100",
        "SUSPICIOUS_BEHAVIOR": f"Suspicious login/device activity — score {a.risk_score:.0f}/100",
        "HIGH_RISK":           f"Risk score exceeded threshold — {a.risk_score:.0f}/100",
        "PAYMENT_FRAUD":       f"Abnormal payment pattern detected — score {a.risk_score:.0f}/100",
        "PRICING_ANOMALY":     f"Pricing manipulation signals — score {a.risk_score:.0f}/100",
        "INVENTORY_MISMATCH":  f"Inventory anomaly detected — score {a.risk_score:.0f}/100",
        "FAKE_REVIEW":         f"Fake review activity detected — score {a.risk_score:.0f}/100",
    }
    # Try to pull first explanation if available
    if a.explanation:
        try:
            reasons = json.loads(a.explanation)
            if reasons:
                return reasons[0]
        except Exception:
            pass
    return type_msgs.get(a.fraud_type, f"Fraud signal detected — score {a.risk_score:.0f}/100")
