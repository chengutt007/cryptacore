"""
Pricing Intelligence Engine — Fraud Detection through Price Anomalies
Detects abnormal pricing patterns, promo abuse, and high-value return fraud.
"""
import numpy as np
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "saved_models"


class PricingIntelligence:
    """
    Analyze pricing patterns to detect fraud:
    - Abnormally low-price orders (potential promo abuse or bulk fraud)
    - High-value returns (expensive items returned at high rates)
    - Repeated use of promo codes across multiple orders
    - Price volatility vs user order patterns
    """
    
    PRICING_FLAGS = {
        "bulk_low_price": "Multiple orders with abnormally low unit prices",
        "high_value_returns": "High-value items (>$200) returned at suspicious rate",
        "promo_abuse": "Excessive use of promo codes generating high discounts",
        "discount_spike": "Sudden large discounts on previously full-price items",
        "average_order_value_low": "Order values significantly below product average",
        "refund_exceeds_paid": "Total refunded exceeds reasonable purchase amounts",
    }

    def __init__(self):
        self.scaler = None
        self._load_model()

    def _load_model(self):
        """Load pricing model if available"""
        try:
            import joblib
            model_path = MODELS_DIR / "pricing_model.joblib"
            if model_path.exists():
                bundle = joblib.load(model_path)
                self.scaler = bundle.get("scaler")
        except Exception:
            pass

    def _calculate_pricing_score(self, features: dict) -> float:
        """
        Heuristic scoring based on pricing features.
        Returns: 0-1 fraud probability
        """
        score = 0.0
        
        # Abnormally low price purchasing
        avg_order_value = features.get("avg_order_value", 50)
        min_observed_price = features.get("min_observed_price", avg_order_value * 0.7)
        if avg_order_value > 0 and min_observed_price < avg_order_value * 0.5:
            score += 0.15 * (1 - (min_observed_price / avg_order_value))
        
        # High-value return rate
        high_value_returns = features.get("high_value_return_count", 0)
        total_returns = features.get("total_returns", 1)
        if total_returns > 0:
            high_value_return_rate = high_value_returns / total_returns
            if high_value_return_rate > 0.3:
                score += 0.20 * high_value_return_rate
        
        # Promo code abuse
        promo_usage_count = features.get("promo_abuse_count", 0)
        total_orders = features.get("total_orders", 1)
        if total_orders > 0:
            promo_rate = promo_usage_count / total_orders
            if promo_rate > 0.5:
                score += 0.15 * min(1.0, promo_rate - 0.5)
        
        # Cumulative discount amount
        total_discount = features.get("total_discount_amount", 0)
        total_revenue = features.get("avg_order_value", 50) * max(total_orders, 1)
        if total_revenue > 0:
            discount_rate = total_discount / total_revenue
            if discount_rate > 0.4:
                score += 0.20 * min(1.0, discount_rate - 0.4)
        
        # Refund exceeds spent
        total_refunded = features.get("total_refunded_amount", 0)
        estimated_spent = features.get("avg_order_value", 50) * max(total_orders, 1)
        if estimated_spent > 0 and total_refunded > estimated_spent * 0.8:
            score += 0.15
        
        # Account age with high spending
        account_age = features.get("account_age_days", 365)
        if account_age < 30 and features.get("total_orders", 0) > 10:
            velocity_score = min(1.0, features.get("total_orders", 0) / 30 * account_age / 100)
            score += 0.15 * velocity_score
        
        return min(1.0, score)

    def _detect_pricing_flags(self, features: dict) -> list[str]:
        """Identify specific pricing fraud patterns"""
        flags = []
        
        if features.get("min_observed_price", float('inf')) < features.get("avg_order_value", 50) * 0.45:
            flags.append(self.PRICING_FLAGS["bulk_low_price"])
        
        if features.get("high_value_return_count", 0) > 2:
            flags.append(self.PRICING_FLAGS["high_value_returns"])
        
        if features.get("promo_abuse_count", 0) > 3:
            flags.append(self.PRICING_FLAGS["promo_abuse"])
        
        if features.get("avg_discount_pct", 0) > 0.3 and features.get("total_orders", 0) > 5:
            flags.append(self.PRICING_FLAGS["discount_spike"])
        
        avg_order = features.get("avg_order_value", 50)
        base_price = features.get("base_price_avg", 100)
        if avg_order > 0 and base_price > 0 and avg_order < base_price * 0.5:
            flags.append(self.PRICING_FLAGS["average_order_value_low"])
        
        if features.get("total_refunded_amount", 0) > features.get("avg_order_value", 50) * features.get("total_orders", 1) * 0.7:
            flags.append(self.PRICING_FLAGS["refund_exceeds_paid"])
        
        return list(dict.fromkeys(flags))[:4]

    def analyze(self, features: dict) -> dict:
        """
        Analyze pricing patterns and generate fraud risk score.
        
        Expected features:
        - avg_order_value: average order value
        - total_orders: number of orders
        - total_returns: number of returns
        - high_value_return_count: returns of items >$200
        - promo_abuse_count: use of promo codes
        - total_discount_amount: total $ discounted
        - total_refunded_amount: total $ refunded
        - account_age_days: age of account
        - min_observed_price: lowest price paid
        - base_price_avg: average product base price
        - avg_discount_pct: average discount percentage
        """
        fraud_probability = self._calculate_pricing_score(features)
        flags = self._detect_pricing_flags(features)
        
        # Convert to 0-100 risk score
        risk_score = round(fraud_probability * 100, 1)
        
        if risk_score >= 70:
            label = "HIGH"
        elif risk_score >= 40:
            label = "MEDIUM"
        else:
            label = "LOW"
        
        return {
            "risk_score": risk_score,
            "label": label,
            "fraud_probability": round(fraud_probability, 4),
            "flags": flags if flags else ["No pricing anomalies detected"],
            "pricing_features": {
                "avg_order_value": features.get("avg_order_value", 0),
                "total_discount_amount": features.get("total_discount_amount", 0),
                "total_refunded_amount": features.get("total_refunded_amount", 0),
                "promo_abuse_count": features.get("promo_abuse_count", 0),
            }
        }


