"""
Seeds demo data on first run so the dashboard, charts, and lists are
never empty (see spec sections 31 & 46).
"""
from __future__ import annotations

import datetime as dt
import logging
import random

from app.database.connection import session_scope
from app.database.models import (
    Role, User, Barn, Flock, FlockEvent, ProductionRecord,
    InventoryCategory, InventoryItem, InventoryTransaction,
    Disease, VeterinaryRecord, Vaccination,
)
from app.config.constants import (
    Roles, FlockEventType, InventoryTransactionType, VetRecordStatus,
    VaccinationStatus, DISEASE_SEED, DEFAULT_SPECIES,
)
from app.utils.security import hash_password

logger = logging.getLogger("wdf.seed")


def seed_database() -> None:
    with session_scope() as session:
        if session.query(Role).count() > 0:
            logger.info("Database already seeded, skipping.")
            return

        # --- Roles -----------------------------------------------------
        roles = {
            Roles.ADMIN: Role(name=Roles.ADMIN, description="Toàn quyền hệ thống"),
            Roles.FARM_MANAGER: Role(name=Roles.FARM_MANAGER, description="Quản lý trang trại"),
            Roles.VETERINARIAN: Role(name=Roles.VETERINARIAN, description="Bác sĩ thú y"),
            Roles.STAFF: Role(name=Roles.STAFF, description="Nhân viên"),
        }
        session.add_all(roles.values())
        session.flush()

        # --- Users -------------------------------------------------------
        users = [
            User(username="admin", password_hash=hash_password("admin123"),
                 full_name="Quản trị viên", role_id=roles[Roles.ADMIN].id),
            User(username="manager", password_hash=hash_password("manager123"),
                 full_name="Quản lý trang trại", role_id=roles[Roles.FARM_MANAGER].id),
            User(username="vet", password_hash=hash_password("vet123"),
                 full_name="Bác sĩ thú y", role_id=roles[Roles.VETERINARIAN].id),
            User(username="staff", password_hash=hash_password("staff123"),
                 full_name="Nhân viên trang trại", role_id=roles[Roles.STAFF].id),
        ]
        session.add_all(users)
        session.flush()

        # --- Barns -------------------------------------------------------
        barns = [
            Barn(code="C01", name="Chuồng 01", location="Khu A", capacity=600, current_count=0),
            Barn(code="C02", name="Chuồng 02", location="Khu A", capacity=500, current_count=0),
            Barn(code="C03", name="Chuồng 03", location="Khu B", capacity=400, current_count=0),
        ]
        session.add_all(barns)
        session.flush()

        # --- Flocks --------------------------------------------------------
        today = dt.date.today()
        flock_defs = [
            ("VD-001", "Đàn vịt trời lứa 1", barns[0], 60, 500, 480, 14),
            ("VD-002", "Đàn vịt trời lứa 2", barns[1], 45, 420, 400, 8),
            ("VD-003", "Đàn vịt trời lứa 3", barns[2], 30, 380, 360, 20),
        ]
        flocks = []
        for code, name, barn, days_ago, initial, current, dead in flock_defs:
            f = Flock(
                flock_code=code, name=name, barn_id=barn.id, species=DEFAULT_SPECIES,
                breed="Vịt trời địa phương",
                start_date=today - dt.timedelta(days=days_ago),
                initial_count=initial, current_count=current, dead_count=dead,
            )
            flocks.append(f)
            barn.current_count += current
        session.add_all(flocks)
        session.flush()

        # --- Flock events ----------------------------------------------
        for f in flocks:
            session.add(FlockEvent(
                flock_id=f.id, event_type=FlockEventType.IMPORT, quantity=f.initial_count,
                event_date=f.start_date, reason="Nhập đàn ban đầu",
            ))
            if f.dead_count:
                session.add(FlockEvent(
                    flock_id=f.id, event_type=FlockEventType.DEATH, quantity=f.dead_count,
                    event_date=f.start_date + dt.timedelta(days=5),
                    reason="Hao hụt tự nhiên",
                ))

        # --- Production records (last 14 days, so charts aren't empty) --
        for f in flocks:
            for i in range(14, 0, -1):
                record_date = today - dt.timedelta(days=i)
                session.add(ProductionRecord(
                    flock_id=f.id,
                    record_date=record_date,
                    egg_quantity=random.randint(int(f.current_count * 0.3), int(f.current_count * 0.5)),
                    average_weight=round(random.uniform(1.6, 2.3), 2),
                    feed_consumption=round(f.current_count * random.uniform(0.15, 0.2), 1),
                ))

        # --- Inventory categories & items --------------------------------
        cat_feed = InventoryCategory(name="Thức ăn", description="Thức ăn chăn nuôi")
        cat_med = InventoryCategory(name="Thuốc thú y", description="Thuốc và vắc xin")
        cat_supply = InventoryCategory(name="Vật tư", description="Vật tư tiêu hao")
        cat_tool = InventoryCategory(name="Dụng cụ", description="Dụng cụ chăn nuôi")
        cat_other = InventoryCategory(name="Khác", description="Khác")
        session.add_all([cat_feed, cat_med, cat_supply, cat_tool, cat_other])
        session.flush()

        items = [
            InventoryItem(category_id=cat_feed.id, code="TA-001", name="Cám vịt tăng trưởng",
                          unit="kg", quantity=250, minimum_quantity=100, unit_price=12000,
                          supplier="Công ty TĂCN Miền Nam"),
            InventoryItem(category_id=cat_feed.id, code="TA-002", name="Cám vịt đẻ trứng",
                          unit="kg", quantity=80, minimum_quantity=100, unit_price=13500,
                          supplier="Công ty TĂCN Miền Nam"),
            InventoryItem(category_id=cat_med.id, code="TH-001", name="Vitamin tổng hợp",
                          unit="chai", quantity=15, minimum_quantity=10, unit_price=45000,
                          expiry_date=today + dt.timedelta(days=20)),
            InventoryItem(category_id=cat_med.id, code="TH-002", name="Vắc xin tụ huyết trùng",
                          unit="liều", quantity=40, minimum_quantity=50, unit_price=8000,
                          expiry_date=today + dt.timedelta(days=90)),
            InventoryItem(category_id=cat_supply.id, code="VT-001", name="Vôi khử trùng chuồng",
                          unit="kg", quantity=60, minimum_quantity=20, unit_price=5000),
            InventoryItem(category_id=cat_tool.id, code="DC-001", name="Máng ăn nhựa",
                          unit="cái", quantity=35, minimum_quantity=10, unit_price=25000),
        ]
        session.add_all(items)
        session.flush()

        for item in items:
            session.add(InventoryTransaction(
                item_id=item.id, transaction_type=InventoryTransactionType.IMPORT,
                quantity=item.quantity, transaction_date=today - dt.timedelta(days=10),
                reference="PN-DEMO", note="Nhập kho ban đầu (seed demo)",
            ))

        # --- Diseases ------------------------------------------------------
        diseases = [Disease(name=d["name"], cause=d["cause"], behavior_signs=d["behavior_signs"])
                    for d in DISEASE_SEED]
        session.add_all(diseases)
        session.flush()

        # --- Veterinary demo records ----------------------------------
        session.add(VeterinaryRecord(
            flock_id=flocks[1].id, animal_reference="Cá thể #12",
            disease_id=diseases[0].id, diagnosis_date=today - dt.timedelta(days=3),
            symptoms="Té ngã, khó đứng dậy", diagnosis="Nghi lật ngửa do virus",
            treatment="Cách ly theo dõi", veterinarian="BSTY Nguyễn Văn A",
            status=VetRecordStatus.THEO_DOI,
        ))
        session.add(VeterinaryRecord(
            flock_id=flocks[0].id, animal_reference="Cá thể #05",
            disease_id=diseases[1].id, diagnosis_date=today - dt.timedelta(days=8),
            symptoms="Liệt chân, tách đàn", diagnosis="Tụ huyết trùng",
            treatment="Kháng sinh theo phác đồ", medication="Amoxicillin",
            veterinarian="BSTY Nguyễn Văn A", status=VetRecordStatus.DANG_DIEU_TRI,
        ))

        # --- Vaccination schedule ------------------------------------------
        session.add(Vaccination(
            flock_id=flocks[0].id, vaccine_name="Vắc xin dịch tả vịt",
            vaccination_date=today - dt.timedelta(days=30),
            next_date=today + dt.timedelta(days=3), dosage="1ml/con",
            veterinarian="BSTY Nguyễn Văn A", status=VaccinationStatus.SCHEDULED,
        ))
        session.add(Vaccination(
            flock_id=flocks[1].id, vaccine_name="Vắc xin tụ huyết trùng",
            vaccination_date=today - dt.timedelta(days=45),
            next_date=today - dt.timedelta(days=2), dosage="1ml/con",
            veterinarian="BSTY Nguyễn Văn A", status=VaccinationStatus.OVERDUE,
        ))
        session.add(Vaccination(
            flock_id=flocks[2].id, vaccine_name="Vắc xin dịch tả vịt",
            vaccination_date=today - dt.timedelta(days=10),
            next_date=today + dt.timedelta(days=20), dosage="1ml/con",
            veterinarian="BSTY Nguyễn Văn A", status=VaccinationStatus.COMPLETED,
        ))

        logger.info("Seed data inserted successfully.")


def run_alert_scan_after_seed() -> None:
    """Populate the notification center from the freshly seeded data."""
    from app.services.alert_service import AlertService
    AlertService().run_full_scan()
