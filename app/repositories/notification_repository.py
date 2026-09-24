from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Notification
from app.repositories.base_repository import BaseRepository
from app.config.constants import AlertStatus


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def get_all(self, session: Session, limit: int = 100) -> list[Notification]:
        stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def get_unread_count(self, session: Session) -> int:
        stmt = select(Notification).where(Notification.status == AlertStatus.UNREAD)
        return len(list(session.execute(stmt).scalars().all()))

    def exists_similar(self, session: Session, alert_type: str, reference_type: str, reference_id: int) -> bool:
        stmt = (
            select(Notification)
            .where(Notification.alert_type == alert_type)
            .where(Notification.reference_type == reference_type)
            .where(Notification.reference_id == reference_id)
            .where(Notification.status != AlertStatus.DISMISSED)
        )
        return session.execute(stmt).first() is not None
