"""
Payment Fraud Detector — Inference Module
Uses XGBoost with feature-level explanations.
"""
import joblib
import numpy as np
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "saved_models"

FEATURE_NAMES = [
    "amount", "amount_vs_user_avg_ratio", "failed_attempts_24h",
    "payment_method_changes_7d", "geo_mismatch", "time_since_last_payment_hours",
    "card_bin_risk", "is_new_payment_method", "vpn_detected", "transaction_hour"
]

FEATURE_EXPLANATIONS = {
    "amount": "Transaction amount unusually high",
    "amount_vs_user_avg_ratio": "Amount significantly above user's historical average",
    "failed_attempts_24h": "Multiple failed payment attempts in last 24 hours",
    "payment_method_changes_7d": "Frequent payment method switching detected",
    "geo_mismatch": "Transaction location does not match account home region",
    "time_since_last_payment_hours": "Unusually short time between transactions",
    "card_bin_risk": "Card BIN associated with high-risk issuer",
    "is_new_payment_method": "New payment method added recently",
    "vpn_detected": "VPN or proxy detected during transaction",
    "transaction_hour": "Transaction at unusual hour (late night / early morning)"
}


class PaymentFraudDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        model_path = MODELS_DIR / "payment_fraud_model.joblib"
        if model_path.exists():
            bundle = joblib.load(model_path)
            self.model = bundle["model"]
            self.scaler = bundle["scaler"]

    def _rule_flags(self, features: dict) -> list[str]:
        flags = []
        if features.get("vpn_detected", 0) == 1:
            flags.append(FEATURE_EXPLANATIONS["vpn_detected"])
        if features.get("geo_mismatch", 0) == 1:
            flags.append(FEATURE_EXPLANATIONS["geo_mismatch"])
        if features.get("failed_attempts_24h", 0) >= 3:
            flags.append(FEATURE_EXPLANATIONS["failed_attempts_24h"])
        if features.get("amount_vs_user_avg_ratio", 1) > 5:
            flags.append(FEATURE_EXPLANATIONS["amount_vs_user_avg_ratio"])
        if features.get("card_bin_risk", 0) > 0.6:
            flags.append(FEATURE_EXPLANATIONS["card_bin_risk"])
        hour = features.get("transaction_hour", 12)
        if hour <= 4:
            flags.append(FEATURE_EXPLANATIONS["transaction_hour"])
        return flags[:5]

    def analyze(self, features: dict) -> dict:
        fvec = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])
        flags = self._rule_flags(features)

        if self.model is not None and self.scaler is not None:
            fvec_s = self.scaler.transform(fvec)
            fraud_prob = float(self.model.predict_proba(fvec_s)[0][1])
        else:
            fraud_prob = min(1.0, len(flags) * 0.22)

        risk_score = round(fraud_prob * 100, 1)

        if risk_score >= 70:
            verdict = "FRAUD"
        elif risk_score >= 40:
            verdict = "SUSPICIOUS"
        else:
            verdict = "LEGITIMATE"

        return {
            "verdict": verdict,
            "fraud_probability": round(fraud_prob, 4),
            "risk_score": risk_score,
            "flags": flags if flags else ["No suspicious payment signals detected"],
            "amount": features.get("amount", 0),
            "transaction_hour": features.get("transaction_hour", 12)
        }
