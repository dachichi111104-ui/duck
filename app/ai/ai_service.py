"""
AI Service interface.

This is the seam where the Computer Vision course project will plug in
a real YOLOv8 + ByteTrack + behavior-classification pipeline later.

Usage from the rest of the app:

    from app.ai.ai_service import get_ai_service
    service = get_ai_service()
    result = service.analyze_video(video_path)

Swapping `PlaceholderAIService` for a future `RealAIService` requires no
change anywhere else in the codebase — only `get_ai_service()` below
needs to point at the new implementation.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class AIDetection:
    """One placeholder/real detection record (mirrors ai_detection_results table)."""
    track_id: int | None = None
    timestamp: float | None = None
    bbox: tuple[float, float, float, float] | None = None  # x, y, w, h
    confidence: float | None = None
    behavior_label: str | None = None
    health_status: str | None = None  # NORMAL | SUSPECTED
    notes: str | None = None


@dataclass
class AIAlertResult:
    track_id: int | None
    alert_type: str
    severity: str
    timestamp: float | None
    description: str


@dataclass
class AIAnalysisResult:
    """Return value of AIService.analyze_video()."""
    model_version: str
    status: str  # matches AISessionStatus
    detections: list[AIDetection] = field(default_factory=list)
    alerts: list[AIAlertResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    message: str = ""


class AIService(abc.ABC):
    """Abstract base — both the placeholder and any future real model implement this."""

    @abc.abstractmethod
    def analyze_video(self, video_path: str) -> AIAnalysisResult:
        """Run (or simulate) detection + tracking + behavior analysis on a video file."""
        raise NotImplementedError


class PlaceholderAIService(AIService):
    """
    DEMO ONLY. No real model is loaded or executed.

    This exists purely so the rest of the system (UI, database schema,
    session/history screens, alerts) can be built and demoed end-to-end
    before the Computer Vision pipeline is integrated. It NEVER claims to
    have performed real detection.
    """

    MODEL_VERSION = "PLACEHOLDER-0.1"

    def analyze_video(self, video_path: str) -> AIAnalysisResult:
        from app.config.constants import AISessionStatus
        return AIAnalysisResult(
            model_version=self.MODEL_VERSION,
            status=AISessionStatus.PLACEHOLDER_DONE,
            detections=[],
            alerts=[],
            summary={
                "total_individuals": None,
                "normal_individuals": None,
                "suspected_individuals": None,
                "detection": "Chưa tích hợp",
                "tracking": "Chưa tích hợp",
                "behavior_classifier": "Chưa tích hợp",
            },
            message="AI MODULE\n\nModel: Chưa tích hợp\nDetection: Chưa tích hợp\n"
                    "Tracking: Chưa tích hợp\nBehavior Classifier: Chưa tích hợp\n\n"
                    "Trạng thái: READY FOR AI INTEGRATION",
        )


def get_ai_service() -> AIService:
    """
    Factory used everywhere the app needs an AI service.

    Swap this single line to `return RealAIService()` once the Computer
    Vision pipeline (YOLOv8 + ByteTrack + Random Forest/MLP) is ready —
    no other file needs to change.
    """
    return PlaceholderAIService()
