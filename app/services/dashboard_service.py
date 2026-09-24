from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.database.connection import session_scope
from app.database.models import Flock, ProductionRecord, InventoryItem, Vaccination
from app.repositories.flock_repository import FlockRepository, ProductionRecordRepository
from app.repositories.inventory_repository import InventoryItemRepository
from app.repositories.veterinary_repository import VaccinationRepository
from app.repositories.notification_repository import NotificationRepository
from app.config.constants import FlockStatus, VaccinationStatus


@dataclass
class DashboardData:
    total_ducks: int = 0
    total_flocks: int = 0
    flocks_under_watch: int = 0
    active_alerts: int = 0
    today_egg_production: int = 0

    flock_count_series: list[tuple[str, int]] = field(default_factory=list)     # (date, total current_count)
    production_series: list[tuple[str, int]] = field(default_factory=list)      # (date, egg_quantity)
    health_distribution: dict[str, int] = field(default_factory=dict)           # label -> count
    low_stock_items: list[InventoryItem] = field(default_factory=list)
    upcoming_vaccinations: list[Vaccination] = field(default_factory=list)


class DashboardService:
    def __init__(self) -> None:
        self._flock_repo = FlockRepository()
        self._prod_repo = ProductionRecordRepository()
        self._item_repo = InventoryItemRepository()
        self._vaccination_repo = VaccinationRepository()
        self._notif_repo = NotificationRepository()

    def get_dashboard_data(self, days: int = 14) -> DashboardData:
        data = DashboardData()
        today = dt.date.today()
        since = today - dt.timedelta(days=days)

        with session_scope() as session:
            flocks = self._flock_repo.get_all(session)
            data.total_flocks = len(flocks)
            data.total_ducks = sum(f.current_count for f in flocks)
            data.flocks_under_watch = sum(
                1 for f in flocks if f.status == FlockStatus.ACTIVE and f.dead_count > 0
            )

            records = self._prod_repo.get_since(session, since)
            data.today_egg_production = sum(
                r.egg_quantity for r in records if r.record_date == today
            )

            # Aggregate egg production per day across all flocks
            by_day: dict[dt.date, int] = {}
            for r in records:
                by_day[r.record_date] = by_day.get(r.record_date, 0) + r.egg_quantity
            data.production_series = [
                (d.strftime("%d/%m"), qty) for d, qty in sorted(by_day.items())
            ]

            # Flock "size" trend — approximate using current_count snapshot
            # repeated per day range isn't tracked historically, so we show
            # the flock start dates vs current counts as a simple bar series.
            data.flock_count_series = [(f.flock_code, f.current_count) for f in flocks]

            # Health distribution (very rough, driven by dead_count ratio)
            normal = sum(1 for f in flocks if f.dead_count == 0)
            watch = sum(1 for f in flocks if f.dead_count > 0)
            data.health_distribution = {"Bình thường": normal, "Theo dõi": watch}

            data.low_stock_items = self._item_repo.get_low_stock(session)[:5]

            data.upcoming_vaccinations = [
                v for v in self._vaccination_repo.get_upcoming(session, 14)
                if v.status != VaccinationStatus.COMPLETED
            ][:5]

            data.active_alerts = self._notif_repo.get_unread_count(session)

            session.expunge_all()

        return data
