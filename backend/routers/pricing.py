"""
Pricing & Inventory Router — Enhanced fraud detection using pricing and inventory data
"""
import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import FraudAlertModel
from schemas import PricingAnalyzeRequest, PricingAnalyzeResponse, InventoryAnalyzeRequest, InventoryAnalyzeResponse

router = APIRouter()


@router.post("/pricing/analyze", response_model=PricingAnalyzeResponse)
async def analyze_pricing_patterns(
    payload: PricingAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Analyze pricing patterns for fraud indicators"""
    registry = request.app.state.registry
    
    features = {
        "avg_order_value": payload.avg_order_value,
        "total_orders": payload.total_orders,
        "total_returns": payload.total_returns,
        "high_value_return_count": payload.high_value_return_count,
        "promo_abuse_count": payload.promo_abuse_count,
        "total_discount_amount": payload.total_discount_amount,
        "total_refunded_amount": payload.total_refunded_amount,
        "account_age_days": payload.account_age_days,
        "min_observed_price": payload.min_observed_price,
        "base_price_avg": payload.base_price_avg,
        "avg_discount_pct": payload.avg_discount_pct,
    }
    
    result = registry.pricing_intelligence.analyze(features)
    
    # Persist alert if high risk
    if result["risk_score"] >= 50:
        alert = FraudAlertModel(
            user_id=payload.user_id,
            fraud_type="PRICING_ANOMALY",
            risk_score=result["risk_score"],
            risk_level=result["label"],
            explanation=json.dumps(result["flags"][:4])
        )
        db.add(alert)
        await db.flush()
    
    return PricingAnalyzeResponse(
        user_id=payload.user_id,
        risk_score=result["risk_score"],
        label=result["label"],
        fraud_probability=result["fraud_probability"],
        flags=result["flags"],
        pricing_features=result.get("pricing_features", {})
    )


@router.post("/inventory/analyze", response_model=InventoryAnalyzeResponse)
async def analyze_inventory_anomalies(
    payload: InventoryAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Analyze inventory patterns for fraud indicators"""
    registry = request.app.state.registry
    
    features = {
        "total_returns": payload.total_returns,
        "product_return_rate": payload.product_return_rate,
        "returned_qty_vs_available": payload.returned_qty_vs_available,
        "item_condition_variance": payload.item_condition_variance,
        "warehouse_quantity_variance": payload.warehouse_quantity_variance,
        "returns_without_packaging_pct": payload.returns_without_packaging_pct,
    }
    
    result = registry.inventory_intelligence.analyze(features)
    
    # Persist alert if high risk
    if result["risk_score"] >= 50:
        alert = FraudAlertModel(
            user_id=payload.user_id,
            fraud_type="INVENTORY_MISMATCH",
            risk_score=result["risk_score"],
            risk_level=result["label"],
            explanation=json.dumps(result["flags"][:4])
        )
        db.add(alert)
        await db.flush()
    
    return InventoryAnalyzeResponse(
        user_id=payload.user_id,
        risk_score=result["risk_score"],
        label=result["label"],
        fraud_probability=result["fraud_probability"],
        flags=result["flags"],
        inventory_features=result.get("inventory_features", {})
    )
