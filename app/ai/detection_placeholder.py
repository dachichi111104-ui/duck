"""
Detection placeholder — seam for future YOLOv8 / Ultralytics integration.

DEMO ONLY. Returns no detections. Kept as its own module (rather than
folded into ai_service.py) so that swapping in a real detector later is
a matter of replacing this file's implementation and importing a
correspondingly real class from ai_service.py's RealAIService.
"""
from __future__ import annotations

from app.ai.ai_service import AIDetection


class DetectionPlaceholder:
    """
    Future: wraps a YOLOv8 (Ultralytics) model loaded from a .pt checkpoint
    and yields per-frame bounding boxes + confidences for duck instances.
    """

    MODEL_NAME = "YOLOv8 (not integrated)"

    def detect(self, video_path: str) -> list[AIDetection]:
        # NOT IMPLEMENTED IN THIS PHASE — intentionally returns an empty list.
        return []
