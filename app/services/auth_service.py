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

        # 1. Attempt API Login
        from app.sync.api_client import APIClient
        api_client = APIClient()
        api_data = None
        try:
            api_data = api_client.login(username, password)
            logger.info("API Login succeeded for username=%s", username)
        except ConnectionError:
            logger.info("API connection unavailable during login for username=%s. Falling back to local offline auth.", username)
        except Exception as e:
            logger.warning("API Login error (%s). Falling back to local offline auth.", e)

        # 2. Local SQLite Sync/Lookup
        with session_scope() as session:
            user = self._user_repo.get_by_username(session, username)

            if api_data:
                user_info = api_data.get("user", {})
                role_name = user_info.get("role") or user_info.get("role_name", "ADMIN")
                if user is None:
                    # Create user in local SQLite with remote user profile
                    from app.repositories.user_repository import RoleRepository
                    from app.utils.security import hash_password
                    from app.database.models import User
                    role = RoleRepository().get_by_name(session, role_name)
                    if not role:
                        role = RoleRepository().get_all(session)[0]
                    user = User(
                        username=username,
                        password_hash=hash_password(password),
                        full_name=user_info.get("full_name") or username,
                        email=user_info.get("email"),
                        phone=user_info.get("phone"),
                        role_id=role.id,
                        status=UserStatus.ACTIVE,
                        remote_id=user_info.get("id"),
                        sync_status="SYNCED",
                    )
                    session.add(user)
                    session.flush()

                current = CurrentUser(
                    id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    role_name=user.role.name if user.role else role_name,
                )
                log_action(current.username, "LOGIN", "Đăng nhập thành công qua API Web")
                return current

            # Offline Fallback Verification
            if user is None or not verify_password(password, user.password_hash):
                logger.warning("Failed login attempt for username=%s", username)
                raise AuthError("Tên đăng nhập hoặc mật khẩu không đúng.")
            if user.status != UserStatus.ACTIVE:
                raise AuthError("Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.")

            current = CurrentUser(
                id=user.id, username=user.username, full_name=user.full_name,
                role_name=user.role.name,
            )
        log_action(current.username, "LOGIN", "Đăng nhập thành công (Chế độ Ngoại tuyến)")
        return current

    def logout(self, current_user: CurrentUser | None) -> None:
        if current_user:
            from app.sync.token_manager import TokenManager
            TokenManager().clear_tokens()
            log_action(current_user.username, "LOGOUT", "Đăng xuất")

