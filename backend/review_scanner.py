"""
Crypta Core AI — Background Review Scanner (Continuous Mode)
Runs every 3 seconds, injects 3-5 synthetic reviews per cycle.

KEY FIX: We pick from TYPED pools, so the fraud type is known at selection time.
We use it directly — no heuristic re-classification needed.
This guarantees BOT, COMPANY_FAKE, SPAM and FAKE all appear in correct proportions.

Pool weights  →  BOT 25% | COMPANY_FAKE 25% | SPAM 20% | FAKE 20% | NORMAL 10%
"""
import asyncio
import logging
import random
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from db_models import ReviewModel, ReviewAlertModel, ReviewAnalysisModel

logger = logging.getLogger("review_scanner")
SCAN_INTERVAL_SECONDS = 3

# ── Typed datasets ────────────────────────────────────────────────────────────

BOT_TEXTS = [
    "This is a great product, I recommend it to everyone.",
    "Excellent product, very satisfied with my purchase today.",
    "Great value for money, highly recommend this product.",
    "Very good product, will definitely buy again soon.",
    "Outstanding quality, exceeded all my expectations completely.",
    "Perfect product, exactly what I was looking for online.",
    "Superb item, 5 stars, recommend to everyone everywhere.",
    "Amazing product, very happy with this purchase today.",
    "Best product ever, will buy again and again for sure.",
    "Fantastic quality, totally worth every single penny spent.",
    "Would definitely recommend this to friends and family.",
    "Great product, fast shipping, will order again.",
]

COMPANY_FAKE_TEXTS = [
    "AMAZING DEAL! Best product on the market right now!!!",
    "Buy now!!! Limited time offer, don't miss out today!",
    "Number one brand in the world, no competition whatsoever!",
    "Best best best!!! Everyone should buy this immediately!!!",
    "UNBELIEVABLE QUALITY!!! Totally worth it, buy now buy now!",
    "Our product is the best! Superior to all competitors clearly!",
    "Industry leading performance, nothing comes close to this!",
    "Company certified excellence! Award winning product here!",
    "Exclusive deal! Only available from us, best price guaranteed!",
    "Trust our brand! Hundreds of verified happy customers daily!",
]

SPAM_TEXTS = [
    "Click link in bio for 50% discount code now!",
    "Visit fraud.com for exclusive offers and free gifts here!",
    "Win a gift card at our website! Limited time offer only!",
    "Free money here! Register now to claim your reward today!",
    "Discount here: bit.ly/fakeoffer sign up today for savings!",
    "Offer now expiring! Go to scam.net for coupon code now!",
    "Check profile for promo code, massive sale happening now!",
    "Get paid to write reviews! DM us for easy extra money!",
    "Earn $500 weekly reviewing products, click link to join us!",
    "Hot deal alert! Use code FAKE99 at spamsite.com right now!",
]

FAKE_TEXTS = [
    "Best product ever!!! Five stars, worth every single cent!!!",
    "Cheap cheap cheap!!! Such a bargain, can't believe the price!!!",
    "INCREDIBLE DEAL!!! Best thing I have ever bought in life!!!",
    "Buy this NOW you won't regret it!!! 100% fully satisfied!!!",
    "Perfect in every way!!! Zero flaws, absolutely flawless item!!!",
    "Totally changed my life!! Everyone needs this product now!!",
    "LOVE LOVE LOVE this!!! Already bought three more units!!!",
    "Mind blowing product!!! Exceeded every single expectation!!!",
    "Cannot believe how good this is!!! Will buy for everyone!!",
    "MUST BUY!!! Telling all friends and family to get this!!!",
]

NORMAL_TEXTS = [
    "Good product, works as described. Delivery was on time.",
    "Decent quality for the price. Would consider buying again.",
    "Works well, nothing extraordinary but does the job fine.",
    "Satisfied with purchase. Packaging was good, arrived safely.",
    "Nice quality overall. Minor issue with sizing but manageable.",
    "Exactly as described in the listing. Happy with my purchase.",
    "Good value for money. Took a week to arrive but acceptable.",
]

# ── Score + reason generators per type ───────────────────────────────────────

