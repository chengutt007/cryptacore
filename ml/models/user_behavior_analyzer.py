"""
User Behavior Analyzer — Enhanced Inference Module (v2)
Primary focus: Detect suspicious users via behavior, order, device/IP, and return patterns.
Uses Random Forest + Isolation Forest with extended feature set.
"""
import joblib
import numpy as np
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "saved_models"

# ── Extended feature set covering all priority areas ──────────────────────────
FEATURE_NAMES = [
    # Session / Login behavior
    "login_frequency_per_day",
    "session_duration_avg_sec",
    "off_hours_login_ratio",          # logins between 11pm–5am / total logins
    # IP / Device
    "ip_changes_30d",
    "device_changes_30d",
    "unique_countries_30d",
    "vpn_proxy_sessions_ratio",       # fraction of sessions via VPN/proxy
    # Order behavior
    "orders_per_day",
    "order_velocity_spike",           # max orders in any single day (last 30d)
    "cart_abandonment_rate",
    "promo_abuse_count",
    "unique_shipping_addresses",
    # Return & refund signals (primary)
    "return_rate",                    # total_returns / total_orders
    "total_returns",
    "refund_total_amount",            # total $ refunded
    "items_returned_damaged",
    "returns_near_deadline_ratio",    # returns within 2 days of deadline
    "consecutive_return_orders",      # max consecutive orders all returned
    # Account
    "account_age_days",
    "failed_payment_attempts",
]

# Rule-based flag thresholds: (threshold, flag message)
FEATURE_FLAGS = {
    "login_frequency_per_day":     (15,   "Abnormally high login frequency — possible bot or scripted access"),
    "off_hours_login_ratio":       (0.6,  "Majority of logins during suspicious off-hours (11pm–5am)"),
    "ip_changes_30d":              (8,    "Excessive IP changes — likely VPN/proxy rotation"),
    "device_changes_30d":          (4,    "Frequent device fingerprint changes — shared or spoofed device"),
    "unique_countries_30d":        (4,    "Logins from multiple countries in 30 days"),
    "vpn_proxy_sessions_ratio":    (0.5,  "High fraction of sessions via VPN/proxy"),
    "orders_per_day":              (8,    "Unusually high order velocity"),
    "order_velocity_spike":        (20,   "Spike: 20+ orders placed in a single day"),
    "cart_abandonment_rate":       (0.75, "Very high cart abandonment rate"),
    "promo_abuse_count":           (3,    "Promotional code abuse detected"),
    "unique_shipping_addresses":   (6,    "Too many unique delivery addresses"),
    "return_rate":                 (0.65, "Return rate above 65% — return fraud pattern"),
    "total_returns":               (15,   "Excessively high lifetime return count"),
    "refund_total_amount":         (2000, "Total refunded amount is unusually high"),
    "items_returned_damaged":      (4,    "Multiple 'damaged item' return claims — possible abuse"),
    "returns_near_deadline_ratio": (0.5,  "Over half of returns filed near the return deadline"),
    "consecutive_return_orders":   (4,    "Long streak of consecutive all-return orders"),
    "account_age_days":            (None, ""),   # handled separately
    "failed_payment_attempts":     (4,    "Multiple failed payment attempts — testing stolen cards?"),
    "session_duration_avg_sec":    (None, ""),
    "refund_total_amount":         (2000, "Total refunded amount unusually high"),
}

# Weights for heuristic score (used when model not trained yet)
HEURISTIC_WEIGHTS = {
    "return_rate":                 0.20,
    "items_returned_damaged":      0.12,
    "refund_total_amount":         0.10,
    "consecutive_return_orders":   0.10,
    "returns_near_deadline_ratio": 0.08,
    "ip_changes_30d":              0.08,
    "device_changes_30d":          0.06,
    "vpn_proxy_sessions_ratio":    0.07,
    "orders_per_day":              0.06,
    "promo_abuse_count":           0.05,
    "login_frequency_per_day":     0.05,
    "off_hours_login_ratio":       0.03,
}

