from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Disease, VeterinaryRecord, Vaccination
from app.repositories.base_repository import BaseRepository


class DiseaseRepository(BaseRepository[Disease]):
    model = Disease

    def get_all(self, session: Session) -> list[Disease]:
        return list(session.execute(select(Disease).order_by(Disease.name)).scalars().all())


class VeterinaryRecordRepository(BaseRepository[VeterinaryRecord]):
    model = VeterinaryRecord

    def get_all(self, session: Session) -> list[VeterinaryRecord]:
        stmt = (
            select(VeterinaryRecord)
            .options(joinedload(VeterinaryRecord.flock), joinedload(VeterinaryRecord.disease))
            .order_by(VeterinaryRecord.diagnosis_date.desc())
        )
        return list(session.execute(stmt).unique().scalars().all())

    def get_for_flock(self, session: Session, flock_id: int) -> list[VeterinaryRecord]:
        stmt = (
            select(VeterinaryRecord)
            .where(VeterinaryRecord.flock_id == flock_id)
            .order_by(VeterinaryRecord.diagnosis_date.desc())
        )
        return list(session.execute(stmt).scalars().all())


class VaccinationRepository(BaseRepository[Vaccination]):
    model = Vaccination

    def get_all(self, session: Session) -> list[Vaccination]:
        stmt = select(Vaccination).options(joinedload(Vaccination.flock)).order_by(Vaccination.next_date)
        return list(session.execute(stmt).unique().scalars().all())

    def get_for_flock(self, session: Session, flock_id: int) -> list[Vaccination]:
        stmt = select(Vaccination).where(Vaccination.flock_id == flock_id).order_by(Vaccination.vaccination_date.desc())
        return list(session.execute(stmt).scalars().all())

    def get_upcoming(self, session: Session, within_days: int) -> list[Vaccination]:
        today = dt.date.today()
        horizon = today + dt.timedelta(days=within_days)
        stmt = (
            select(Vaccination)
            .options(joinedload(Vaccination.flock))
            .where(Vaccination.next_date.isnot(None))
            .where(Vaccination.next_date <= horizon)
            .order_by(Vaccination.next_date)
        )
        return list(session.execute(stmt).unique().scalars().all())
