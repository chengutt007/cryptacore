"""
Returns Router — Return Fraud Detection
"""
import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import FraudAlertModel
from schemas import ReturnEvaluateRequest, ReturnEvaluateResponse

router = APIRouter()


@router.post("/evaluate", response_model=ReturnEvaluateResponse)
async def evaluate_return_fraud(
    payload: ReturnEvaluateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    registry = request.app.state.registry
    features = payload.model_dump(exclude={"user_id"})
    result = registry.return_detector.evaluate(features)

    # Persist fraud alert if high risk
    if result["risk_score"] >= 40:
        # Include sub-types in the explanation if they exist
        alert_reasons = result["explanation"]
        if result.get("fraud_subtypes"):
            sub_labels = [st["label"] for st in result["fraud_subtypes"]]
            alert_reasons = [f"Sub-types: {', '.join(sub_labels)}"] + alert_reasons

        alert = FraudAlertModel(
            user_id=payload.user_id,
            fraud_type="RETURN_FRAUD",
            risk_score=result["risk_score"],
            risk_level=result["label"],
            explanation=json.dumps(alert_reasons[:5])
        )
        db.add(alert)
        await db.flush()

    return ReturnEvaluateResponse(
        user_id=payload.user_id,
        risk_score=result["risk_score"],
        label=result["label"],
        fraud_probability=result["fraud_probability"],
        explanation=result["explanation"],
        fraud_subtypes=result.get("fraud_subtypes", []),
        fraud_subtype_count=result.get("fraud_subtype_count", 0),
        return_rate_pct=result.get("return_rate_pct", 0.0),
        total_refunded_amount=result.get("total_refunded_amount", 0.0),
        features_analyzed=result["features_analyzed"]
    )
