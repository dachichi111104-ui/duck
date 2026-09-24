from __future__ import annotations

import datetime as dt

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.config.constants import AlertStatus


class Notification(Base):
    """
    Central notification / alert table backing the Notification Center.
    Populated by services (inventory, vaccination, AI) whenever a
    threshold or condition is triggered — never hard-coded in the UI.
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # RED/ORANGE/GREEN
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))  # e.g. "inventory_item"
    reference_id: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default=AlertStatus.UNREAD)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Notification {self.alert_type} sev={self.severity}>"
