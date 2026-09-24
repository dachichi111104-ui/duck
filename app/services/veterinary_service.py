from __future__ import annotations

from app.database.connection import session_scope
from app.database.models import Disease, VeterinaryRecord, Vaccination
from app.repositories.veterinary_repository import (
    DiseaseRepository, VeterinaryRecordRepository, VaccinationRepository,
)
from app.utils.validators import require_not_empty, require_valid_date, ValidationError
from app.utils.logger import log_action, get_logger
from app.config.constants import VetRecordStatus, VaccinationStatus
from app.config.settings import VACCINATION_DUE_SOON_DAYS

logger = get_logger("veterinary_service")


class VeterinaryService:
    def __init__(self) -> None:
        self._disease_repo = DiseaseRepository()
        self._record_repo = VeterinaryRecordRepository()
        self._vaccination_repo = VaccinationRepository()

    def list_diseases(self) -> list[Disease]:
        with session_scope() as session:
            diseases = self._disease_repo.get_all(session)
            session.expunge_all()
            return diseases

    def list_records(self, flock_id: int | None = None) -> list[VeterinaryRecord]:
        with session_scope() as session:
            records = (
                self._record_repo.get_for_flock(session, flock_id)
                if flock_id else self._record_repo.get_all(session)
            )
            session.expunge_all()
            return records

    def create_record(self, actor: str, flock_id: int, disease_id: int | None, diagnosis_date,
                       symptoms: str, diagnosis: str, treatment: str, medication: str,
                       veterinarian: str, status: str = VetRecordStatus.THEO_DOI,
                       animal_reference: str = "", notes: str = "",
                       source: str = "MANUAL") -> VeterinaryRecord:
        date_val = require_valid_date(diagnosis_date, "Ngày chẩn đoán")
        veterinarian = require_not_empty(veterinarian, "Bác sĩ thú y")

        with session_scope() as session:
            record = VeterinaryRecord(
                flock_id=flock_id, animal_reference=animal_reference, disease_id=disease_id,
                diagnosis_date=date_val, symptoms=symptoms, diagnosis=diagnosis,
                treatment=treatment, medication=medication, veterinarian=veterinarian,
                status=status, notes=notes, source=source,
            )
            self._record_repo.add(session, record)
            session.expunge(record)
        log_action(actor, "CREATE_VET_RECORD", f"flock={flock_id}")
        return record

    def update_record(self, actor: str, record_id: int, **fields) -> VeterinaryRecord:
        with session_scope() as session:
            record = self._record_repo.get_by_id(session, record_id)
            if record is None:
                raise ValidationError("Không tìm thấy bệnh án.")
            for key in ("symptoms", "diagnosis", "treatment", "medication", "veterinarian",
                        "status", "notes", "disease_id"):
                if key in fields:
                    setattr(record, key, fields[key])
            session.flush()
            session.expunge(record)
        log_action(actor, "UPDATE_VET_RECORD", str(record_id))
        return record

    # ------------------------------------------------------------------
    def list_vaccinations(self, flock_id: int | None = None) -> list[Vaccination]:
        with session_scope() as session:
            items = (
                self._vaccination_repo.get_for_flock(session, flock_id)
                if flock_id else self._vaccination_repo.get_all(session)
            )
            session.expunge_all()
            return items

    def get_upcoming_vaccinations(self, within_days: int = VACCINATION_DUE_SOON_DAYS) -> list[Vaccination]:
        with session_scope() as session:
            items = self._vaccination_repo.get_upcoming(session, within_days)
            session.expunge_all()
            return items

    def schedule_vaccination(self, actor: str, flock_id: int, vaccine_name: str,
                              vaccination_date, next_date=None, dosage: str = "",
                              veterinarian: str = "", notes: str = "") -> Vaccination:
        vaccine_name = require_not_empty(vaccine_name, "Tên vắc xin")
        date_val = require_valid_date(vaccination_date, "Ngày tiêm")
        next_val = require_valid_date(next_date, "Ngày tiêm tiếp theo") if next_date else None

        with session_scope() as session:
            vac = Vaccination(
                flock_id=flock_id, vaccine_name=vaccine_name, vaccination_date=date_val,
                next_date=next_val, dosage=dosage, veterinarian=veterinarian, notes=notes,
                status=VaccinationStatus.COMPLETED,
            )
            self._vaccination_repo.add(session, vac)
            session.expunge(vac)
        log_action(actor, "SCHEDULE_VACCINATION", f"flock={flock_id} vaccine={vaccine_name}")
        return vac
