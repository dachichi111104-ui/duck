import datetime as dt

import pytest

from app.services.inventory_service import InventoryService
from app.database.connection import session_scope
from app.database.models import InventoryCategory
from app.config.constants import InventoryTransactionType
from app.utils.validators import ValidationError


@pytest.fixture
def category_id():
    with session_scope() as session:
        cat = InventoryCategory(name="Thức ăn test")
        session.add(cat)
        session.flush()
        return cat.id


def test_create_item_and_import(category_id):
    service = InventoryService()
    item = service.create_item(
        "tester", category_id=category_id, code="ITM-001", name="Cám test",
        unit="kg", minimum_quantity=10, unit_price=1000,
    )
    assert item.quantity == 0

    service.record_transaction(
        "tester", item.id, InventoryTransactionType.IMPORT, quantity=50,
        transaction_date=dt.date.today(),
    )
    updated = [i for i in service.list_items() if i.id == item.id][0]
    assert updated.quantity == 50


def test_export_more_than_stock_raises(category_id):
    service = InventoryService()
    item = service.create_item(
        "tester", category_id=category_id, code="ITM-002", name="Cám test 2",
        unit="kg", minimum_quantity=10, unit_price=1000,
    )
    service.record_transaction("tester", item.id, InventoryTransactionType.IMPORT, 20, dt.date.today())

    with pytest.raises(ValidationError):
        service.record_transaction("tester", item.id, InventoryTransactionType.EXPORT, 100, dt.date.today())


def test_low_stock_detection(category_id):
    service = InventoryService()
    item = service.create_item(
        "tester", category_id=category_id, code="ITM-003", name="Cám test 3",
        unit="kg", minimum_quantity=30, unit_price=1000,
    )
    service.record_transaction("tester", item.id, InventoryTransactionType.IMPORT, 10, dt.date.today())

    low_stock_codes = [i.code for i in service.get_low_stock_items()]
    assert "ITM-003" in low_stock_codes


def test_duplicate_item_code_raises(category_id):
    service = InventoryService()
    service.create_item("tester", category_id=category_id, code="ITM-004", name="A",
                         unit="kg", minimum_quantity=1, unit_price=1)
    with pytest.raises(ValidationError):
        service.create_item("tester", category_id=category_id, code="ITM-004", name="B",
                             unit="kg", minimum_quantity=1, unit_price=1)
