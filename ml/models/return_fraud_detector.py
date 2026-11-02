"""
Return Fraud Detector — Enhanced Inference Module (v2)
PRIMARY FEATURE: Comprehensive return fraud detection with fraud sub-type classification.
Detects: excessive returns, damaged item fraud, fake return claims, refund abuse, policy abuse.
Uses XGBoost with SHAP explanations.
"""
import joblib
import numpy as np
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "saved_models"

# ── Extended return-focused feature set ──────────────────────────────────────
FEATURE_NAMES = [
    # Core return metrics
    "return_rate",                   # total_returns / total_orders
    "total_returns",
    "total_orders",
    "avg_days_to_return",            # avg days between purchase and return initiation
    "returns_near_deadline_ratio",   # fraction of returns within 2 days of deadline
    # Refund signals
    "refund_abuse_count",            # times flagged for refund abuse
    "refund_total_amount",           # total $ refunded (lifetime)
    "avg_refund_value",              # avg refund per return
    "high_value_return_count",       # returns of items > $200
    # Damage fraud signals
    "items_returned_damaged",        # count of 'damaged' returns
    "damaged_return_rate",           # items_returned_damaged / total_returns
    "no_original_packaging_count",   # returns missing original packaging
    # Pattern signals
    "consecutive_return_orders",     # max streak of consecutive fully-returned orders
    "same_item_return_count",        # same product returned multiple times
    "cross_account_return_flag",     # returns matched to multiple accounts (0/1)
    # Account context
    "account_age_days",
    "avg_order_value",
    "dispute_count",
]

# Sub-type classifiers (rule-based layer on top of ML)
FRAUD_SUBTYPES = {
    "excessive_returns": {
        "check": lambda f: f.get("return_rate", 0) > 0.60 and f.get("total_returns", 0) > 5,
        "label": "Excessive Return Rate",
        "desc": "User returns over 60% of all orders — far above normal behaviour",
    },
    "damaged_item_fraud": {
        "check": lambda f: f.get("items_returned_damaged", 0) > 3 or f.get("damaged_return_rate", 0) > 0.5,
        "label": "Damaged Item Fraud",
        "desc": "Abnormally high rate of 'damaged' claims — likely keeping items and claiming damage",
    },
    "refund_abuse": {
        "check": lambda f: f.get("refund_abuse_count", 0) > 2 or f.get("refund_total_amount", 0) > 1500,
        "label": "Refund Abuse",
        "desc": "Repeated refund exploitation — high total refund amounts issued",
    },
    "deadline_gaming": {
        "check": lambda f: f.get("returns_near_deadline_ratio", 0) > 0.7,
        "label": "Return Deadline Gaming",
        "desc": "Most returns filed within days of the policy deadline — deliberate timing",
    },
    "policy_abuse": {
        "check": lambda f: f.get("same_item_return_count", 0) > 2 or f.get("no_original_packaging_count", 0) > 3,
        "label": "Return Policy Abuse",
        "desc": "Returning same items repeatedly or without original packaging",
    },
    "fake_return_claims": {
        "check": lambda f: f.get("cross_account_return_flag", 0) == 1 or (
            f.get("consecutive_return_orders", 0) > 5 and f.get("return_rate", 0) > 0.8
        ),
        "label": "Fake Return Claims",
        "desc": "Return patterns suggest coordinated or fabricated return requests",
    },
    "high_value_abuse": {
        "check": lambda f: f.get("high_value_return_count", 0) > 2 and f.get("avg_order_value", 0) > 100,
        "label": "High-Value Item Abuse",
        "desc": "Repeatedly returning high-value items — potential exploitation",
    },
    "new_account_fraud": {
        "check": lambda f: f.get("account_age_days", 365) < 30 and f.get("return_rate", 0) > 0.5 and f.get("total_returns", 0) > 3,
        "label": "New Account Fraud",
        "desc": "Brand new account with immediate high return activity — likely testing fraud",
    },
}

