"""
Users Router — Real-Time User Risk Analysis
"""
import json
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

ML_PATH = Path(__file__).parent.parent.parent / "ml"
sys.path.insert(0, str(ML_PATH))

from typing import List
from database import get_db
from db_models import (
    UserModel, FraudAlertModel, FlaggedUsersModel,
    OrderModel, ReturnedItemModel, LoginHistoryModel, DeviceHistoryModel
)
from schemas import (
    UserRiskRequest, UserRiskResponse,
    LoginItem, DeviceItem, OrderItemSchema, ReturnItemSchema,
    UserFullResponse
)
from risk_score import analyze_user_risk

router = APIRouter()


@router.post("/risk-score", response_model=UserRiskResponse)
async def compute_user_risk(
    payload: UserRiskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    registry = request.app.state.registry

    risk = await analyze_user_risk(payload.user_id, registry, db)
    if not risk:
        return {"error": "User analysis failed"}

    is_flagged = risk["crypta_risk_score"] >= 70

    await db.commit()

    return UserRiskResponse(
        user_id=payload.user_id,
        crypta_risk_score=risk["crypta_risk_score"],
        risk_level=risk["risk_level"],
        recommended_action=risk["recommended_action"],
        component_scores=risk["component_scores"],
        behavior_signals=risk.get("behavior_signals", {}),
        user_profile=risk.get("user_profile", {}),
        top_contributors=risk["top_contributors"],
        explanation=risk["explanation"],
        is_flagged=is_flagged
    )


@router.get("/flagged")
async def get_flagged_users(
    limit: int = 50,
    min_score: float = 70.0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserModel)
        .where(UserModel.crypta_risk_score >= min_score)
        .order_by(UserModel.crypta_risk_score.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "user_id": u.user_id,
            "crypta_risk_score": u.crypta_risk_score,
            "risk_level": u.risk_level,
            "is_flagged": u.is_flagged,
            "account_age_days": u.account_age_days,
            "total_orders": u.total_orders,
            "total_returns": u.total_returns,
            "last_analyzed": u.last_analyzed,
        }
        for u in users
    ]


@router.get("/all")
async def get_all_users(
    limit: int = 1000,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserModel)
        .order_by(UserModel.crypta_risk_score.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "user_id": u.user_id,
            "crypta_risk_score": u.crypta_risk_score,
            "risk_level": u.risk_level,
            "is_flagged": u.is_flagged,
            "total_orders": u.total_orders,
            "total_returns": u.total_returns,
            "account_age_days": u.account_age_days,
        }
        for u in users
    ]


