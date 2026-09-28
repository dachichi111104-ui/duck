"""Generic repository base class — thin wrapper over a SQLAlchemy session."""
from __future__ import annotations

import datetime as dt
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def _mark_pending(self, instance: ModelT) -> None:
        if hasattr(instance, "sync_status"):
            current_status = getattr(instance, "sync_status", None)
            if current_status != "SYNCED":
                setattr(instance, "sync_status", "PENDING")
        if hasattr(instance, "last_modified_at"):
            setattr(instance, "last_modified_at", dt.datetime.utcnow())

    def get_by_id(self, session: Session, pk: int) -> ModelT | None:
        return session.get(self.model, pk)

    def get_by_remote_id(self, session: Session, remote_id: int) -> ModelT | None:
        if not hasattr(self.model, "remote_id"):
            return None
        stmt = select(self.model).where(self.model.remote_id == remote_id)
        return session.execute(stmt).scalar_one_or_none()

    def get_all(self, session: Session) -> list[ModelT]:
        return list(session.query(self.model).all())

    def get_pending(self, session: Session) -> list[ModelT]:
        if not hasattr(self.model, "sync_status"):
            return []
        stmt = select(self.model).where(self.model.sync_status == "PENDING")
        return list(session.execute(stmt).scalars().all())

    def get_conflicts(self, session: Session) -> list[ModelT]:
        if not hasattr(self.model, "sync_status"):
            return []
        stmt = select(self.model).where(self.model.sync_status == "CONFLICT")
        return list(session.execute(stmt).scalars().all())

    def add(self, session: Session, instance: ModelT) -> ModelT:
        self._mark_pending(instance)
        session.add(instance)
        session.flush()
        return instance

    def update(self, session: Session, instance: ModelT) -> ModelT:
        self._mark_pending(instance)
        session.flush()
        return instance

    def delete(self, session: Session, instance: ModelT) -> None:
        session.delete(instance)
        session.flush()

    def mark_synced(self, session: Session, instance: ModelT, remote_id: int | None = None) -> None:
        if hasattr(instance, "sync_status"):
            setattr(instance, "sync_status", "SYNCED")
        if remote_id is not None and hasattr(instance, "remote_id"):
            setattr(instance, "remote_id", remote_id)
        session.flush()

    def mark_conflict(self, session: Session, instance: ModelT) -> None:
        if hasattr(instance, "sync_status"):
            setattr(instance, "sync_status", "CONFLICT")
        session.flush()
