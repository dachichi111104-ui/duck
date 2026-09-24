from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.config.constants import AISessionStatus


class AIAnalysisSession(Base):
    __tablename__ = "ai_analysis_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float)  # seconds
    resolution: Mapped[str | None] = mapped_column(String(30))  # e.g. 1920x1080
    fps: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default=AISessionStatus.PENDING)
    model_version: Mapped[str] = mapped_column(String(50), default="PLACEHOLDER")
    notes: Mapped[str | None] = mapped_column(String(500))

    detections: Mapped[list["AIDetectionResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AIAlert"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AIAnalysisSession {self.file_name} status={self.status}>"


class AIDetectionResult(Base):
    """
    Placeholder schema for future YOLOv8 + tracking detection results.
    Not populated with real detections in the current phase.
    """
    __tablename__ = "ai_detection_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ai_analysis_sessions.id"), nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[float | None] = mapped_column(Float)  # seconds into video
    bbox_x: Mapped[float | None] = mapped_column(Float)
    bbox_y: Mapped[float | None] = mapped_column(Float)
    bbox_width: Mapped[float | None] = mapped_column(Float)
    bbox_height: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    behavior_label: Mapped[str | None] = mapped_column(String(100))
    health_status: Mapped[str | None] = mapped_column(String(20))  # NORMAL | SUSPECTED
    notes: Mapped[str | None] = mapped_column(String(255))

    session: Mapped["AIAnalysisSession"] = relationship(back_populates="detections")

    def __repr__(self) -> str:
        return f"<AIDetectionResult session={self.session_id} track={self.track_id}>"


class AIAlert(Base):
    __tablename__ = "ai_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ai_analysis_sessions.id"), nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="UNREAD")

    session: Mapped["AIAnalysisSession"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<AIAlert {self.alert_type} session={self.session_id}>"