FEATURE_EXPLANATIONS = {
    "return_rate":                 "Return rate is extremely high relative to purchase history",
    "avg_days_to_return":          "Returns initiated very close to the policy deadline",
    "refund_abuse_count":          "Multiple prior refund abuse incidents on record",
    "items_returned_damaged":      "Unusually high number of 'damaged item' claims",
    "account_age_days":            "New account with disproportionately high return activity",
    "total_orders":                "Low order volume with high returns suggests exploratory abuse",
    "total_returns":               "Excessively high lifetime return count",
    "avg_order_value":             "High-value orders being returned at suspicious rate",
    "dispute_count":               "Multiple payment disputes filed alongside returns",
    "refund_total_amount":         "Total refunded amount is unusually high",
    "damaged_return_rate":         "High fraction of returns logged as 'damaged'",
    "consecutive_return_orders":   "Long streak of orders that were all fully returned",
    "same_item_return_count":      "Same product returned multiple times",
    "returns_near_deadline_ratio": "Most returns filed in the final days of the return window",
    "high_value_return_count":     "Multiple high-value item (>$200) returns within short period",
    "no_original_packaging_count": "Returns missing original packaging suggesting item kept/reused",
    "cross_account_return_flag":   "Return patterns detected across multiple linked accounts",
}


class ReturnFraudDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.explainer = None
        self._load_model()

    def _load_model(self):
        model_path = MODELS_DIR / "return_fraud_model.joblib"
        if model_path.exists():
            bundle = joblib.load(model_path)
            self.model = bundle.get("model")
            self.scaler = bundle.get("scaler")
            try:
                import shap
                self.explainer = shap.TreeExplainer(self.model)
            except Exception:
                pass

    def _get_shap_reasons(self, fvec_s: np.ndarray, features_raw: dict) -> list[str]:
        reasons = []
        if self.explainer is not None:
            try:
                sv = self.explainer.shap_values(fvec_s)
                if isinstance(sv, list):
                    sv = sv[1]   # class 1 (fraud)
                top_idx = np.argsort(np.abs(sv[0]))[::-1][:4]
                for idx in top_idx:
                    fname = FEATURE_NAMES[idx]
                    val = features_raw.get(fname, 0)
                    reason = FEATURE_EXPLANATIONS.get(fname, fname)
                    reasons.append(f"{reason} (actual value: {val})")
            except Exception:
                pass
        return reasons

    def _heuristic_score(self, features: dict) -> float:
        score = 0.0
        score += min(0.30, features.get("return_rate", 0) * 0.40)
        score += min(0.20, features.get("refund_abuse_count", 0) / 10 * 0.20)
        score += min(0.15, features.get("items_returned_damaged", 0) / 8 * 0.15)
        score += min(0.10, features.get("consecutive_return_orders", 0) / 8 * 0.10)
        score += min(0.10, features.get("returns_near_deadline_ratio", 0) * 0.10)
        score += min(0.08, features.get("refund_total_amount", 0) / 5000 * 0.08)
        if features.get("account_age_days", 999) < 30:
            score += 0.07 * (1 - features["account_age_days"] / 30)
        return min(1.0, score)

    def _detect_fraud_subtypes(self, features: dict) -> list[dict]:
        detected = []
        for _, info in FRAUD_SUBTYPES.items():
            try:
                if info["check"](features):
                    detected.append({"label": info["label"], "description": info["desc"]})
            except Exception:
                pass
        return detected

    def evaluate(self, features: dict) -> dict:
        fvec = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])

        if self.model is not None and self.scaler is not None:
            fvec_s = self.scaler.transform(fvec)
            fraud_prob = float(self.model.predict_proba(fvec_s)[0][1])
            reasons = self._get_shap_reasons(fvec_s, features)
        else:
            fraud_prob = self._heuristic_score(features)
            reasons = []

        # Always add rule-based explanations if ML reasons are sparse
        if len(reasons) < 2:
            for fname in FEATURE_NAMES:
                if features.get(fname, 0) > 0:
                    exp = FEATURE_EXPLANATIONS.get(fname)
                    if exp and exp not in [r.split(" (")[0] for r in reasons]:
                        reasons.append(f"{exp} (value: {features[fname]})")
                if len(reasons) >= 4:
                    break

        fraud_subtypes = self._detect_fraud_subtypes(features)
        risk_score = round(fraud_prob * 100, 1)

        if risk_score >= 75:
            label = "HIGH"
        elif risk_score >= 45:
            label = "MEDIUM"
        else:
            label = "LOW"

        return {
            "risk_score": risk_score,
            "label": label,
            "fraud_probability": round(fraud_prob, 4),
            "explanation": reasons[:5] or ["Insufficient history for detailed analysis"],
            "fraud_subtypes": fraud_subtypes,           # NEW: classified fraud types
            "fraud_subtype_count": len(fraud_subtypes),
            "return_rate_pct": round(features.get("return_rate", 0) * 100, 1),
            "total_refunded_amount": features.get("refund_total_amount", 0),
            "features_analyzed": FEATURE_NAMES,
        }
