"""
ORM Models for Crypta Core AI
"""
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FraudType(str, enum.Enum):
    FAKE_REVIEW = "FAKE_REVIEW"
    RETURN_FRAUD = "RETURN_FRAUD"
    SUSPICIOUS_BEHAVIOR = "SUSPICIOUS_BEHAVIOR"
    PAYMENT_FRAUD = "PAYMENT_FRAUD"
    PRICING_ANOMALY = "PRICING_ANOMALY"
    INVENTORY_MISMATCH = "INVENTORY_MISMATCH"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), nullable=True)
    account_age_days: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_returns: Mapped[int] = mapped_column(Integer, default=0)
    total_refunded_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    promo_abuse_count: Mapped[int] = mapped_column(Integer, default=0)
    ip_changes_30d: Mapped[int] = mapped_column(Integer, default=0)
    device_changes_30d: Mapped[int] = mapped_column(Integer, default=0)
    login_frequency_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    crypta_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), default="LOW")
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    last_analyzed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    alerts: Mapped[list["FraudAlertModel"]] = relationship("FraudAlertModel", back_populates="user_ref", lazy="dynamic")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    review_text: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ReviewAnalysisModel(Base):
    __tablename__ = "review_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.id"), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))  # NORMAL, FAKE, SPAM, BOT, COMPANY_FAKE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewAlertModel(Base):
    __tablename__ = "review_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True)
    review_text: Mapped[str] = mapped_column(Text)
    risk_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))  # FAKE, SPAM, BOT, COMPANY_FAKE
    reason: Mapped[str] = mapped_column(Text, nullable=True)   # short one-liner
    detail: Mapped[str] = mapped_column(Text, nullable=True)   # full fraud-type explanation
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[float] = mapped_column(Float)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    promo_code: Mapped[str] = mapped_column(String(64), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(64), nullable=True)
    is_returned: Mapped[bool] = mapped_column(Boolean, default=False)
    fraud_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    payment_fraud_score: Mapped[float] = mapped_column(Float, default=0.0)
    pricing_fraud_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FraudAlertModel(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True)
    fraud_type: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    explanation: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user_ref: Mapped["UserModel"] = relationship("UserModel", back_populates="alerts")


# ──────────────────────────────────────────────
# Inventory & Product Models
# ──────────────────────────────────────────────
class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    base_price: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(128), nullable=True)
    return_rate: Mapped[float] = mapped_column(Float, default=0.0)
    high_return_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InventoryModel(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(String(64), index=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockLogModel(Base):
    __tablename__ = "stock_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))  # IN, OUT, RETURNED, ADJUSTED
    quantity: Mapped[int] = mapped_column(Integer)
    reference_id: Mapped[str] = mapped_column(String(64), nullable=True)  # order_id or return_id
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[str] = mapped_column(String(64), ForeignKey("orders.order_id"), index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    promo_code: Mapped[str] = mapped_column(String(64), nullable=True)
    total_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReturnedItemModel(Base):
    __tablename__ = "returned_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    return_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("order_items.id"))
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True)
    order_id: Mapped[str] = mapped_column(String(64), ForeignKey("orders.order_id"), index=True)
    return_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    item_condition: Mapped[str] = mapped_column(String(64), default="GOOD")  # GOOD, DAMAGED, MISSING_PARTS
    refund_amount: Mapped[float] = mapped_column(Float)
    restocking_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    days_to_return: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PricingPolicyModel(Base):
    __tablename__ = "pricing_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), index=True)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    avg_price_7d: Mapped[float] = mapped_column(Float)
    avg_discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    abnormal_low_price_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromoAbuseModel(Base):
    __tablename__ = "promo_abuse_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True)
    promo_code: Mapped[str] = mapped_column(String(64), index=True)
    usage_count: Mapped[int] = mapped_column(Integer)
    total_discount_amount: Mapped[float] = mapped_column(Float)
    days_active: Mapped[int] = mapped_column(Integer)
    flagged_as_abuse: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FlaggedUsersModel(Base):
    __tablename__ = "flagged_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), unique=True, index=True)
    crypta_risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))  # HIGH or CRITICAL
    primary_fraud_type: Mapped[str] = mapped_column(String(32), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    analyst_notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class LoginHistoryModel(Base):
    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True)
    login_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[str] = mapped_column(String(64))
    device_id: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(128), nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)


class DeviceHistoryModel(Base):
    __tablename__ = "device_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True)
    device_id: Mapped[str] = mapped_column(String(64))
    device_type: Mapped[str] = mapped_column(String(64)) # mobile, desktop, tablet
    os: Mapped[str] = mapped_column(String(64))
    browser: Mapped[str] = mapped_column(String(64))
    last_used: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_new_device: Mapped[bool] = mapped_column(Boolean, default=False)
