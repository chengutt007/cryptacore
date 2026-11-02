"""
Crypta Core AI — Model Training Script (v2)
Added extended features for Return Fraud and User Behavior.
"""
import os
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent / "training_data"
MODELS_DIR = Path(__file__).parent / "saved_models"
MODELS_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("  Crypta Core AI — Model Training (v2 - User & Return Focus)")
print("=" * 60)

def evaluate(name, y_test, y_pred, y_prob=None):
    print(f"\n📊 {name}")
    print(classification_report(y_test, y_pred, target_names=["Genuine", "Fraud/Suspicious"]))
    if y_prob is not None:
        auc = roc_auc_score(y_test, y_prob)
        print(f"   AUC-ROC: {auc:.4f}")

# ──────────────────────────────────────────────────────────────
# 1. USER BEHAVIOR ANALYZER (Isolation Forest + Random Forest)
# ──────────────────────────────────────────────────────────────
print("\n[1/2] Training User Behavior Analyzer (Enhanced Features)...")
df_behavior = pd.read_csv(DATA_DIR / "user_behavior.csv")
BEHAVIOR_FEATURES = [
    "login_frequency_per_day", "session_duration_avg_sec", "off_hours_login_ratio",
    "ip_changes_30d", "device_changes_30d", "unique_countries_30d", "vpn_proxy_sessions_ratio",
    "orders_per_day", "order_velocity_spike", "cart_abandonment_rate", "promo_abuse_count",
    "unique_shipping_addresses", "return_rate", "total_returns", "refund_total_amount",
    "items_returned_damaged", "returns_near_deadline_ratio", "consecutive_return_orders",
    "account_age_days", "failed_payment_attempts"
]
X_beh = df_behavior[BEHAVIOR_FEATURES].values
y_beh = df_behavior["label"].values

X_tr, X_te, y_tr, y_te = train_test_split(X_beh, y_beh, test_size=0.2, random_state=42)
scaler_beh = StandardScaler()
X_tr_s = scaler_beh.fit_transform(X_tr)
X_te_s = scaler_beh.transform(X_te)

rf_behavior = RandomForestClassifier(n_estimators=300, max_depth=12, class_weight="balanced", random_state=42, n_jobs=-1)
rf_behavior.fit(X_tr_s, y_tr)
y_pred_beh = rf_behavior.predict(X_te_s)
y_prob_beh = rf_behavior.predict_proba(X_te_s)[:, 1]
evaluate("User Behavior Analyzer (RF)", y_te, y_pred_beh, y_prob_beh)

iso_forest = IsolationForest(n_estimators=300, contamination=0.25, random_state=42, n_jobs=-1)
iso_forest.fit(scaler_beh.transform(X_beh))

joblib.dump({"rf_model": rf_behavior, "iso_forest": iso_forest, "scaler": scaler_beh}, MODELS_DIR / "user_behavior_model.joblib")
print("   ✅ Saved: user_behavior_model.joblib")

# ──────────────────────────────────────────────────────────────
# 2. RETURN FRAUD DETECTOR (XGBoost)
# ──────────────────────────────────────────────────────────────
print("\n[2/2] Training Return Fraud Detector (Enhanced Features)...")
df_returns = pd.read_csv(DATA_DIR / "return_fraud.csv")
RETURN_FEATURES = [
    "return_rate", "total_returns", "total_orders", "avg_days_to_return",
    "returns_near_deadline_ratio", "refund_abuse_count", "refund_total_amount",
    "avg_refund_value", "high_value_return_count", "items_returned_damaged",
    "damaged_return_rate", "no_original_packaging_count", "consecutive_return_orders",
    "same_item_return_count", "cross_account_return_flag", "account_age_days",
    "avg_order_value", "dispute_count"
]
X_ret = df_returns[RETURN_FEATURES].values
y_ret = df_returns["label"].values

X_tr, X_te, y_tr, y_te = train_test_split(X_ret, y_ret, test_size=0.2, random_state=42)
scaler_ret = StandardScaler()
X_tr_s = scaler_ret.fit_transform(X_tr)
X_te_s = scaler_ret.transform(X_te)

xgb_return = xgb.XGBClassifier(
    n_estimators=300, max_depth=7, learning_rate=0.08,
    use_label_encoder=False, eval_metric="logloss",
    scale_pos_weight=2.5, random_state=42, n_jobs=-1
)
xgb_return.fit(X_tr_s, y_tr)
y_pred_ret = xgb_return.predict(X_te_s)
y_prob_ret = xgb_return.predict_proba(X_te_s)[:, 1]
evaluate("Return Fraud Detector", y_te, y_pred_ret, y_prob_ret)

joblib.dump({"model": xgb_return, "scaler": scaler_ret}, MODELS_DIR / "return_fraud_model.joblib")
print("   ✅ Saved: return_fraud_model.joblib")

print("\n" + "=" * 60)
print("  ✅ Core User/Return models successfully retrained.")
print("=" * 60)
