from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.config.constants import FlockStatus, DEFAULT_SPECIES


class Flock(Base):
    __tablename__ = "flocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    flock_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    barn_id: Mapped[int | None] = mapped_column(ForeignKey("barns.id"))
    species: Mapped[str] = mapped_column(String(100), default=DEFAULT_SPECIES)
    breed: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    initial_count: Mapped[int] = mapped_column(Integer, default=0)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    dead_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=FlockStatus.ACTIVE)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    barn: Mapped["Barn"] = relationship(back_populates="flocks")
    events: Mapped[list["FlockEvent"]] = relationship(back_populates="flock", cascade="all, delete-orphan")
    production_records: Mapped[list["ProductionRecord"]] = relationship(
        back_populates="flock", cascade="all, delete-orphan"
    )
    veterinary_records: Mapped[list["VeterinaryRecord"]] = relationship(
        back_populates="flock", cascade="all, delete-orphan"
    )
    vaccinations: Mapped[list["Vaccination"]] = relationship(
        back_populates="flock", cascade="all, delete-orphan"
    )

    @property
    def survival_rate(self) -> float:
        if not self.initial_count:
            return 0.0
        return round((self.current_count / self.initial_count) * 100, 1)

    def __repr__(self) -> str:
        return f"<Flock {self.flock_code}>"


class FlockEvent(Base):
    __tablename__ = "flock_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    flock_id: Mapped[int] = mapped_column(ForeignKey("flocks.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    event_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    flock: Mapped["Flock"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<FlockEvent {self.event_type} qty={self.quantity}>"


class ProductionRecord(Base):
    __tablename__ = "production_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    flock_id: Mapped[int] = mapped_column(ForeignKey("flocks.id"), nullable=False)
    record_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    egg_quantity: Mapped[int] = mapped_column(Integer, default=0)
    average_weight: Mapped[float | None] = mapped_column(Float)
    feed_consumption: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(String(500))

    flock: Mapped["Flock"] = relationship(back_populates="production_records")

    def __repr__(self) -> str:
        return f"<ProductionRecord {self.record_date} eggs={self.egg_quantity}>"
