"""
Payments Router — Payment Fraud Detection
"""
import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import FraudAlertModel, OrderModel
from schemas import PaymentAnalyzeRequest, PaymentAnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=PaymentAnalyzeResponse)
async def analyze_payment(
    payload: PaymentAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    registry = request.app.state.registry
    features = payload.model_dump(exclude={"user_id", "order_id"})
    result = registry.payment_detector.analyze(features)

    # Persist order record
    if payload.order_id:
        order = OrderModel(
            order_id=payload.order_id,
            user_id=payload.user_id,
            amount=payload.amount,
            fraud_risk_score=result["risk_score"],
            payment_fraud_score=result["risk_score"],
            is_suspicious=result["risk_score"] >= 55,
        )
        db.add(order)

    # Persist fraud alert for suspicious payments
    if result["risk_score"] >= 40:
        alert = FraudAlertModel(
            user_id=payload.user_id,
            fraud_type="PAYMENT_FRAUD",
            risk_score=result["risk_score"],
            risk_level="HIGH" if result["risk_score"] >= 70 else "MEDIUM",
            explanation=json.dumps(result["flags"])
        )
        db.add(alert)

    await db.flush()
    return PaymentAnalyzeResponse(
        user_id=payload.user_id,
        order_id=payload.order_id,
        **result
    )
