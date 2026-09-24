from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.config.constants import VetRecordStatus, VaccinationStatus


class Disease(Base):
    __tablename__ = "diseases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    cause: Mapped[str | None] = mapped_column(String(255))
    behavior_signs: Mapped[str | None] = mapped_column(String(500))

    records: Mapped[list["VeterinaryRecord"]] = relationship(back_populates="disease")

    def __repr__(self) -> str:
        return f"<Disease {self.name}>"


class VeterinaryRecord(Base):
    __tablename__ = "veterinary_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    flock_id: Mapped[int] = mapped_column(ForeignKey("flocks.id"), nullable=False)
    animal_reference: Mapped[str | None] = mapped_column(String(100))
    disease_id: Mapped[int | None] = mapped_column(ForeignKey("diseases.id"))
    diagnosis_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    symptoms: Mapped[str | None] = mapped_column(String(500))
    diagnosis: Mapped[str | None] = mapped_column(String(500))
    treatment: Mapped[str | None] = mapped_column(String(500))
    medication: Mapped[str | None] = mapped_column(String(255))
    veterinarian: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default=VetRecordStatus.THEO_DOI)
    notes: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(30), default="MANUAL")  # MANUAL | AI_ANALYSIS
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    flock: Mapped["Flock"] = relationship(back_populates="veterinary_records")
    disease: Mapped["Disease"] = relationship(back_populates="records")

    def __repr__(self) -> str:
        return f"<VeterinaryRecord flock={self.flock_id} status={self.status}>"


class Vaccination(Base):
    __tablename__ = "vaccinations"

    id: Mapped[int] = mapped_column(primary_key=True)
    flock_id: Mapped[int] = mapped_column(ForeignKey("flocks.id"), nullable=False)
    vaccine_name: Mapped[str] = mapped_column(String(150), nullable=False)
    vaccination_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    next_date: Mapped[dt.date | None] = mapped_column(Date)
    dosage: Mapped[str | None] = mapped_column(String(100))
    veterinarian: Mapped[str | None] = mapped_column(String(150))
    notes: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=VaccinationStatus.SCHEDULED)

    flock: Mapped["Flock"] = relationship(back_populates="vaccinations")

    def __repr__(self) -> str:
        return f"<Vaccination {self.vaccine_name} flock={self.flock_id}>"
