"""
Synthetic Data Generator for Crypta Core AI (v2)
Enhanced for deep return fraud and user behavior analysis.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import random

np.random.seed(42)
random.seed(42)

DATA_DIR = Path(__file__).parent / "training_data"
DATA_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# 1. USER BEHAVIOR DATASET (Enhanced - 500+ users)
# ──────────────────────────────────────────────
def generate_user_behavior(is_suspicious):
    if is_suspicious:
        return {
            "login_frequency_per_day": round(random.uniform(15, 60), 1),
            "session_duration_avg_sec": round(random.uniform(5, 60), 1),
            "off_hours_login_ratio": round(random.uniform(0.7, 1.0), 2),
            "ip_changes_30d": random.randint(10, 40),
            "device_changes_30d": random.randint(5, 15),
            "unique_countries_30d": random.randint(2, 8),
            "vpn_proxy_sessions_ratio": round(random.uniform(0.8, 1.0), 2),
            "orders_per_day": round(random.uniform(5, 25), 1),
            "order_velocity_spike": random.randint(15, 50),
            "cart_abandonment_rate": round(random.uniform(0.8, 1.0), 2),
            "promo_abuse_count": random.randint(5, 20),
            "unique_shipping_addresses": random.randint(5, 20),
            "return_rate": round(random.uniform(0.7, 1.0), 2),
            "total_returns": random.randint(20, 100),
            "refund_total_amount": round(random.uniform(2000, 20000), 2),
            "items_returned_damaged": random.randint(10, 30),
            "returns_near_deadline_ratio": round(random.uniform(0.7, 1.0), 2),
            "consecutive_return_orders": random.randint(5, 20),
            "account_age_days": random.randint(0, 30),
            "failed_payment_attempts": random.randint(5, 30),
            "label": 1
        }
    else:
        return {
            "login_frequency_per_day": round(random.uniform(0.1, 3), 1),
            "session_duration_avg_sec": round(random.uniform(120, 900), 1),
            "off_hours_login_ratio": round(random.uniform(0.0, 0.2), 2),
            "ip_changes_30d": random.randint(0, 2),
            "device_changes_30d": random.randint(0, 1),
            "unique_countries_30d": 1,
            "vpn_proxy_sessions_ratio": round(random.uniform(0.0, 0.1), 2),
            "orders_per_day": round(random.uniform(0.05, 1.5), 1),
            "order_velocity_spike": random.randint(0, 3),
            "cart_abandonment_rate": round(random.uniform(0.1, 0.4), 2),
            "promo_abuse_count": random.randint(0, 1),
            "unique_shipping_addresses": random.randint(1, 3),
            "return_rate": round(random.uniform(0.0, 0.2), 2),
            "total_returns": random.randint(0, 5),
            "refund_total_amount": round(random.uniform(0, 300), 2),
            "items_returned_damaged": random.randint(0, 1),
            "returns_near_deadline_ratio": round(random.uniform(0.0, 0.2), 2),
            "consecutive_return_orders": random.randint(0, 1),
            "account_age_days": random.randint(90, 1800),
            "failed_payment_attempts": random.randint(0, 1),
            "label": 0
        }

# 500+ users: ~100 suspicious, ~400 legitimate
behavior_samples = [generate_user_behavior(True) for _ in range(1200)] + \
                   [generate_user_behavior(False) for _ in range(3800)]
df_behavior = pd.DataFrame(behavior_samples).sample(frac=1).reset_index(drop=True)
df_behavior.to_csv(DATA_DIR / "user_behavior.csv", index=False)
print(f"✅ Enhanced User behavior dataset: {len(df_behavior)} samples (500+ users)")

# ──────────────────────────────────────────────
# 2. RETURN FRAUD DATASET (Enhanced - 2000+ orders)
# ──────────────────────────────────────────────
def generate_return_sample(is_fraud):
    if is_fraud:
        fraud_type = random.choice(["excessive", "damaged", "refund", "deadline", "fake"])
        
        base = {
            "return_rate": round(random.uniform(0.6, 1.0), 2),
            "total_returns": random.randint(10, 50),
            "total_orders": random.randint(10, 60),
            "avg_days_to_return": round(random.uniform(20, 30), 1),
            "returns_near_deadline_ratio": round(random.uniform(0.5, 1.0), 2),
            "refund_abuse_count": random.randint(1, 10),
            "refund_total_amount": round(random.uniform(1000, 15000), 2),
            "avg_refund_value": round(random.uniform(50, 500), 2),
            "high_value_return_count": random.randint(2, 10),
            "items_returned_damaged": random.randint(1, 10),
            "damaged_return_rate": round(random.uniform(0.2, 0.8), 2),
            "no_original_packaging_count": random.randint(1, 8),
            "consecutive_return_orders": random.randint(3, 12),
            "same_item_return_count": random.randint(1, 5),
            "cross_account_return_flag": random.choice([0, 1]),
            "account_age_days": random.randint(5, 90),
            "avg_order_value": round(random.uniform(100, 1000), 2),
            "dispute_count": random.randint(1, 5),
            "label": 1
        }
        
        # Exaggerate features based on subtype
        if fraud_type == "excessive":
            base["return_rate"] = random.uniform(0.8, 1.0)
            base["total_returns"] = random.randint(30, 100)
        elif fraud_type == "damaged":
            base["items_returned_damaged"] = random.randint(8, 20)
            base["damaged_return_rate"] = random.uniform(0.6, 1.0)
        elif fraud_type == "refund":
            base["refund_abuse_count"] = random.randint(5, 15)
            base["refund_total_amount"] = random.uniform(5000, 25000)
            base["dispute_count"] = random.randint(3, 10)
        elif fraud_type == "deadline":
            base["returns_near_deadline_ratio"] = random.uniform(0.8, 1.0)
            base["avg_days_to_return"] = random.uniform(28, 30)
        elif fraud_type == "fake":
            base["cross_account_return_flag"] = 1
            base["consecutive_return_orders"] = random.randint(8, 20)
            base["account_age_days"] = random.randint(1, 14)
            
        return base
    else:
        total_orders = random.randint(2, 100)
        total_returns = random.randint(0, int(total_orders * 0.2))
        return {
            "return_rate": round(total_returns / max(total_orders, 1), 2),
            "total_returns": total_returns,
            "total_orders": total_orders,
            "avg_days_to_return": round(random.uniform(1, 15), 1),
            "returns_near_deadline_ratio": round(random.uniform(0.0, 0.2), 2),
            "refund_abuse_count": 0,
            "refund_total_amount": round(random.uniform(0, 300), 2),
            "avg_refund_value": round(random.uniform(10, 50), 2) if total_returns > 0 else 0,
            "high_value_return_count": random.randint(0, 1),
            "items_returned_damaged": random.randint(0, 1),
            "damaged_return_rate": round(random.uniform(0.0, 0.1), 2),
            "no_original_packaging_count": random.randint(0, 1),
            "consecutive_return_orders": random.randint(0, 1),
            "same_item_return_count": random.randint(0, 1),
            "cross_account_return_flag": 0,
            "account_age_days": random.randint(90, 1800),
            "avg_order_value": round(random.uniform(20, 200), 2),
            "dispute_count": 0,
            "label": 0
        }

# 2000+ orders: ~600 fraudulent, ~1400 legitimate
return_samples = [generate_return_sample(True) for _ in range(1800)] + \
                 [generate_return_sample(False) for _ in range(4200)]
df_returns = pd.DataFrame(return_samples).sample(frac=1).reset_index(drop=True)
df_returns.to_csv(DATA_DIR / "return_fraud.csv", index=False)
print(f"✅ Enhanced Return fraud dataset: {len(df_returns)} samples (2000+ orders)")

# ──────────────────────────────────────────────
# 3. PRODUCTS DATASET
# ──────────────────────────────────────────────
product_samples = []
for i in range(300):
    has_issue = random.random() < 0.15
    product_samples.append({
        "product_id": f"PROD_{i:05d}",
        "product_name": f"Product {i}",
        "base_price": round(random.uniform(10, 1000), 2),
        "category": random.choice(["Electronics", "Clothing", "Home", "Sports", "Books"]),
        "return_rate": round(random.uniform(0.3, 0.9), 2) if has_issue else round(random.uniform(0.01, 0.15), 2),
        "high_return_flag": 1 if has_issue else 0,
    })
df_products = pd.DataFrame(product_samples)
df_products.to_csv(DATA_DIR / "products.csv", index=False)
print(f"✅ Products dataset: {len(df_products)} products")

# ──────────────────────────────────────────────
# 4. PRICING POLICIES DATASET
# ──────────────────────────────────────────────
pricing_samples = []
for idx, row in df_products.iterrows():
    base_price = row['base_price']
    pricing_samples.append({
        "product_id": row['product_id'],
        "min_price": round(base_price * 0.7, 2),
        "max_price": round(base_price * 1.3, 2),
        "avg_price_7d": round(base_price + random.uniform(-10, 10), 2),
        "avg_discount_pct": round(random.uniform(0.05, 0.35), 2),
        "abnormal_low_price_flag": 1 if random.random() < 0.08 else 0,
    })
df_pricing = pd.DataFrame(pricing_samples)
df_pricing.to_csv(DATA_DIR / "pricing_policies.csv", index=False)
print(f"✅ Pricing policies dataset: {len(df_pricing)} records")

# ──────────────────────────────────────────────
# 5. INVENTORY DATASET
# ──────────────────────────────────────────────
inventory_samples = []
for idx, row in df_products.iterrows():
    for warehouse in ["WH_EAST", "WH_WEST", "WH_CENTRAL"]:
        inventory_samples.append({
            "product_id": row['product_id'],
            "warehouse_id": warehouse,
            "stock_quantity": random.randint(0, 500),
            "reserved_quantity": random.randint(0, 100),
        })
df_inventory = pd.DataFrame(inventory_samples)
df_inventory.to_csv(DATA_DIR / "inventory.csv", index=False)
print(f"✅ Inventory dataset: {len(df_inventory)} warehouse records")

# ──────────────────────────────────────────────
# 6. STOCK LOGS DATASET
# ──────────────────────────────────────────────
stock_log_samples = []
for _ in range(2000):
    stock_log_samples.append({
        "product_id": f"PROD_{random.randint(0, 299):05d}",
        "warehouse_id": random.choice(["WH_EAST", "WH_WEST", "WH_CENTRAL"]),
        "action": random.choice(["IN", "OUT", "RETURNED", "ADJUSTED"]),
        "quantity": random.randint(1, 50),
        "reference_id": f"ORD_{random.randint(10000, 99999)}" if random.random() > 0.3 else None,
    })
df_stock_logs = pd.DataFrame(stock_log_samples)
df_stock_logs.to_csv(DATA_DIR / "stock_logs.csv", index=False)
print(f"✅ Stock logs dataset: {len(df_stock_logs)} records")

# Keep the old fake_reviews and payment_fraud generators the same if missing
try:
    df = pd.read_csv(DATA_DIR / "fake_reviews.csv")
    print(f"✅ Preserved fake reviews dataset: {len(df)} samples")
except:
    pass

# ──────────────────────────────────────────────
# 7. LIVE USERS DATASET (Production Data — NEVER seen during training)
#    Uses a DIFFERENT seed (99) so model has never seen these users.
#    This eliminates data leakage between training and prediction.
# ──────────────────────────────────────────────
np.random.seed(99)
random.seed(99)

# 1250 suspicious + 3750 legitimate = 5000 live production users
live_samples = (
    [generate_user_behavior(True)  for _ in range(1250)] +
    [generate_user_behavior(False) for _ in range(3750)]
)
df_live = pd.DataFrame(live_samples).sample(frac=1, random_state=99).reset_index(drop=True)
df_live.to_csv(DATA_DIR / "live_users.csv", index=False)
print(f"✅ Live users dataset (production): {len(df_live)} users (seed=99, never seen by model)")
print(f"   Fraud users : {(df_live['label']==1).sum()}")
print(f"   Normal users: {(df_live['label']==0).sum()}")
