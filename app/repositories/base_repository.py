"""Generic repository base class — thin wrapper over a SQLAlchemy session."""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def get_by_id(self, session: Session, pk: int) -> ModelT | None:
        return session.get(self.model, pk)

    def get_all(self, session: Session) -> list[ModelT]:
        return list(session.query(self.model).all())

    def add(self, session: Session, instance: ModelT) -> ModelT:
        session.add(instance)
        session.flush()
        return instance

    def delete(self, session: Session, instance: ModelT) -> None:
        session.delete(instance)
        session.flush()
