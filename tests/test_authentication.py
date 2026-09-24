import pytest

from app.database.seed import seed_database
from app.services.auth_service import AuthService, AuthError
from app.config.constants import Roles


@pytest.fixture(autouse=True)
def seeded():
    seed_database()


def test_login_success():
    user = AuthService().login("admin", "admin123")
    assert user.username == "admin"
    assert user.role_name == Roles.ADMIN


def test_login_wrong_password():
    with pytest.raises(AuthError):
        AuthService().login("admin", "wrong-password")


def test_login_unknown_user():
    with pytest.raises(AuthError):
        AuthService().login("nonexistent", "whatever")


def test_login_empty_fields():
    with pytest.raises(AuthError):
        AuthService().login("", "")


def test_password_is_hashed_in_db():
    from app.database.connection import session_scope
    from app.database.models import User

    with session_scope() as session:
        user = session.query(User).filter_by(username="admin").one()
        assert user.password_hash != "admin123"
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
