"""
Pydantic request/response schemas for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────
# Review Schemas
# ──────────────────────────────────────
class ReviewAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=5000, description="Review text to analyze")
    user_id: Optional[str] = None
    product_id: Optional[str] = None


class ReviewAnalyzeResponse(BaseModel):
    label: str
    confidence: float
    risk_score: float
    reasons: List[str]
    word_count: int
    text_length: int


# ──────────────────────────────────────
# Return Fraud Schemas
# ──────────────────────────────────────
class ReturnEvaluateRequest(BaseModel):
    user_id: str
    return_rate: float = Field(0.0, ge=0, le=1)
    total_returns: int = Field(0, ge=0)
    total_orders: int = Field(1, ge=1)
    avg_days_to_return: float = Field(0.0, ge=0)
    returns_near_deadline_ratio: float = Field(0.0, ge=0, le=1)
    refund_abuse_count: int = Field(0, ge=0)
    refund_total_amount: float = Field(0.0, ge=0)
    avg_refund_value: float = Field(0.0, ge=0)
    high_value_return_count: int = Field(0, ge=0)
    items_returned_damaged: int = Field(0, ge=0)
    damaged_return_rate: float = Field(0.0, ge=0, le=1)
    no_original_packaging_count: int = Field(0, ge=0)
    consecutive_return_orders: int = Field(0, ge=0)
    same_item_return_count: int = Field(0, ge=0)
    cross_account_return_flag: int = Field(0, ge=0, le=1)
    account_age_days: int = Field(365, ge=0)
    avg_order_value: float = Field(50.0, ge=0)
    dispute_count: int = Field(0, ge=0)


class ReturnEvaluateResponse(BaseModel):
    user_id: str
    risk_score: float
    label: str
    fraud_probability: float
    explanation: List[str]
    fraud_subtypes: List[dict] = []
    fraud_subtype_count: int = 0
    return_rate_pct: float = 0.0
    total_refunded_amount: float = 0.0
    features_analyzed: List[str]


# ──────────────────────────────────────
# User Risk Schemas
# ──────────────────────────────────────
class UserRiskRequest(BaseModel):
    user_id: str
    # Behavior features
    login_frequency_per_day: float = 1.0
    session_duration_avg_sec: float = 300.0
    off_hours_login_ratio: float = 0.0
    ip_changes_30d: int = 0
    device_changes_30d: int = 0
    unique_countries_30d: int = 1
    vpn_proxy_sessions_ratio: float = 0.0
    orders_per_day: float = 0.5
    order_velocity_spike: int = 0
    cart_abandonment_rate: float = 0.2
    promo_abuse_count: int = 0
    unique_shipping_addresses: int = 1
    failed_payment_attempts: int = 0
    account_age_days: int = 365
    # Return features
    return_rate: float = 0.0
    total_returns: int = 0
    total_orders: int = 10
    refund_total_amount: float = 0.0
    refund_abuse_count: int = 0
    items_returned_damaged: int = 0
    returns_near_deadline_ratio: float = 0.0
    consecutive_return_orders: int = 0
    avg_days_to_return: float = 7.0
    avg_order_value: float = 50.0
    dispute_count: int = 0
    # Pricing features (optional)
    high_value_return_count: int = 0
    total_discount_amount: float = 0.0
    min_observed_price: float = 0.0
    base_price_avg: float = 0.0
    avg_discount_pct: float = 0.0
    # Inventory features (optional)
    product_return_rate: float = 0.0
    returned_qty_vs_available: float = 0.0
    item_condition_variance: float = 0.0
    warehouse_quantity_variance: float = 0.0
    returns_without_packaging_pct: float = 0.0


class UserRiskResponse(BaseModel):
    user_id: str
    crypta_risk_score: float
    risk_level: str
    recommended_action: str
    component_scores: dict
    behavior_signals: dict = {}
    user_profile: dict = {}  # Added for auto-filling fields
    top_contributors: List[dict]
    explanation: List[str]
    is_flagged: bool




class FlaggedUserItem(BaseModel):
    user_id: str
    crypta_risk_score: float
    risk_level: str
    is_flagged: bool
    last_analyzed: datetime
    top_risk_factor: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────
# Pricing & Inventory Schemas
# ──────────────────────────────────────
class PricingAnalyzeRequest(BaseModel):
    user_id: str
    avg_order_value: float = Field(50.0, ge=0)
    total_orders: int = Field(1, ge=1)
    total_returns: int = Field(0, ge=0)
    high_value_return_count: int = Field(0, ge=0)
    promo_abuse_count: int = Field(0, ge=0)
    total_discount_amount: float = Field(0.0, ge=0)
    total_refunded_amount: float = Field(0.0, ge=0)
    account_age_days: int = Field(365, ge=0)
    min_observed_price: float = Field(0.0, ge=0)
    base_price_avg: float = Field(100.0, ge=0)
    avg_discount_pct: float = Field(0.1, ge=0, le=1)


class PricingAnalyzeResponse(BaseModel):
    user_id: str
    risk_score: float
    label: str
    fraud_probability: float
    flags: List[str]
    pricing_features: dict


class InventoryAnalyzeRequest(BaseModel):
    user_id: str
    total_returns: int = Field(0, ge=0)
    product_return_rate: float = Field(0.0, ge=0, le=1)
    returned_qty_vs_available: float = Field(0.0, ge=0)
    item_condition_variance: float = Field(0.0, ge=0, le=1)
    warehouse_quantity_variance: float = Field(0.0, ge=0)
    returns_without_packaging_pct: float = Field(0.0, ge=0, le=1)


class InventoryAnalyzeResponse(BaseModel):
    user_id: str
    risk_score: float
    label: str
    fraud_probability: float
    flags: List[str]
    inventory_features: dict


# ──────────────────────────────────────
# Payment Schemas
# ──────────────────────────────────────
class PaymentAnalyzeRequest(BaseModel):
    user_id: str
    order_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    amount_vs_user_avg_ratio: float = 1.0
    failed_attempts_24h: int = 0
    payment_method_changes_7d: int = 0
    geo_mismatch: int = Field(0, ge=0, le=1)
    time_since_last_payment_hours: float = 24.0
    card_bin_risk: float = Field(0.1, ge=0, le=1)
    is_new_payment_method: int = Field(0, ge=0, le=1)
    vpn_detected: int = Field(0, ge=0, le=1)
    transaction_hour: int = Field(12, ge=0, le=23)


class PaymentAnalyzeResponse(BaseModel):
    user_id: str
    order_id: Optional[str]
    verdict: str
    fraud_probability: float
    risk_score: float
    flags: List[str]
    amount: float
    transaction_hour: int


# ──────────────────────────────────────
# Dashboard Schemas
# ──────────────────────────────────────
class DashboardStats(BaseModel):
    total_users_analyzed: int
    flagged_users: int
    total_reviews_analyzed: int
    fake_reviews_detected: int
    total_orders_analyzed: int
    suspicious_orders: int
    avg_crypta_risk_score: float
    alerts_today: int
    fraud_breakdown: dict


class SuspiciousOrderItem(BaseModel):
    order_id: str
    user_id: str
    amount: float
    fraud_risk_score: float
    payment_fraud_score: float
    is_returned: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginItem(BaseModel):
    login_time: datetime
    ip_address: str
    device_id: str
    location: Optional[str] = None
    is_suspicious: bool

    class Config:
        from_attributes = True


class DeviceItem(BaseModel):
    device_id: str
    device_type: str
    os: str
    browser: str
    last_used: datetime
    is_new_device: bool

    class Config:
        from_attributes = True


class OrderItemSchema(BaseModel):
    order_id: str
    amount: float
    fraud_risk_score: float
    is_suspicious: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReturnItemSchema(BaseModel):
    return_id: str
    order_id: str
    return_reason: Optional[str] = None
    item_condition: str
    refund_amount: float
    days_to_return: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserFullResponse(BaseModel):
    """Combined user data + live-computed risk for GET /users/{id}/full"""
    # Core user info
    user_id: str
    email: Optional[str] = None
    account_age_days: int
    created_at: Optional[datetime] = None
    is_flagged: bool

    # Related data
    orders: List[OrderItemSchema] = []
    returns: List[ReturnItemSchema] = []
    login_history: List[LoginItem] = []
    device_history: List[DeviceItem] = []

    # Computed risk
    risk_score: float
    risk_level: str
    fraud_reasons: List[str] = []
    component_scores: dict = {}
    top_contributors: List[dict] = []
    recommended_action: str = ""

    # Live-computed profile stats
    user_profile: dict = {}