# Normalizers for heuristic (upper bounds → maps to 1.0)
HEURISTIC_NORM = {
    "return_rate": 1.0, "items_returned_damaged": 10, "refund_total_amount": 5000,
    "consecutive_return_orders": 10, "returns_near_deadline_ratio": 1.0,
    "ip_changes_30d": 20, "device_changes_30d": 10, "vpn_proxy_sessions_ratio": 1.0,
    "orders_per_day": 20, "promo_abuse_count": 10, "login_frequency_per_day": 30,
    "off_hours_login_ratio": 1.0,
}


class UserBehaviorAnalyzer:
    def __init__(self):
        self.rf_model = None
        self.iso_forest = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        model_path = MODELS_DIR / "user_behavior_model.joblib"
        if model_path.exists():
            bundle = joblib.load(model_path)
            self.rf_model = bundle.get("rf_model")
            self.iso_forest = bundle.get("iso_forest")
            self.scaler = bundle.get("scaler")

    def _get_flags(self, features: dict) -> list[str]:
        flags = []
        for feat, val_msg in FEATURE_FLAGS.items():
            threshold, msg = val_msg
            if threshold is None or not msg:
                continue
            val = features.get(feat, 0)
            if val >= threshold:
                flags.append(msg)
        if features.get("account_age_days", 999) < 14:
            flags.append("Very new account with suspicious activity levels")
        return list(dict.fromkeys(flags))[:6]  # deduplicate, cap at 6

    def _heuristic_score(self, features: dict) -> float:
        score = 0.0
        for feat, weight in HEURISTIC_WEIGHTS.items():
            val = features.get(feat, 0)
            norm = HEURISTIC_NORM.get(feat, 1)
            score += weight * min(1.0, val / max(norm, 1e-6))
        # New account penalty
        age = features.get("account_age_days", 365)
        if age < 30:
            score += 0.10 * (1 - age / 30)
        return min(1.0, score)

    def analyze(self, features: dict) -> dict:
        fvec = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])
        flags = self._get_flags(features)

        if self.rf_model is not None and self.scaler is not None:
            fvec_s = self.scaler.transform(fvec)
            suspicious_prob = float(self.rf_model.predict_proba(fvec_s)[0][1])
            iso_score = self.iso_forest.score_samples(fvec_s)[0]
            anomaly_score = float(np.clip((-iso_score - 0.1) / 0.4, 0, 1))
            # Behavior RF weighted higher than anomaly for interpretability
            combined = 0.70 * suspicious_prob + 0.30 * anomaly_score
        else:
            combined = self._heuristic_score(features)
            anomaly_score = combined

        risk_score = round(min(100.0, combined * 100), 1)

        if risk_score >= 75:
            risk_level = "CRITICAL"
        elif risk_score >= 55:
            risk_level = "HIGH"
        elif risk_score >= 35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "anomaly_score": round(anomaly_score, 4),
            "suspicious_probability": round(combined, 4),
            "flags": flags if flags else ["No suspicious behavior patterns detected"],
            "features_analyzed": len(FEATURE_NAMES),
            # Breakdown of key signals for explainability
            "signal_breakdown": {
                "return_signals": round(
                    min(1.0, (features.get("return_rate", 0) * 0.5 +
                              features.get("items_returned_damaged", 0) / 10 * 0.3 +
                              features.get("consecutive_return_orders", 0) / 8 * 0.2)) * 100, 1),
                "device_ip_signals": round(
                    min(1.0, (features.get("ip_changes_30d", 0) / 20 * 0.5 +
                              features.get("vpn_proxy_sessions_ratio", 0) * 0.3 +
                              features.get("device_changes_30d", 0) / 10 * 0.2)) * 100, 1),
                "order_velocity_signals": round(
                    min(1.0, (features.get("orders_per_day", 0) / 20 * 0.6 +
                              features.get("promo_abuse_count", 0) / 10 * 0.4)) * 100, 1),
                "account_signals": round(
                    min(1.0, max(0, (30 - features.get("account_age_days", 365)) / 30) * 0.7 +
                    features.get("failed_payment_attempts", 0) / 10 * 0.3) * 100, 1),
            }
        }
