from __future__ import annotations

from dataclasses import dataclass

from app.database.connection import session_scope
from app.repositories.user_repository import UserRepository
from app.utils.security import verify_password
from app.utils.logger import log_action, get_logger
from app.config.constants import UserStatus, ROLE_MENU_PERMISSIONS

logger = get_logger("auth")


@dataclass
class CurrentUser:
    id: int
    username: str
    full_name: str
    role_name: str

    def can_access(self, menu_key: str) -> bool:
        return menu_key in ROLE_MENU_PERMISSIONS.get(self.role_name, set())


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self) -> None:
        self._user_repo = UserRepository()

    def login(self, username: str, password: str) -> CurrentUser:
        username = (username or "").strip()
        if not username or not password:
            raise AuthError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")

        with session_scope() as session:
            user = self._user_repo.get_by_username(session, username)
            if user is None or not verify_password(password, user.password_hash):
                logger.warning("Failed login attempt for username=%s", username)
                raise AuthError("Tên đăng nhập hoặc mật khẩu không đúng.")
            if user.status != UserStatus.ACTIVE:
                raise AuthError("Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.")

            current = CurrentUser(
                id=user.id, username=user.username, full_name=user.full_name,
                role_name=user.role.name,
            )
        log_action(current.username, "LOGIN", "Đăng nhập thành công")
        return current

    def logout(self, current_user: CurrentUser | None) -> None:
        if current_user:
            log_action(current_user.username, "LOGOUT", "Đăng xuất")