@router.get("/risk-factors/{user_id}")
async def get_user_risk_factors(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive risk factors and analysis for a user"""
    registry = request.app.state.registry
    
    risk = await analyze_user_risk(user_id, registry, db)
    if not risk:
        return {"error": "User analysis failed"}
    
    result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
    user = result.scalar_one_or_none()

    return {
        "user_id": user.user_id,
        "crypta_risk_score": risk["crypta_risk_score"],
        "risk_level": risk["risk_level"],
        "recommended_action": risk["recommended_action"],
        "component_scores": risk["component_scores"],
        "top_contributors": risk["top_contributors"],
        "user_profile": risk.get("user_profile", {}),
        "behavior_signals": risk.get("behavior_signals", {}),
        "explanation": risk["explanation"]
    }


@router.post("/analyze-all")
async def analyze_all_users(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Automatically analyze all users in the database"""
    registry = request.app.state.registry
    
    result = await db.execute(select(UserModel))
    users = result.scalars().all()
    
    total = len(users)
    flagged_count = 0
    
    for user in users:
        risk = await analyze_user_risk(user.user_id, registry, db)
        if risk and risk["crypta_risk_score"] >= 70:
            flagged_count += 1
    
    await db.commit()
    return {
        "total_users_analyzed": total,
        "flagged_users": flagged_count,
        "status": "completed"
    }


# ──────────────────────────────────────────────
# Risk Explorer Real-Data Endpoints
# ──────────────────────────────────────────────

@router.get("/{user_id}/features")
async def get_user_ml_features(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the raw features used for ML analysis"""
    result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}
    
    return {
        "login_frequency_per_day": user.login_frequency_per_day,
        "ip_changes_30d": user.ip_changes_30d,
        "device_changes_30d": user.device_changes_30d,
        "orders_per_day": user.total_orders / max(user.account_age_days / 30, 1),
        "account_age_days": user.account_age_days,
        "promo_abuse_count": user.promo_abuse_count,
        "return_rate": user.total_returns / max(user.total_orders, 1),
        "total_returns": user.total_returns,
        "total_orders": user.total_orders,
        "refund_total_amount": user.total_refunded_amount
    }


@router.get("/{user_id}/orders", response_model=List[OrderItemSchema])
async def get_user_orders(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get historical orders for a user"""
    result = await db.execute(
        select(OrderModel)
        .where(OrderModel.user_id == user_id)
        .order_by(OrderModel.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{user_id}/returns", response_model=List[ReturnItemSchema])
async def get_user_returns(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get historical returns for a user"""
    result = await db.execute(
        select(ReturnedItemModel)
        .where(ReturnedItemModel.user_id == user_id)
        .order_by(ReturnedItemModel.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{user_id}/logins", response_model=List[LoginItem])
async def get_user_logins(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed login history for a user"""
    result = await db.execute(
        select(LoginHistoryModel)
        .where(LoginHistoryModel.user_id == user_id)
        .order_by(LoginHistoryModel.login_time.desc())
    )
    return result.scalars().all()


@router.get("/{user_id}/devices", response_model=List[DeviceItem])
async def get_user_devices(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get list of devices used by a user"""
    result = await db.execute(
        select(DeviceHistoryModel)
        .where(DeviceHistoryModel.user_id == user_id)
        .order_by(DeviceHistoryModel.last_used.desc())
    )
    return result.scalars().all()


@router.get("/{user_id}/risk")
async def get_user_risk_analysis(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Alias for comprehensive risk analysis for Risk Explorer"""
    return await get_user_risk_factors(user_id, request, db)


@router.get("/{user_id}/full")
async def get_user_full(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time full user analysis for Risk Explorer.
    Queries all related tables, computes risk live, returns everything in one response.
    """
    registry = request.app.state.registry

    # 1. Fetch user
    user_result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found in database")

    # 2. Query related tables
    orders_result = await db.execute(
        select(OrderModel)
        .where(OrderModel.user_id == user_id)
        .order_by(OrderModel.created_at.desc())
        .limit(20)
    )
    orders = orders_result.scalars().all()

    returns_result = await db.execute(
        select(ReturnedItemModel)
        .where(ReturnedItemModel.user_id == user_id)
        .order_by(ReturnedItemModel.created_at.desc())
        .limit(20)
    )
    returns_list = returns_result.scalars().all()

    logins_result = await db.execute(
        select(LoginHistoryModel)
        .where(LoginHistoryModel.user_id == user_id)
        .order_by(LoginHistoryModel.login_time.desc())
        .limit(20)
    )
    logins = logins_result.scalars().all()

    devices_result = await db.execute(
        select(DeviceHistoryModel)
        .where(DeviceHistoryModel.user_id == user_id)
        .order_by(DeviceHistoryModel.last_used.desc())
    )
    devices = devices_result.scalars().all()

    # 3. Live risk computation from real data
    risk = await analyze_user_risk(user_id, registry, db)
    if not risk:
        raise HTTPException(status_code=500, detail="Risk analysis failed")

    await db.commit()

    # 4. Build fraud reasons (combine all flag types)
    fraud_reasons = list(risk.get("explanation", []))

    return {
        # User info
        "user_id": user.user_id,
        "email": user.email,
        "account_age_days": risk["user_profile"].get("account_age_days", user.account_age_days),
        "created_at": user.created_at,
        "is_flagged": user.is_flagged,

        # Related data (real rows)
        "orders": [
            {
                "order_id": o.order_id,
                "amount": o.amount,
                "fraud_risk_score": o.fraud_risk_score,
                "is_suspicious": o.is_suspicious,
                "is_returned": o.is_returned,
                "created_at": o.created_at,
            }
            for o in orders
        ],
        "returns": [
            {
                "return_id": r.return_id,
                "order_id": r.order_id,
                "return_reason": r.return_reason,
                "item_condition": r.item_condition,
                "refund_amount": r.refund_amount,
                "days_to_return": r.days_to_return,
                "created_at": r.created_at,
            }
            for r in returns_list
        ],
        "login_history": [
            {
                "login_time": l.login_time,
                "ip_address": l.ip_address,
                "device_id": l.device_id,
                "location": l.location,
                "is_suspicious": l.is_suspicious,
            }
            for l in logins
        ],
        "device_history": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type,
                "os": d.os,
                "browser": d.browser,
                "last_used": d.last_used,
                "is_new_device": d.is_new_device,
            }
            for d in devices
        ],

        # Computed risk
        "risk_score": risk["crypta_risk_score"],
        "risk_level": risk["risk_level"],
        "fraud_reasons": fraud_reasons,
        "component_scores": risk.get("component_scores", {}),
        "top_contributors": risk.get("top_contributors", []),
        "recommended_action": risk.get("recommended_action", ""),

        # Live-computed profile stats
        "user_profile": risk.get("user_profile", {}),
    }


@router.get("/{user_id}")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserModel).where(UserModel.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found", "user_id": user_id}

    return {
        "user_id": user.user_id,
        "crypta_risk_score": user.crypta_risk_score,
        "risk_level": user.risk_level,
        "is_flagged": user.is_flagged,
        "account_age_days": user.account_age_days,
        "total_orders": user.total_orders,
        "total_returns": user.total_returns,
        "ip_changes_30d": user.ip_changes_30d,
        "device_changes_30d": user.device_changes_30d,
        "login_frequency_per_day": user.login_frequency_per_day,
        "last_analyzed": user.last_analyzed,
    }
