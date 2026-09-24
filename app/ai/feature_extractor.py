"""
Behavior feature extraction placeholder.

Future: computes per-track motion/pose features (e.g. posture angle,
movement speed, isolation distance from flock centroid) to feed the
Random Forest / MLP behavior classifier.
"""
from __future__ import annotations

from app.ai.ai_service import AIDetection


class FeatureExtractorPlaceholder:
    def extract(self, tracked_detections: list[AIDetection]) -> list[dict]:
        # NOT IMPLEMENTED IN THIS PHASE.
        return []
