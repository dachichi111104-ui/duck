"""
Tracking placeholder — seam for future ByteTrack / DeepSORT integration.

DEMO ONLY. Does not perform any real multi-object tracking.
Tracking scope, per project spec, is intra-video only (no long-term
re-identification across videos/sessions).
"""
from __future__ import annotations

from app.ai.ai_service import AIDetection


class TrackingPlaceholder:
    MODEL_NAME = "ByteTrack / DeepSORT (not integrated)"

    def track(self, detections: list[AIDetection]) -> list[AIDetection]:
        # NOT IMPLEMENTED IN THIS PHASE — passes detections through unchanged.
        return detections
