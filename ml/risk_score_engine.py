"""
Crypta Risk Score Engine — Enhanced (v2)
Prioritizes Return Fraud and User Behavior.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RiskComponents:
    fake_review_score: float = 0.0      # 0-100
    return_fraud_score: float = 0.0     # 0-100
    behavior_score: float = 0.0         # 0-100
    payment_fraud_score: float = 0.0    # 0-100
    pricing_score: float = 0.0          # 0-100 (NEW)
    inventory_score: float = 0.0        # 0-100 (NEW)

    # Optional reasons/subtypes
    fake_review_reasons: list = None
    return_fraud_reasons: list = None
    return_fraud_subtypes: list = None  # [{label, description}]
    behavior_flags: list = None
    payment_flags: list = None
    pricing_flags: list = None
    inventory_flags: list = None
    behavior_signal_breakdown: dict = None

    def __post_init__(self):
        self.fake_review_reasons = self.fake_review_reasons or []
        self.return_fraud_reasons = self.return_fraud_reasons or []
        self.return_fraud_subtypes = self.return_fraud_subtypes or []
        self.behavior_flags = self.behavior_flags or []
        self.payment_flags = self.payment_flags or []
        self.pricing_flags = self.pricing_flags or []
        self.inventory_flags = self.inventory_flags or []
        self.behavior_signal_breakdown = self.behavior_signal_breakdown or {}


# NEW WEIGHTS: Return Fraud (45%) & User Behavior (35%) primary; Pricing (10%), Inventory (5%), Others (5%)
WEIGHTS = {
    "fake_review": 0.02,
    "return_fraud": 0.45,
    "behavior": 0.35,
    "payment_fraud": 0.08,
    "pricing": 0.08,
    "inventory": 0.02,
}


def compute_risk_score(components: RiskComponents) -> dict:
    """
    Compute composite Crypta Risk Score (0–100) prioritizing returns and behavior.
    Enhanced with pricing and inventory insights.
    """
    weighted_score = (
        components.fake_review_score * WEIGHTS["fake_review"] +
        components.return_fraud_score * WEIGHTS["return_fraud"] +
        components.behavior_score * WEIGHTS["behavior"] +
        components.payment_fraud_score * WEIGHTS["payment_fraud"] +
        components.pricing_score * WEIGHTS["pricing"] +
        components.inventory_score * WEIGHTS["inventory"]
    )
    
    # Non-linear scaling: if return fraud or behavior is critical, boost the overall score
    if components.return_fraud_score > 85 or components.behavior_score > 85:
        weighted_score = max(weighted_score, 80.0)
    
    # Pricing abuse significantly boosts risk
    if components.pricing_score > 70:
        weighted_score = max(weighted_score, 60.0)
        
    crypta_score = round(min(100.0, max(0.0, weighted_score)), 1)

    # SHAP-style top contributing factors
    contributions = {
        "Return Fraud Pattern": round(components.return_fraud_score * WEIGHTS["return_fraud"], 1),
        "Suspicious User Behavior": round(components.behavior_score * WEIGHTS["behavior"], 1),
        "Pricing Anomalies": round(components.pricing_score * WEIGHTS["pricing"], 1),
        "Payment Fraud Signals": round(components.payment_fraud_score * WEIGHTS["payment_fraud"], 1),
        "Inventory Mismatch": round(components.inventory_score * WEIGHTS["inventory"], 1),
        "Fake Review Activity": round(components.fake_review_score * WEIGHTS["fake_review"], 1),
    }
    sorted_contributions = sorted(contributions.items(), key=lambda x: x[1], reverse=True)

    # Aggregate reasons from sub-models
    all_reasons = []
    
    # Prioritize sub-types if any
    for st in components.return_fraud_subtypes:
        all_reasons.append(f"[Fraud Type Detected] {st['label']}: {st['description']}")
        
    for r in components.return_fraud_reasons[:2]:
        all_reasons.append(f"[Returns] {r}")
    
    for r in components.pricing_flags[:2]:
        all_reasons.append(f"[Pricing] {r}")
    
    for r in components.inventory_flags[:2]:
        all_reasons.append(f"[Inventory] {r}")
        
    for r in components.behavior_flags[:2]:
        all_reasons.append(f"[Behavior] {r}")
        
    for r in components.fake_review_reasons[:1]:
        all_reasons.append(f"[Review] {r}")
        
    for r in components.payment_flags[:1]:
        all_reasons.append(f"[Payment] {r}")

    # Deduplicate reasons list preserving order
    unique_reasons = list(dict.fromkeys(all_reasons))

    # Risk level determination
    if crypta_score >= 85:
        risk_level = "CRITICAL"
        action = "Block user and freeze associated returns/refunds immediately"
    elif crypta_score >= 70:
        risk_level = "HIGH"
        action = "Flag for manual review, require supervisor approval for returns"
    elif crypta_score >= 40:
        risk_level = "MEDIUM"
        action = "Monitor closely, limit automated refund approvals"
    else:
        risk_level = "LOW"
        action = "No immediate action required"

    return {
        "crypta_risk_score": crypta_score,
        "risk_level": risk_level,
        "recommended_action": action,
        "component_scores": {
            "fake_review": components.fake_review_score,
            "return_fraud": components.return_fraud_score,
            "behavior": components.behavior_score,
            "payment_fraud": components.payment_fraud_score,
            "pricing": components.pricing_score,
            "inventory": components.inventory_score,
        },
        "behavior_signals": components.behavior_signal_breakdown,
        "top_contributors": [
            {"factor": name, "contribution": score, "weight_pct": f"{WEIGHTS.get(name.lower().replace(' ', '_').replace('suspicious_user_behavior', 'behavior').replace('pricing_anomalies', 'pricing').replace('inventory_mismatch', 'inventory'), 0)*100:.0f}%"}
            for name, score in sorted_contributions if score > 0
        ],
        "explanation": unique_reasons[:10] or ["Insufficient data to generate detailed explanation"],
    }
