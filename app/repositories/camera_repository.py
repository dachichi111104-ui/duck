from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Camera
from app.repositories.base_repository import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    def get_all(self, session: Session) -> list[Camera]:
        return list(session.execute(select(Camera).order_by(Camera.code)).scalars().all())

    def get_by_code(self, session: Session, code: str) -> Camera | None:
        return session.execute(select(Camera).where(Camera.code == code)).scalar_one_or_none()
