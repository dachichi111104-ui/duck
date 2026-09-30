"""
AI Analysis Service - Business logic & Database Seam for AI pipeline results.
"""
from __future__ import annotations

import datetime as dt

from app.database.connection import session_scope
from app.database.models import (
    AIAnalysisSession, AIDetectionResult, AIAlert, Notification, Flock, VeterinaryRecord
)
from app.repositories.ai_repository import AISessionRepository, AIDetectionRepository, AIAlertRepository
from app.ai.ai_service import get_ai_service, AIAnalysisResult
from app.ai.video_processor import extract_metadata, VideoMetadata
from app.utils.logger import log_action, get_logger
from app.config.constants import AlertStatus, AlertSeverity, AlertType, VetRecordStatus

logger = get_logger("ai_analysis_service")


class AIAnalysisService:
    def __init__(self) -> None:
        self._session_repo = AISessionRepository()
        self._detection_repo = AIDetectionRepository()
        self._alert_repo = AIAlertRepository()
        self._ai_service = get_ai_service()

    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        return extract_metadata(video_path)

    def run_analysis(self, actor: str, video_path: str, metadata: VideoMetadata, flock_id: int | None = None, barn_id: int | None = None) -> AIAnalysisSession:
        """
        Executes AI analysis pipeline and runs the fully automated end-to-end workflow:
        1. Saves AI Analysis Session metadata.
        2. Persists AI Detections & Bounding Box Coordinates.
        3. Creates System Alerts & Unread Notifications.
        4. Links AI alerts directly to Veterinary Medical Records (VeterinaryRecord).
        """
        result: AIAnalysisResult = self._ai_service.analyze_video(video_path)

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

            has_sick_duck = False
            sick_details = []

            for det in result.detections:
                is_sick = (det.health_status == "Có bệnh" or "bệnh" in str(det.behavior_label).lower())
                if is_sick:
                    has_sick_duck = True
                    sick_details.append(f"Cá thể ID:{det.track_id} - {det.behavior_label}")

                self._detection_repo.add(session, AIDetectionResult(
                    session_id=ai_session.id,
                    track_id=det.track_id,
                    timestamp=det.timestamp,
                    bbox_x=det.bbox[0] if det.bbox else None,
                    bbox_y=det.bbox[1] if det.bbox else None,
                    bbox_width=det.bbox[2] if det.bbox else None,
                    bbox_height=det.bbox[3] if det.bbox else None,
                    confidence=det.confidence,
                    behavior_label=det.behavior_label,
                    health_status=det.health_status,
                    notes=det.notes,
                ))

            for alert in result.alerts:
                self._alert_repo.add(session, AIAlert(
                    session_id=ai_session.id,
                    track_id=alert.track_id,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    timestamp=alert.timestamp,
                    description=alert.description,
                ))

            session.flush()  # ai_session.id is populated

            # AUTOMATED WORKFLOW: Create Red Alert Notification & Auto-Suggest Vet Record
            if has_sick_duck or result.alerts:
                summary_str = "; ".join(sick_details[:2]) if sick_details else "Phát hiện triệu chứng té ngã / giảm vận động."
                session.add(Notification(
                    alert_type=AlertType.AI_ABNORMAL_BEHAVIOR,
                    severity=AlertSeverity.RED,
                    title="CẢNH BÁO AI: Phát hiện vịt có dấu hiệu bệnh",
                    message=f"Hệ thống AI vừa phát hiện cá thể bất thường trong video '{metadata.file_name}'. Chi tiết: {summary_str}",
                    reference_type="ai_session",
                    reference_id=ai_session.id,
                    status=AlertStatus.UNREAD,
                ))

                # Link Veterinary Record to user-selected flock or active flock fallback
                target_flock = None
                if flock_id:
                    target_flock = session.get(Flock, flock_id)
                if not target_flock:
                    target_flock = session.query(Flock).filter(Flock.status.in_(("ACTIVE", "ACTIVE", "Hoạt động"))).first()
                if not target_flock:
                    target_flock = session.query(Flock).first()
                if not target_flock:
                    target_flock = Flock(
                        flock_code="DV001",
                        name="Đàn Vịt Trời Mặc Định AI",
                        start_date=dt.date.today(),
                        initial_count=500,
                        current_count=500,
                        status="ACTIVE",
                        notes="Tự động tạo bởi hệ thống AI",
                    )
                    session.add(target_flock)
                    session.flush()

                vet_rec = VeterinaryRecord(
                    flock_id=target_flock.id,
                    diagnosis_date=dt.date.today(),
                    diagnosis="Nghi dịch bệnh / Té ngã (Phát hiện từ AI)",
                    animal_reference="1 cá thể (AI)",
                    symptoms=f"Cảnh báo AI từ video {metadata.file_name}: {summary_str}",
                    treatment="Cách ly cá thể nghi bệnh, theo dõi thân nhiệt và tiêm vắc xin bổ sung.",
                    veterinarian=actor or "Hệ thống AI tự động",
                    status=VetRecordStatus.THEO_DOI,
                    source="AI_ANALYSIS",
                    notes=f"Tự động khởi tạo từ phiên phân tích AI #{ai_session.id}",
                )
                session.add(vet_rec)
            else:
                session.add(Notification(
                    alert_type=AlertType.VIDEO_ANALYSIS_DONE,
                    severity=AlertSeverity.GREEN,
                    title="Phân tích video hoàn thành",
                    message=f"Đã phân tích xong video '{metadata.file_name}'. Đàn vịt khỏe mạnh bình thường.",
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
