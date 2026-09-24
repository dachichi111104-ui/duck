from __future__ import annotations

from app.database.connection import session_scope
from app.database.models import User, Role
from app.repositories.user_repository import UserRepository, RoleRepository
from app.utils.security import hash_password
from app.utils.validators import require_not_empty, ValidationError
from app.utils.logger import log_action, get_logger
from app.config.constants import UserStatus

logger = get_logger("user_mgmt_service")


class UserManagementService:
    def __init__(self) -> None:
        self._user_repo = UserRepository()
        self._role_repo = RoleRepository()

    def list_users(self) -> list[User]:
        with session_scope() as session:
            users = self._user_repo.get_all_with_roles(session)
            session.expunge_all()
            return users

    def list_roles(self) -> list[Role]:
        with session_scope() as session:
            roles = self._role_repo.get_all(session)
            session.expunge_all()
            return roles

    def create_user(self, actor: str, username: str, password: str, full_name: str,
                     role_id: int, phone: str = "", email: str = "") -> User:
        username = require_not_empty(username, "Tên đăng nhập")
        full_name = require_not_empty(full_name, "Họ tên")
        if not password or len(password) < 4:
            raise ValidationError("Mật khẩu phải có ít nhất 4 ký tự.")

        with session_scope() as session:
            if self._user_repo.get_by_username(session, username):
                raise ValidationError(f"Tên đăng nhập '{username}' đã tồn tại.")
            user = User(
                username=username, password_hash=hash_password(password), full_name=full_name,
                role_id=role_id, phone=phone, email=email, status=UserStatus.ACTIVE,
            )
            self._user_repo.add(session, user)
            session.expunge(user)
        log_action(actor, "CREATE_USER", username)
        return user

    def update_user(self, actor: str, user_id: int, **fields) -> User:
        with session_scope() as session:
            user = self._user_repo.get_by_id(session, user_id)
            if user is None:
                raise ValidationError("Không tìm thấy người dùng.")
            if "full_name" in fields:
                user.full_name = require_not_empty(fields["full_name"], "Họ tên")
            for key in ("phone", "email", "role_id", "status"):
                if key in fields:
                    setattr(user, key, fields[key])
            if fields.get("new_password"):
                user.password_hash = hash_password(fields["new_password"])
            session.flush()
            session.expunge(user)
        log_action(actor, "UPDATE_USER", str(user_id))
        return user

    def delete_user(self, actor: str, user_id: int) -> None:
        with session_scope() as session:
            user = self._user_repo.get_by_id(session, user_id)
            if user is None:
                return
            self._user_repo.delete(session, user)
        log_action(actor, "DELETE_USER", str(user_id))
