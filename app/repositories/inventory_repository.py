from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import InventoryCategory, InventoryItem, InventoryTransaction
from app.repositories.base_repository import BaseRepository


class InventoryCategoryRepository(BaseRepository[InventoryCategory]):
    model = InventoryCategory

    def get_all(self, session: Session) -> list[InventoryCategory]:
        return list(session.execute(select(InventoryCategory).order_by(InventoryCategory.name)).scalars().all())


class InventoryItemRepository(BaseRepository[InventoryItem]):
    model = InventoryItem

    def get_all(self, session: Session) -> list[InventoryItem]:
        stmt = select(InventoryItem).options(joinedload(InventoryItem.category)).order_by(InventoryItem.code)
        return list(session.execute(stmt).unique().scalars().all())

    def get_by_code(self, session: Session, code: str) -> InventoryItem | None:
        return session.execute(select(InventoryItem).where(InventoryItem.code == code)).scalar_one_or_none()

    def get_low_stock(self, session: Session) -> list[InventoryItem]:
        return [item for item in self.get_all(session) if item.is_low_stock]


class InventoryTransactionRepository(BaseRepository[InventoryTransaction]):
    model = InventoryTransaction

    def get_for_item(self, session: Session, item_id: int) -> list[InventoryTransaction]:
        stmt = (
            select(InventoryTransaction)
            .where(InventoryTransaction.item_id == item_id)
            .order_by(InventoryTransaction.transaction_date.desc())
        )
        return list(session.execute(stmt).scalars().all())

    def get_recent(self, session: Session, limit: int = 50) -> list[InventoryTransaction]:
        stmt = (
            select(InventoryTransaction)
            .options(joinedload(InventoryTransaction.item))
            .order_by(InventoryTransaction.transaction_date.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).unique().scalars().all())
