"""
API Client for Desktop App.

Handles all REST API HTTP calls to FastAPI web backend:
- Health check (GET /health)
- JWT Authentication (POST /auth/login, POST /auth/refresh)
- REST CRUD endpoints with automatic Bearer token injection & refresh retry.
"""
from __future__ import annotations

import logging
from typing import Any
import requests

from app.config.settings import API_BASE_URL
from app.sync.token_manager import TokenManager

logger = logging.getLogger("wdf.sync.api_client")


class AuthRequiredError(Exception):
    """Raised when authentication tokens expire and refresh fails."""
    pass


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_manager = TokenManager()

    def check_health(self) -> dict[str, Any]:
        """
        Calls GET {API_BASE_URL}/health and logs backend engine / host.
        Returns result dict with 'online': True/False.
        """
        health_url = f"{self.base_url}/health"
        try:
            resp = requests.get(health_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                db_engine = data.get("database_engine", "PostgreSQL Cloud")
                db_host = data.get("database_host", "Neon Postgres")
                msg = f"Đã kết nối API tại {self.base_url}, database backend: {db_engine} @ {db_host}"
                logger.info(msg)
                return {
                    "online": True,
                    "database_engine": db_engine,
                    "database_host": db_host,
                    "connection_status": data.get("connection_status", "connected"),
                    "raw": data,
                }
        except Exception as e:
            msg = f"Không kết nối được API tại {self.base_url} ({e}), chạy chế độ offline hoàn toàn"
            logger.warning(msg)

        return {
            "online": False,
            "database_engine": "SQLite (Offline)",
            "database_host": "Local DB",
            "connection_status": "offline",
        }

    def login(self, username: str, password: str) -> dict[str, Any]:
        """
        Calls POST {API_BASE_URL}/auth/login and saves JWT tokens locally.
        """
        login_url = f"{self.base_url}/auth/login"
        payload = {"username": username, "password": password}
        try:
            resp = requests.post(login_url, json=payload, timeout=10)
            if resp.status_code != 200:
                # Try form-data payload in case backend uses OAuth2PasswordRequestForm
                resp = requests.post(login_url, data=payload, timeout=10)

            if resp.status_code in (200, 201):
                data = resp.json()
                access_token = data.get("access_token") or data.get("token")
                refresh_token = data.get("refresh_token", access_token)
                user_info = data.get("user", {})
                if access_token:
                    self.token_manager.save_tokens(access_token, refresh_token, user_info)
                return data
            else:
                logger.warning("API Login failed with status code %s: %s", resp.status_code, resp.text)
                raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng.")
        except requests.exceptions.ConnectionError as e:
            logger.warning("API connection error during login: %s", e)
            raise ConnectionError("Không thể kết nối API backend") from e

    def refresh_access_token(self) -> str | None:
        """
        Calls POST {API_BASE_URL}/auth/refresh using stored refresh token.
        """
        refresh_token = self.token_manager.get_refresh_token()
        if not refresh_token:
            raise AuthRequiredError("Không tìm thấy refresh token.")

        refresh_url = f"{self.base_url}/auth/refresh"
        headers = {"Authorization": f"Bearer {refresh_token}"}
        payload = {"refresh_token": refresh_token}
        try:
            resp = requests.post(refresh_url, json=payload, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                data = resp.json()
                new_access = data.get("access_token") or data.get("token")
                new_refresh = data.get("refresh_token", refresh_token)
                saved_user = self.token_manager.get_saved_user()
                if new_access:
                    self.token_manager.save_tokens(new_access, new_refresh, saved_user)
                    return new_access
            logger.warning("Token refresh rejected by server (HTTP %s)", resp.status_code)
        except Exception as e:
            logger.error("Error refreshing token: %s", e)

        raise AuthRequiredError("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.")

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self.token_manager.get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Execute HTTP request with automatic token header and 401 refresh retry."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())

        try:
            resp = requests.request(method, url, headers=headers, timeout=kwargs.pop("timeout", 10), **kwargs)
            if resp.status_code == 401:
                # Attempt to refresh token once
                try:
                    self.refresh_access_token()
                    headers.update(self._get_headers())
                    resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
                except AuthRequiredError:
                    raise
            return resp
        except requests.exceptions.RequestException as e:
            logger.warning("API request failed (%s %s): %s", method, endpoint, e)
            raise
