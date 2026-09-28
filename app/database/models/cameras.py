from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="ONLINE")
    rtsp_url: Mapped[str | None] = mapped_column(String(500))
    video_file_path: Mapped[str | None] = mapped_column(String(500))
    resolution: Mapped[str | None] = mapped_column(String(20), default="1920x1080")
    fps: Mapped[int] = mapped_column(Integer, default=30)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    barn_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("barns.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    last_modified_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    remote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Camera {self.code} - {self.name}>"
