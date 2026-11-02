"""
Fake Review Detector — Inference Module
Uses TF-IDF + Logistic Regression (fast) or DistilBERT (accurate).
"""
import re
import joblib
import numpy as np
from pathlib import Path
from typing import Optional

MODELS_DIR = Path(__file__).parent.parent / "saved_models"

# Suspicious patterns for rule-based pre-screening
SPAM_PATTERNS = [
    r"buy\s*now", r"best.*ever", r"amazing.*amazing", r"!!!+", r"\b(5\s*stars?){2,}",
    r"(wow\s*){2,}", r"you\s*won't\s*regret", r"life\s*changing", r"must\s*buy",
    r"(\b\w+\b)(\s+\1){3,}",  # repeated words
]

SPAM_KEYWORDS = [
    "buy now", "limited time", "click here", "don't miss", "amazing amazing",
    "best ever", "life changing", "must buy", "100% recommend", "incredible unbelievable"
]


class FakeReviewDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = MODELS_DIR / "fake_review_model.joblib"
        if model_path.exists():
            self.model = joblib.load(model_path)

    def _rule_based_flags(self, text: str) -> list[str]:
        flags = []
        text_lower = text.lower()

        if len(re.findall(r"!", text)) > 5:
            flags.append("Excessive exclamation marks")
        if len(re.findall(r"[A-Z]", text)) / max(len(text), 1) > 0.5:
            flags.append("Excessive capitalization")
        words = text.split()
        unique_ratio = len(set(words)) / max(len(words), 1)
        if unique_ratio < 0.5:
            flags.append("High word repetition detected")
        for kw in SPAM_KEYWORDS:
            if kw in text_lower:
                flags.append(f"Spam keyword: '{kw}'")
        for pat in SPAM_PATTERNS[:5]:
            if re.search(pat, text_lower):
                flags.append("Suspicious phrase pattern detected")
                break
        if len(text) < 20:
            flags.append("Review too short to be genuine")
        word_count = len(words)
        if word_count > 5:
            positive_words = ["amazing", "perfect", "best", "love", "incredible", "fantastic", "excellent", "outstanding"]
            pos_count = sum(1 for w in words if w.lower() in positive_words)
            if pos_count / word_count > 0.4:
                flags.append("Unusually high density of superlative words")

        return list(set(flags))[:5]

    def analyze(self, text: str) -> dict:
        flags = self._rule_based_flags(text)

        if self.model is not None:
            prob = self.model.predict_proba([text])[0]
            fake_prob = float(prob[1])
            is_fake = fake_prob > 0.5
        else:
            # Fallback heuristic if model not trained yet
            fake_prob = min(1.0, len(flags) * 0.25)
            is_fake = fake_prob > 0.5

        # Boost confidence if rule-based flags also triggered
        if flags and fake_prob > 0.4:
            fake_prob = min(1.0, fake_prob * 1.1)

        risk_score = round(fake_prob * 100, 1)

        return {
            "label": "FAKE" if is_fake else "GENUINE",
            "confidence": round(fake_prob if is_fake else 1 - fake_prob, 4),
            "risk_score": risk_score,
            "reasons": flags if is_fake else ["No suspicious patterns detected"],
            "word_count": len(text.split()),
            "text_length": len(text)
        }
