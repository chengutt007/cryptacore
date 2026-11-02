"""
Model Registry — singleton that loads all ML models at startup.
"""
import sys
from pathlib import Path

ML_PATH = Path(__file__).parent.parent / "ml"
sys.path.insert(0, str(ML_PATH))


class ModelRegistry:
    def __init__(self):
        self._ready = False
        self.review_detector = None
        self.return_detector = None
        self.behavior_analyzer = None
        self.payment_detector = None
        self.pricing_intelligence = None
        self.inventory_intelligence = None

    def load_all(self):
        try:
            from models.fake_review_detector import FakeReviewDetector
            from models.return_fraud_detector import ReturnFraudDetector
            from models.user_behavior_analyzer import UserBehaviorAnalyzer
            from models.payment_fraud_detector import PaymentFraudDetector
            from models.pricing_intelligence import PricingIntelligence, InventoryIntelligence

            self.review_detector = FakeReviewDetector()
            self.return_detector = ReturnFraudDetector()
            self.behavior_analyzer = UserBehaviorAnalyzer()
            self.payment_detector = PaymentFraudDetector()
            self.pricing_intelligence = PricingIntelligence()
            self.inventory_intelligence = InventoryIntelligence()
            self._ready = True
            print("[OK] All ML models loaded into registry")
        except Exception as e:
            print(f"[WARN] Model loading error: {e}. Running in demo mode.")
            self._ready = False

    def is_ready(self) -> bool:
        return self._ready
