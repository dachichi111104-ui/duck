from app.ai.ai_service import get_ai_service, PlaceholderAIService, AIAnalysisResult
from app.config.constants import AISessionStatus


def test_get_ai_service_returns_valid_service():
    from app.ai.ai_service import AIServiceBase
    service = get_ai_service()
    assert isinstance(service, AIServiceBase)


def test_placeholder_analyze_video_returns_simulated_detections():
    service = PlaceholderAIService()
    result: AIAnalysisResult = service.analyze_video("nonexistent_video.mp4")

    assert result.status == AISessionStatus.PLACEHOLDER_DONE
    assert len(result.tracks) == 3
    assert len(result.detections) > 0
    assert len(result.alerts) > 0
    assert result.summary["detection"] == "YOLOv8-Simulated"


def test_video_metadata_missing_file():
    from app.ai.video_processor import extract_metadata

    metadata = extract_metadata("does_not_exist.mp4")
    assert metadata.valid is False
    assert metadata.error is not None


def test_detection_and_tracking_placeholders_are_inert():
    from app.ai.detection_placeholder import DetectionPlaceholder
    from app.ai.tracking_placeholder import TrackingPlaceholder

    assert DetectionPlaceholder().detect("video.mp4") == []
    assert TrackingPlaceholder().track([]) == []
