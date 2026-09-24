"""
Notification Center engine.

Scans current data (inventory levels, expiry dates, vaccination schedule,
flock watch-list) and raises Notification rows. Called after seeding and
can be re-run any time (e.g. on dashboard refresh) via run_full_scan().
"""
from __future__ import annotations

import datetime as dt

from app.database.connection import session_scope
from app.database.models import Notification, InventoryItem, Vaccination, VeterinaryRecord
from app.repositories.notification_repository import NotificationRepository
from app.repositories.inventory_repository import InventoryItemRepository
from app.repositories.veterinary_repository import VaccinationRepository, VeterinaryRecordRepository
from app.config.constants import (
    AlertType, AlertSeverity, AlertStatus, VaccinationStatus, VetRecordStatus,
)
from app.config.settings import EXPIRY_WARNING_DAYS, VACCINATION_DUE_SOON_DAYS
from app.utils.logger import get_logger

logger = get_logger("alert_service")


class AlertService:
    def __init__(self) -> None:
        self._notif_repo = NotificationRepository()
        self._item_repo = InventoryItemRepository()
        self._vaccination_repo = VaccinationRepository()
        self._vet_repo = VeterinaryRecordRepository()

    def run_full_scan(self) -> int:
        created = 0
        with session_scope() as session:
            today = dt.date.today()

            # --- Inventory: low stock / critical -------------------------
            for item in self._item_repo.get_all(session):
                if item.is_low_stock:
                    critical = item.quantity <= 0
                    alert_type = AlertType.STOCK_CRITICAL if critical else AlertType.STOCK_LOW
                    if not self._notif_repo.exists_similar(session, alert_type, "inventory_item", item.id):
                        session.add(Notification(
                            alert_type=alert_type,
                            severity=AlertSeverity.RED if critical else AlertSeverity.ORANGE,
                            title="Tồn kho thấp" if not critical else "Tồn kho nghiêm trọng",
                            message=f"Vật tư '{item.name}' ({item.code}) còn {item.quantity} {item.unit}.",
                            reference_type="inventory_item", reference_id=item.id,
                        ))
                        created += 1

                if item.expiry_date and item.expiry_date <= today + dt.timedelta(days=EXPIRY_WARNING_DAYS):
                    if not self._notif_repo.exists_similar(session, AlertType.ITEM_EXPIRING, "inventory_item", item.id):
                        session.add(Notification(
                            alert_type=AlertType.ITEM_EXPIRING,
                            severity=AlertSeverity.ORANGE,
                            title="Vật tư sắp hết hạn",
                            message=f"'{item.name}' ({item.code}) hết hạn vào {item.expiry_date}.",
                            reference_type="inventory_item", reference_id=item.id,
                        ))
                        created += 1

            # --- Vaccination: due soon / overdue ---------------------------
            for vac in self._vaccination_repo.get_all(session):
                if vac.next_date is None or vac.status == VaccinationStatus.COMPLETED:
                    continue
                if vac.next_date < today:
                    if not self._notif_repo.exists_similar(session, AlertType.VACCINATION_OVERDUE, "vaccination", vac.id):
                        session.add(Notification(
                            alert_type=AlertType.VACCINATION_OVERDUE,
                            severity=AlertSeverity.RED,
                            title="Lịch tiêm quá hạn",
                            message=f"Đàn '{vac.flock.flock_code if vac.flock else vac.flock_id}' quá hạn tiêm "
                                    f"'{vac.vaccine_name}' từ {vac.next_date}.",
                            reference_type="vaccination", reference_id=vac.id,
                        ))
                        created += 1
                elif vac.next_date <= today + dt.timedelta(days=VACCINATION_DUE_SOON_DAYS):
                    if not self._notif_repo.exists_similar(session, AlertType.VACCINATION_DUE_SOON, "vaccination", vac.id):
                        session.add(Notification(
                            alert_type=AlertType.VACCINATION_DUE_SOON,
                            severity=AlertSeverity.ORANGE,
                            title="Sắp đến lịch tiêm",
                            message=f"Đàn '{vac.flock.flock_code if vac.flock else vac.flock_id}' sắp đến lịch "
                                    f"tiêm '{vac.vaccine_name}' vào {vac.next_date}.",
                            reference_type="vaccination", reference_id=vac.id,
                        ))
                        created += 1

            # --- Veterinary: flocks needing follow-up ----------------------
            for rec in self._vet_repo.get_all(session):
                if rec.status in (VetRecordStatus.THEO_DOI, VetRecordStatus.CAN_TAI_KHAM):
                    if not self._notif_repo.exists_similar(session, AlertType.FLOCK_WATCH, "veterinary_record", rec.id):
                        session.add(Notification(
                            alert_type=AlertType.FLOCK_WATCH,
                            severity=AlertSeverity.ORANGE,
                            title="Cần theo dõi đàn",
                            message=f"Đàn '{rec.flock.flock_code if rec.flock else rec.flock_id}' cần theo dõi "
                                    f"({rec.diagnosis or 'chưa rõ chẩn đoán'}).",
                            reference_type="veterinary_record", reference_id=rec.id,
                        ))
                        created += 1

        if created:
            logger.info("Alert scan created %d notification(s).", created)
        return created

    def list_notifications(self, limit: int = 100) -> list[Notification]:
        with session_scope() as session:
            items = self._notif_repo.get_all(session, limit)
            session.expunge_all()
            return items

    def unread_count(self) -> int:
        with session_scope() as session:
            return self._notif_repo.get_unread_count(session)

    def mark_read(self, notification_id: int) -> None:
        with session_scope() as session:
            notif = self._notif_repo.get_by_id(session, notification_id)
            if notif:
                notif.status = AlertStatus.READ

    def mark_all_read(self) -> None:
        with session_scope() as session:
            for notif in self._notif_repo.get_all(session, limit=1000):
                if notif.status == AlertStatus.UNREAD:
                    notif.status = AlertStatus.READ
