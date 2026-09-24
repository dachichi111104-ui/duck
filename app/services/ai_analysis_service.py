from __future__ import annotations

import datetime as dt

from app.database.connection import session_scope
from app.database.models import AIAnalysisSession, AIDetectionResult, AIAlert, Notification
from app.repositories.ai_repository import AISessionRepository, AIDetectionRepository, AIAlertRepository
from app.ai.ai_service import get_ai_service
from app.ai.video_processor import extract_metadata, VideoMetadata
from app.utils.logger import log_action, get_logger
from app.config.constants import AlertStatus, AlertSeverity, AlertType

logger = get_logger("ai_analysis_service")


class AIAnalysisService:
    def __init__(self) -> None:
        self._session_repo = AISessionRepository()
        self._detection_repo = AIDetectionRepository()
        self._alert_repo = AIAlertRepository()
        self._ai_service = get_ai_service()

    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        return extract_metadata(video_path)

    def run_analysis(self, actor: str, video_path: str, metadata: VideoMetadata) -> AIAnalysisSession:
        result = self._ai_service.analyze_video(video_path)

        with session_scope() as session:
            ai_session = AIAnalysisSession(
                video_path=video_path,
                file_name=metadata.file_name,
                duration=metadata.duration_seconds,
                resolution=metadata.resolution,
                fps=metadata.fps,
                completed_at=dt.datetime.now(),
                status=result.status,
                model_version=result.model_version,
                notes=result.message,
            )
            self._session_repo.add(session, ai_session)

            for det in result.detections:
                self._detection_repo.add(session, AIDetectionResult(
                    session_id=ai_session.id, track_id=det.track_id, timestamp=det.timestamp,
                    bbox_x=det.bbox[0] if det.bbox else None,
                    bbox_y=det.bbox[1] if det.bbox else None,
                    bbox_width=det.bbox[2] if det.bbox else None,
                    bbox_height=det.bbox[3] if det.bbox else None,
                    confidence=det.confidence, behavior_label=det.behavior_label,
                    health_status=det.health_status, notes=det.notes,
                ))

            for alert in result.alerts:
                self._alert_repo.add(session, AIAlert(
                    session_id=ai_session.id, track_id=alert.track_id,
                    alert_type=alert.alert_type, severity=alert.severity,
                    timestamp=alert.timestamp, description=alert.description,
                ))

            session.flush()  # ai_session.id is now populated

            # Always raise a green "analysis completed" notification so the
            # Notification Center reflects that the placeholder ran.
            session.add(Notification(
                alert_type=AlertType.VIDEO_ANALYSIS_DONE,
                severity=AlertSeverity.GREEN,
                title="Phân tích video hoàn thành",
                message=f"Đã xử lý video '{metadata.file_name}' (AI placeholder).",
                reference_type="ai_session",
                reference_id=ai_session.id,
                status=AlertStatus.UNREAD,
            ))

            session.flush()
            session.expunge(ai_session)

        log_action(actor, "AI_ANALYZE_VIDEO", metadata.file_name)
        return ai_session

    def list_sessions(self) -> list[AIAnalysisSession]:
        with session_scope() as session:
            sessions = self._session_repo.get_all(session)
            session.expunge_all()
            return sessions

    def get_session_alerts(self, session_id: int) -> list[AIAlert]:
        with session_scope() as session:
            alerts = self._alert_repo.get_for_session(session, session_id)
            session.expunge_all()
            return alerts
