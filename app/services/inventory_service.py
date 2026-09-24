from __future__ import annotations

import datetime as dt

from app.database.connection import session_scope
from app.database.models import InventoryItem, InventoryTransaction, InventoryCategory
from app.repositories.inventory_repository import (
    InventoryItemRepository, InventoryTransactionRepository, InventoryCategoryRepository,
)
from app.utils.validators import require_not_empty, require_positive_number, require_valid_date, ValidationError
from app.utils.logger import log_action, get_logger
from app.config.constants import InventoryTransactionType

logger = get_logger("inventory_service")


class InventoryService:
    def __init__(self) -> None:
        self._item_repo = InventoryItemRepository()
        self._txn_repo = InventoryTransactionRepository()
        self._cat_repo = InventoryCategoryRepository()

    def list_categories(self) -> list[InventoryCategory]:
        with session_scope() as session:
            cats = self._cat_repo.get_all(session)
            session.expunge_all()
            return cats

    def list_items(self) -> list[InventoryItem]:
        with session_scope() as session:
            items = self._item_repo.get_all(session)
            session.expunge_all()
            return items

    def get_low_stock_items(self) -> list[InventoryItem]:
        with session_scope() as session:
            items = self._item_repo.get_low_stock(session)
            session.expunge_all()
            return items

    def get_expiring_items(self, within_days: int) -> list[InventoryItem]:
        horizon = dt.date.today() + dt.timedelta(days=within_days)
        with session_scope() as session:
            items = [
                i for i in self._item_repo.get_all(session)
                if i.expiry_date is not None and i.expiry_date <= horizon
            ]
            session.expunge_all()
            return items

    def recent_transactions(self, limit: int = 50) -> list[InventoryTransaction]:
        with session_scope() as session:
            txns = self._txn_repo.get_recent(session, limit)
            session.expunge_all()
            return txns

    def create_item(self, actor: str, category_id: int, code: str, name: str, unit: str,
                     minimum_quantity: float, unit_price: float, expiry_date=None,
                     supplier: str = "", description: str = "") -> InventoryItem:
        code = require_not_empty(code, "Mã vật tư")
        name = require_not_empty(name, "Tên vật tư")
        unit = require_not_empty(unit, "Đơn vị")
        min_qty = require_positive_number(minimum_quantity, "Định mức tối thiểu", allow_zero=True)
        price = require_positive_number(unit_price, "Đơn giá", allow_zero=True)

        with session_scope() as session:
            if self._item_repo.get_by_code(session, code):
                raise ValidationError(f"Mã vật tư '{code}' đã tồn tại.")
            item = InventoryItem(
                category_id=category_id, code=code, name=name, unit=unit, quantity=0,
                minimum_quantity=min_qty, unit_price=price, expiry_date=expiry_date,
                supplier=supplier, description=description,
            )
            self._item_repo.add(session, item)
            session.expunge(item)
        log_action(actor, "CREATE_ITEM", code)
        return item

    def update_item(self, actor: str, item_id: int, **fields) -> InventoryItem:
        with session_scope() as session:
            item = self._item_repo.get_by_id(session, item_id)
            if item is None:
                raise ValidationError("Không tìm thấy vật tư.")
            for key in ("name", "unit", "supplier", "description", "status", "expiry_date", "category_id"):
                if key in fields:
                    setattr(item, key, fields[key])
            if "minimum_quantity" in fields:
                item.minimum_quantity = require_positive_number(fields["minimum_quantity"], "Định mức", allow_zero=True)
            if "unit_price" in fields:
                item.unit_price = require_positive_number(fields["unit_price"], "Đơn giá", allow_zero=True)
            session.flush()
            session.expunge(item)
        log_action(actor, "UPDATE_ITEM", str(item_id))
        return item

    def delete_item(self, actor: str, item_id: int) -> None:
        with session_scope() as session:
            item = self._item_repo.get_by_id(session, item_id)
            if item is None:
                return
            self._item_repo.delete(session, item)
        log_action(actor, "DELETE_ITEM", str(item_id))

    def record_transaction(self, actor: str, item_id: int, transaction_type: str, quantity: float,
                            transaction_date, reference: str = "", note: str = "") -> InventoryTransaction:
        qty = require_positive_number(quantity, "Số lượng")
        date_val = require_valid_date(transaction_date, "Ngày giao dịch")

        with session_scope() as session:
            item = self._item_repo.get_by_id(session, item_id)
            if item is None:
                raise ValidationError("Không tìm thấy vật tư.")

            if transaction_type == InventoryTransactionType.EXPORT:
                if qty > item.quantity:
                    raise ValidationError("Số lượng xuất vượt quá tồn kho hiện có.")
                item.quantity -= qty
            elif transaction_type == InventoryTransactionType.IMPORT:
                item.quantity += qty
            elif transaction_type == InventoryTransactionType.ADJUSTMENT:
                if item.quantity + qty < 0:
                    raise ValidationError("Điều chỉnh khiến tồn kho bị âm.")
                item.quantity += qty
            else:
                raise ValidationError("Loại giao dịch không hợp lệ.")

            txn = InventoryTransaction(
                item_id=item_id, transaction_type=transaction_type, quantity=qty,
                transaction_date=date_val, reference=reference, note=note,
            )
            self._txn_repo.add(session, txn)
            session.flush()
            session.expunge(txn)
        log_action(actor, "INVENTORY_TXN", f"{transaction_type} item={item_id} qty={qty}")
        return txn
