from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Flock, FlockEvent, ProductionRecord
from app.repositories.base_repository import BaseRepository


class FlockRepository(BaseRepository[Flock]):
    model = Flock

    def get_all(self, session: Session) -> list[Flock]:
        stmt = select(Flock).options(joinedload(Flock.barn)).order_by(Flock.flock_code)
        return list(session.execute(stmt).unique().scalars().all())

    def get_by_code(self, session: Session, code: str) -> Flock | None:
        return session.execute(select(Flock).where(Flock.flock_code == code)).scalar_one_or_none()

    def get_with_details(self, session: Session, flock_id: int) -> Flock | None:
        stmt = (
            select(Flock)
            .options(
                joinedload(Flock.barn),
                joinedload(Flock.events),
                joinedload(Flock.production_records),
                joinedload(Flock.veterinary_records),
                joinedload(Flock.vaccinations),
            )
            .where(Flock.id == flock_id)
        )
        return session.execute(stmt).unique().scalar_one_or_none()


class FlockEventRepository(BaseRepository[FlockEvent]):
    model = FlockEvent

    def get_for_flock(self, session: Session, flock_id: int) -> list[FlockEvent]:
        stmt = select(FlockEvent).where(FlockEvent.flock_id == flock_id).order_by(FlockEvent.event_date.desc())
        return list(session.execute(stmt).scalars().all())


class ProductionRecordRepository(BaseRepository[ProductionRecord]):
    model = ProductionRecord

    def get_for_flock(self, session: Session, flock_id: int) -> list[ProductionRecord]:
        stmt = (
            select(ProductionRecord)
            .options(joinedload(ProductionRecord.flock))
            .where(ProductionRecord.flock_id == flock_id)
            .order_by(ProductionRecord.record_date)
        )
        return list(session.execute(stmt).unique().scalars().all())

    def get_since(self, session: Session, since: dt.date) -> list[ProductionRecord]:
        stmt = (
            select(ProductionRecord)
            .options(joinedload(ProductionRecord.flock))
            .where(ProductionRecord.record_date >= since)
            .order_by(ProductionRecord.record_date)
        )
        return list(session.execute(stmt).unique().scalars().all())
