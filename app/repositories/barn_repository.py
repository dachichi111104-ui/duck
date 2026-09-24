from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Barn
from app.repositories.base_repository import BaseRepository


class BarnRepository(BaseRepository[Barn]):
    model = Barn

    def get_all(self, session: Session) -> list[Barn]:
        return list(session.execute(select(Barn).order_by(Barn.code)).scalars().all())

    def get_by_code(self, session: Session, code: str) -> Barn | None:
        return session.execute(select(Barn).where(Barn.code == code)).scalar_one_or_none()
