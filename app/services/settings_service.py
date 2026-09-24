"""
Application settings (farm info, theme) persisted to a small local JSON
file under data/. This is intentionally separate from the SQLite
business database — it holds presentation/configuration data, not
domain records, so a lightweight file store is appropriate here.
"""
from __future__ import annotations

import json

from app.config.settings import DATA_DIR, APP_NAME_VI, APP_VERSION, DATABASE_FILE
from app.utils.logger import log_action, get_logger

logger = get_logger("settings_service")
SETTINGS_FILE = DATA_DIR / "app_settings.json"

DEFAULTS = {
    "farm_name": "Trang trại Vịt Trời",
    "address": "",
    "phone": "",
    "unit_system": "Metric (kg, ml)",
    "theme": "light",
}


class SettingsService:
    def load(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                merged = {**DEFAULTS, **data}
                return merged
            except Exception:
                logger.exception("Failed to read settings file, using defaults.")
        return dict(DEFAULTS)

    def save(self, actor: str, **fields) -> dict:
        current = self.load()
        current.update({k: v for k, v in fields.items() if v is not None})
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        log_action(actor, "UPDATE_SETTINGS", str(fields))
        return current

    def app_info(self) -> dict:
        return {
            "name": APP_NAME_VI,
            "version": APP_VERSION,
            "database_path": str(DATABASE_FILE),
        }