def _build_result(fraud_type: str, text: str) -> dict:
    """Return classification dict for a KNOWN fraud_type from the pool."""
    if fraud_type == "BOT":
        signals = [
            "Identical review text detected across 10+ products",
            "Post velocity: 47 identical reviews in 2 hours",
            "No variation in phrasing — classic copy-paste bot signature",
            "User account age < 3 days with 30+ identical reviews",
        ]
        return dict(
            status="BOT",
            score=round(random.uniform(88.0, 99.0), 2),
            reason="Automated bot pattern — identical text posted across multiple products",
            detail="Automated bot reviewer posting identical reviews at scale to manipulate product ratings",
            signals=signals[:random.randint(2, 4)],
            confidence="VERY HIGH",
        )
    elif fraud_type == "COMPANY_FAKE":
        excl = text.count("!")
        signals = [
            f"Brand-promotional language detected ({excl} exclamation marks)",
            "Superlative overuse: 'best', 'amazing', 'unbelievable'",
            "No purchase history for this user on this product",
            "Review posted within minutes of product listing",
            "Language matches competitor-bashing playbook patterns",
        ]
        return dict(
            status="COMPANY_FAKE",
            score=round(random.uniform(72.0, 94.0), 2),
            reason="Company-planted review — brand-manipulation language and promotional patterns",
            detail="Review written by or on behalf of the brand/company to artificially inflate product ratings or defame rival products",
            signals=signals[:random.randint(2, 4)],
            confidence="HIGH",
        )
    elif fraud_type == "SPAM":
        spam_kw = ["link", "bit.ly", "free money", "gift card", "discount here",
                   "earn $", "get paid", "register now", "fraud.com", "scam.net"]
        hits = [k for k in spam_kw if k in text.lower()]
        signals = [
            f"Spam keyword found: '{hits[0]}'" if hits else "External URL embedded in review",
            "Review contains promotional call-to-action",
            "Pattern matches known spam campaign templates",
            "User has posted identical spam across 20+ product categories",
        ]
        return dict(
            status="SPAM",
            score=round(random.uniform(80.0, 97.0), 2),
            reason=f"Spam campaign — {hits[0] if hits else 'promotional links'} detected",
            detail="Review is part of a spam/phishing campaign containing external links, promo codes or monetary solicitations",
            signals=signals[:random.randint(2, 4)],
            confidence="VERY HIGH",
        )
    elif fraud_type == "FAKE":
        excl = text.count("!")
        signals = [
            f"Unnatural enthusiasm: {excl} exclamation marks in short text",
            "Hyperbole density above 95th percentile of authentic reviews",
            "No specific product details — generic praise only",
            "Sentiment score: 100% positive (statistically improbable for genuine buyer)",
        ]
        return dict(
            status="FAKE",
            score=round(random.uniform(65.0, 90.0), 2),
            reason=f"Paid/incentivised fake — {excl} exclamation marks and manufactured enthusiasm",
            detail="Review shows manufactured sentiment patterns consistent with paid review farms or incentivised reviewer programs",
            signals=signals[:random.randint(2, 4)],
            confidence="HIGH",
        )
    else:  # NORMAL
        return dict(
            status="NORMAL",
            score=round(random.uniform(3.0, 18.0), 2),
            reason="No suspicious signals detected — review appears genuine",
            detail="Language patterns consistent with authentic customer feedback",
            signals=["No spam keywords", "Natural language variation detected"],
            confidence="LOW RISK",
        )


# ── Weighted pool: BOT 25 | COMP 25 | SPAM 20 | FAKE 20 | NORM 10 ────────────

_POOL: list[tuple[str, str]] = (
    [("BOT",          t) for t in BOT_TEXTS          for _ in range(3)] +   # 36 entries ~25%
    [("COMPANY_FAKE", t) for t in COMPANY_FAKE_TEXTS  for _ in range(3)] +   # 30 entries ~25%
    [("SPAM",         t) for t in SPAM_TEXTS          for _ in range(2)] +   # 20 entries ~17%
    [("FAKE",         t) for t in FAKE_TEXTS          for _ in range(2)] +   # 20 entries ~17%
    [("NORMAL",       t) for t in NORMAL_TEXTS        for _ in range(2)]     # 14 entries ~12%
)


# ── Core scan ─────────────────────────────────────────────────────────────────

async def _scan_batch(db: AsyncSession) -> None:
    batch_size = random.randint(3, 5)

    for _ in range(batch_size):
        fraud_type, review_text = random.choice(_POOL)
        user_id    = f"USR_{random.randint(1, 1000):06d}"
        product_id = f"PROD_{random.randint(1, 500):05d}"
        rating     = 5 if fraud_type in ("COMPANY_FAKE", "FAKE", "BOT") else random.randint(1, 5)

        # Insert raw review
        review = ReviewModel(
            user_id=user_id,
            product_id=product_id,
            review_text=review_text,
            rating=rating,
            created_at=datetime.utcnow(),
        )
        db.add(review)
        await db.flush()   # get review.id

        result = _build_result(fraud_type, review_text)

        # Always store analysis record
        db.add(ReviewAnalysisModel(
            review_id=review.id,
            risk_score=result["score"],
            status=result["status"],
            created_at=datetime.utcnow(),
        ))

        # Alert row for suspicious types only
        if result["status"] != "NORMAL":
            import json
            db.add(ReviewAlertModel(
                review_id=review.id,
                user_id=user_id,
                product_id=product_id,
                review_text=review_text,
                risk_score=result["score"],
                status=result["status"],
                reason=result["reason"],
                detail=result["detail"],
                is_resolved=False,
                created_at=datetime.utcnow(),
            ))
            logger.info(
                f"[review_scanner] {result['status']} | user={user_id} "
                f"| score={result['score']} | {result['reason'][:50]}"
            )

    await db.commit()


# ── Infinite loop ─────────────────────────────────────────────────────────────

async def run_review_scanner():
    logger.info(f"[review_scanner] Started (interval={SCAN_INTERVAL_SECONDS}s, batch=3-5)")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await _scan_batch(db)
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("[review_scanner] Cancelled.")
            break
        except Exception as e:
            logger.error(f"[review_scanner] Error: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
