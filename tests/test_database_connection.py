from app.database.connection import session_scope, get_engine
from app.database.models import Role
from sqlalchemy import inspect


def test_tables_created():
    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    expected = {
        "users", "roles", "barns", "flocks", "flock_events", "production_records",
        "inventory_categories", "inventory_items", "inventory_transactions",
        "diseases", "veterinary_records", "vaccinations",
        "ai_analysis_sessions", "ai_detection_results", "ai_alerts", "notifications",
    }
    assert expected.issubset(tables)


def test_session_scope_commits():
    with session_scope() as session:
        session.add(Role(name="TEST_ROLE", description="unit test role"))

    with session_scope() as session:
        role = session.query(Role).filter_by(name="TEST_ROLE").one_or_none()
        assert role is not None


def test_session_scope_rolls_back_on_error():
    try:
        with session_scope() as session:
            session.add(Role(name="ROLLBACK_ROLE"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    with session_scope() as session:
        role = session.query(Role).filter_by(name="ROLLBACK_ROLE").one_or_none()
        assert role is None