class InventoryIntelligence:
    """
    Analyze inventory patterns to detect fraud:
    - Returned items that differ from sent items
    - Stock mismatches linked to returns
    - Repeated returns of out-of-stock items
    - Warehouse inventory anomalies
    """
    
    INVENTORY_FLAGS = {
        "stock_mismatch": "Returned quantity exceeds available stock for product",
        "item_condition_mismatch": "Returned items show different condition than recorded",
        "repeat_high_return_product": "Product has abnormally high return rate",
        "warehouse_anomaly": "Inventory quantity mismatches across warehouses",
        "packaging_issue": "Returns missing original packaging at abnormal rate",
    }

    def __init__(self):
        pass

    def _detect_inventory_flags(self, features: dict) -> list[str]:
        """Identify specific inventory anomalies"""
        flags = []
        
        if features.get("returned_qty_vs_available", 0) > 0.8:
            flags.append(self.INVENTORY_FLAGS["stock_mismatch"])
        
        if features.get("item_condition_variance", 0) > 0.5:
            flags.append(self.INVENTORY_FLAGS["item_condition_mismatch"])
        
        if features.get("product_return_rate", 0) > 0.5:
            flags.append(self.INVENTORY_FLAGS["repeat_high_return_product"])
        
        if features.get("warehouse_quantity_variance", 0) > 30:
            flags.append(self.INVENTORY_FLAGS["warehouse_anomaly"])
        
        if features.get("returns_without_packaging_pct", 0) > 0.4:
            flags.append(self.INVENTORY_FLAGS["packaging_issue"])
        
        return list(dict.fromkeys(flags))[:3]

    def _calculate_inventory_score(self, features: dict) -> float:
        """Calculate inventory-based fraud risk"""
        score = 0.0
        
        # Stock mismatch risk
        if features.get("returned_qty_vs_available", 0) > 0.8:
            score += 0.25
        
        # Item condition issues
        if features.get("item_condition_variance", 0) > 0.5:
            score += 0.20
        
        # High product return rate
        if features.get("product_return_rate", 0) > 0.6:
            score += 0.20
        
        # Warehouse variance
        warehouse_var = features.get("warehouse_quantity_variance", 0)
        if warehouse_var > 30:
            score += min(0.15, warehouse_var / 100 * 0.15)
        
        # Packaging issues
        if features.get("returns_without_packaging_pct", 0) > 0.4:
            score += 0.10
        
        return min(1.0, score)

    def analyze(self, features: dict) -> dict:
        """Analyze inventory patterns and generate fraud risk"""
        fraud_probability = self._calculate_inventory_score(features)
        flags = self._detect_inventory_flags(features)
        
        risk_score = round(fraud_probability * 100, 1)
        
        if risk_score >= 70:
            label = "HIGH"
        elif risk_score >= 40:
            label = "MEDIUM"
        else:
            label = "LOW"
        
        return {
            "risk_score": risk_score,
            "label": label,
            "fraud_probability": round(fraud_probability, 4),
            "flags": flags if flags else ["No inventory anomalies detected"],
            "inventory_features": {
                "product_return_rate": features.get("product_return_rate", 0),
                "warehouse_quantity_variance": features.get("warehouse_quantity_variance", 0),
                "item_condition_variance": features.get("item_condition_variance", 0),
            }
        }
