"""
Behavior classifier placeholder — seam for future Random Forest / MLP model.

Target classes (per project spec):
  - Bệnh mục tiêu: Lật ngửa, Tụ huyết trùng
  - Nhãn tổng: Có bệnh / Không bệnh

DEMO ONLY. Does not classify anything.
"""
from __future__ import annotations


class ClassifierPlaceholder:
    MODEL_NAME = "RandomForest/MLP (not integrated)"
    TARGET_DISEASES = ["Lật ngửa", "Tụ huyết trùng"]
    LABELS = ["Không bệnh", "Có bệnh"]

    def classify(self, features: list[dict]) -> list[str]:
        # NOT IMPLEMENTED IN THIS PHASE.
        return []
