import datetime as dt

import pytest

from app.services.flock_service import FlockService
from app.services.barn_service import BarnService
from app.config.constants import FlockEventType
from app.utils.validators import ValidationError


@pytest.fixture
def barn():
    return BarnService().create_barn("tester", code="B-TEST", name="Chuồng test", location="Khu test", capacity=100)


def test_create_flock_within_capacity(barn):
    flock = FlockService().create_flock(
        "tester", flock_code="F-001", name="Đàn test", barn_id=barn.id,
        breed="Vịt trời", start_date=dt.date.today(), initial_count=50,
    )
    assert flock.current_count == 50

    updated_barn = BarnService().get_barn(barn.id)
    assert updated_barn.current_count == 50


def test_create_flock_exceeding_capacity_raises(barn):
    with pytest.raises(ValidationError):
        FlockService().create_flock(
            "tester", flock_code="F-002", name="Đàn quá tải", barn_id=barn.id,
            breed="Vịt trời", start_date=dt.date.today(), initial_count=999,
        )


def test_duplicate_flock_code_raises(barn):
    FlockService().create_flock(
        "tester", flock_code="F-003", name="Đàn A", barn_id=barn.id,
        breed="Vịt trời", start_date=dt.date.today(), initial_count=10,
    )
    with pytest.raises(ValidationError):
        FlockService().create_flock(
            "tester", flock_code="F-003", name="Đàn B", barn_id=barn.id,
            breed="Vịt trời", start_date=dt.date.today(), initial_count=10,
        )


def test_flock_death_event_reduces_counts(barn):
    flock = FlockService().create_flock(
        "tester", flock_code="F-004", name="Đàn C", barn_id=barn.id,
        breed="Vịt trời", start_date=dt.date.today(), initial_count=30,
    )
    FlockService().record_event(
        "tester", flock.id, event_type=FlockEventType.DEATH, quantity=5,
        event_date=dt.date.today(), reason="test",
    )
    details = FlockService().get_flock_details(flock.id)
    assert details.current_count == 25
    assert details.dead_count == 5

    updated_barn = BarnService().get_barn(barn.id)
    assert updated_barn.current_count == 25


def test_flock_addition_event_respects_barn_capacity(barn):
    flock = FlockService().create_flock(
        "tester", flock_code="F-005", name="Đàn D", barn_id=barn.id,
        breed="Vịt trời", start_date=dt.date.today(), initial_count=90,
    )
    with pytest.raises(ValidationError):
        FlockService().record_event(
            "tester", flock.id, event_type=FlockEventType.ADDITION, quantity=20,
            event_date=dt.date.today(),
        )
