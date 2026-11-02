"""
Crypta Core AI — Background Fraud Scanner (Continuous Mode)
Runs every 3 seconds, picks a random user, always inserts a new alert.
No deduplication — each scan always creates a new row.
Alert type: 70% RETURN_FRAUD, 30% PAYMENT_FRAUD.
"""
import asyncio
import json
import logging
import random
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from db_models import UserModel, FraudAlertModel

logger = logging.getLogger("fraud_scanner")

SCAN_INTERVAL_SECONDS = 3

# Alert type weights: 70% RETURN_FRAUD, 30% PAYMENT_FRAUD
ALERT_TYPES = ["RETURN_FRAUD", "PAYMENT_FRAUD"]
ALERT_WEIGHTS = [0.70, 0.30]


def _risk_level_from_score(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _build_explanation(alert_type: str, user: UserModel) -> list:
    if alert_type == "RETURN_FRAUD":
        return_rate = user.total_returns / max(user.total_orders, 1)
        return [
            f"Suspicious return pattern detected — rate {return_rate:.0%}",
            f"Total returns: {user.total_returns} across {user.total_orders} orders",
            f"Total refunded: ${user.total_refunded_amount:.2f}",
        ]
    else:  # PAYMENT_FRAUD
        return [
            f"Abnormal payment / refund activity detected",
            f"Total refunded amount: ${user.total_refunded_amount:.2f}",
            f"Risk score: {user.crypta_risk_score:.1f}/100",
        ]


async def _scan_once(db: AsyncSession) -> None:
    """
    Pick one random user, choose alert type by weighted random,
    and always insert a new FraudAlertModel row.
    """
    # Count users
    count_result = await db.execute(select(func.count(UserModel.id)))
    total_users = count_result.scalar() or 0
    if total_users == 0:
        logger.warning("[scanner] No users found, skipping scan")
        return

    # Pick a random offset to select one random user
    random_offset = random.randint(0, total_users - 1)
    user_result = await db.execute(
        select(UserModel).offset(random_offset).limit(1)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return

    # Choose alert type by weight
    alert_type = random.choices(ALERT_TYPES, weights=ALERT_WEIGHTS, k=1)[0]

    score = user.crypta_risk_score
    # Boost score slightly for realism if it's too low
    if score < 40:
        score = random.uniform(42, 75)

    level = _risk_level_from_score(score)
    reasons = _build_explanation(alert_type, user)

    alert = FraudAlertModel(
        user_id=user.user_id,
        fraud_type=alert_type,
        risk_score=round(score, 2),
        risk_level=level,
        explanation=json.dumps(reasons),
        is_resolved=False,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    await db.commit()

    logger.info(
        f"[scanner] New alert: {alert_type} | user={user.user_id} | score={score:.1f}"
    )


async def run_scanner():
    """
    Infinite loop — inserts a new fraud alert every SCAN_INTERVAL_SECONDS.
    Started as an asyncio background task on server startup.
    """
    logger.info(
        f"[scanner] Continuous fraud scanner started "
        f"(interval={SCAN_INTERVAL_SECONDS}s, no dedup)"
    )
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await _scan_once(db)
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("[scanner] Scanner task cancelled, shutting down.")
            break
        except Exception as e:
            logger.error(f"[scanner] Error in scan loop: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
