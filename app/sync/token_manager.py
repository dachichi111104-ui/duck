"""
Token Manager for desktop app authentication storage.

Persists JWT access_token, refresh_token, and user session profile
locally in data/tokens.json so that offline logins work seamlessly.
"""
from __future__ import annotations

import json
import logging
import datetime as dt
from typing import Any

from app.config.settings import TOKEN_STORAGE_FILE

logger = logging.getLogger("wdf.sync.tokens")


class TokenManager:
    def __init__(self) -> None:
        self.file_path = TOKEN_STORAGE_FILE

    def save_tokens(self, access_token: str, refresh_token: str, user_data: dict[str, Any] | None = None) -> None:
        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_data": user_data or {},
            "saved_at": dt.datetime.utcnow().isoformat(),
        }
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info("Saved authentication tokens locally.")
        except Exception as e:
            logger.error("Failed to save authentication tokens: %s", e)

    def load_tokens(self) -> dict[str, Any] | None:
        if not self.file_path.exists():
            return None
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load authentication tokens: %s", e)
            return None

    def clear_tokens(self) -> None:
        if self.file_path.exists():
            try:
                self.file_path.unlink()
                logger.info("Cleared local authentication tokens.")
            except Exception as e:
                logger.error("Failed to clear authentication tokens: %s", e)

    def get_access_token(self) -> str | None:
        data = self.load_tokens()
        return data.get("access_token") if data else None

    def get_refresh_token(self) -> str | None:
        data = self.load_tokens()
        return data.get("refresh_token") if data else None

    def get_saved_user(self) -> dict[str, Any] | None:
        data = self.load_tokens()
        return data.get("user_data") if data else None
