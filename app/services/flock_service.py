from __future__ import annotations

import datetime as dt

from app.database.connection import session_scope
from app.database.models import Flock, FlockEvent, ProductionRecord, Barn
from app.repositories.flock_repository import (
    FlockRepository, FlockEventRepository, ProductionRecordRepository,
)
from app.repositories.barn_repository import BarnRepository
from app.utils.validators import require_not_empty, require_positive_number, require_valid_date, ValidationError
from app.utils.logger import log_action, get_logger
from app.config.constants import FlockEventType, DEFAULT_SPECIES

logger = get_logger("flock_service")


class FlockService:
    def __init__(self) -> None:
        self._repo = FlockRepository()
        self._event_repo = FlockEventRepository()
        self._prod_repo = ProductionRecordRepository()
        self._barn_repo = BarnRepository()

    # ------------------------------------------------------------------
    def list_flocks(self) -> list[Flock]:
        with session_scope() as session:
            flocks = self._repo.get_all(session)
            session.expunge_all()
            return flocks

    def get_flock_details(self, flock_id: int) -> Flock | None:
        with session_scope() as session:
            flock = self._repo.get_with_details(session, flock_id)
            if flock:
                session.expunge(flock)
            return flock

    def create_flock(self, actor: str, flock_code: str, name: str, barn_id: int | None,
                      breed: str, start_date, initial_count: float, notes: str = "") -> Flock:
        flock_code = require_not_empty(flock_code, "Mã đàn")
        name = require_not_empty(name, "Tên đàn")
        initial = int(require_positive_number(initial_count, "Số lượng ban đầu"))
        start = require_valid_date(start_date, "Ngày nhập")

        with session_scope() as session:
            if self._repo.get_by_code(session, flock_code):
                raise ValidationError(f"Mã đàn '{flock_code}' đã tồn tại.")

            barn: Barn | None = None
            if barn_id:
                barn = self._barn_repo.get_by_id(session, barn_id)
                if barn is None:
                    raise ValidationError("Không tìm thấy chuồng.")
                if barn.current_count + initial > barn.capacity:
                    remaining = max(barn.capacity - barn.current_count, 0)
                    raise ValidationError(
                        f"Số lượng vượt quá sức chứa chuồng '{barn.code}'. Còn lại: {remaining}."
                    )

            flock = Flock(
                flock_code=flock_code, name=name, barn_id=barn_id, species=DEFAULT_SPECIES,
                breed=breed, start_date=start, initial_count=initial, current_count=initial,
                dead_count=0, notes=notes,
            )
            self._repo.add(session, flock)

            self._event_repo.add(session, FlockEvent(
                flock_id=flock.id, event_type=FlockEventType.IMPORT, quantity=initial,
                event_date=start, reason="Nhập đàn ban đầu", created_by=None,
            ))

            if barn:
                barn.current_count += initial

            session.flush()
            session.expunge(flock)
        log_action(actor, "CREATE_FLOCK", flock_code)
        return flock

    def update_flock(self, actor: str, flock_id: int, **fields) -> Flock:
        with session_scope() as session:
            flock = self._repo.get_by_id(session, flock_id)
            if flock is None:
                raise ValidationError("Không tìm thấy đàn.")
            if "name" in fields:
                flock.name = require_not_empty(fields["name"], "Tên đàn")
            if "breed" in fields:
                flock.breed = fields["breed"]
            if "notes" in fields:
                flock.notes = fields["notes"]
            if "status" in fields:
                flock.status = fields["status"]
            session.flush()
            session.expunge(flock)
        log_action(actor, "UPDATE_FLOCK", str(flock_id))
        return flock

    def delete_flock(self, actor: str, flock_id: int) -> None:
        with session_scope() as session:
            flock = self._repo.get_by_id(session, flock_id)
            if flock is None:
                return
            if flock.barn_id:
                barn = self._barn_repo.get_by_id(session, flock.barn_id)
                if barn:
                    barn.current_count = max(barn.current_count - flock.current_count, 0)
            self._repo.delete(session, flock)
        log_action(actor, "DELETE_FLOCK", str(flock_id))

    # ------------------------------------------------------------------
    def record_event(self, actor: str, flock_id: int, event_type: str, quantity: float,
                      event_date, reason: str = "", notes: str = "") -> FlockEvent:
        qty = int(require_positive_number(quantity, "Số lượng"))
        date_val = require_valid_date(event_date, "Ngày")

        with session_scope() as session:
            flock = self._repo.get_by_id(session, flock_id)
            if flock is None:
                raise ValidationError("Không tìm thấy đàn.")

            if event_type in (FlockEventType.DEATH, FlockEventType.CULL):
                if qty > flock.current_count:
                    raise ValidationError("Số lượng vượt quá số cá thể hiện có trong đàn.")
                flock.current_count -= qty
                if event_type == FlockEventType.DEATH:
                    flock.dead_count += qty
                if flock.barn_id:
                    barn = self._barn_repo.get_by_id(session, flock.barn_id)
                    if barn:
                        barn.current_count = max(barn.current_count - qty, 0)
            elif event_type in (FlockEventType.IMPORT, FlockEventType.ADDITION):
                if flock.barn_id:
                    barn = self._barn_repo.get_by_id(session, flock.barn_id)
                    if barn and barn.current_count + qty > barn.capacity:
                        remaining = max(barn.capacity - barn.current_count, 0)
                        raise ValidationError(
                            f"Số lượng vượt quá sức chứa chuồng. Còn lại: {remaining}."
                        )
                    if barn:
                        barn.current_count += qty
                flock.current_count += qty

            event = FlockEvent(
                flock_id=flock_id, event_type=event_type, quantity=qty,
                event_date=date_val, reason=reason, notes=notes,
            )
            self._event_repo.add(session, event)
            session.flush()
            session.expunge(event)
        log_action(actor, "FLOCK_EVENT", f"{event_type} flock={flock_id} qty={qty}")
        return event

    def add_production_record(self, actor: str, flock_id: int, record_date, egg_quantity: float,
                               average_weight: float | None = None,
                               feed_consumption: float | None = None, notes: str = "") -> ProductionRecord:
        date_val = require_valid_date(record_date, "Ngày ghi nhận")
        eggs = int(require_positive_number(egg_quantity, "Sản lượng trứng", allow_zero=True))

        with session_scope() as session:
            record = ProductionRecord(
                flock_id=flock_id, record_date=date_val, egg_quantity=eggs,
                average_weight=average_weight, feed_consumption=feed_consumption, notes=notes,
            )
            self._prod_repo.add(session, record)
            session.expunge(record)
        log_action(actor, "ADD_PRODUCTION", f"flock={flock_id} eggs={eggs}")
        return record

    def production_since(self, since_days: int = 14) -> list[ProductionRecord]:
        since = dt.date.today() - dt.timedelta(days=since_days)
        with session_scope() as session:
            records = self._prod_repo.get_since(session, since)
            session.expunge_all()
            return records
