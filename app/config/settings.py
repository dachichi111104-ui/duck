"""
Application-wide settings.

Centralizes paths, database configuration, and app metadata so nothing
is hard-coded across the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # project root (wild_duck_farm/)

DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
VIDEOS_DIR = DATA_DIR / "videos"
EXPORTS_DIR = DATA_DIR / "exports"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
RESOURCES_DIR = BASE_DIR / "app" / "resources"
STYLES_DIR = RESOURCES_DIR / "styles"
ICONS_DIR = RESOURCES_DIR / "icons"

for _d in (DATABASE_DIR, VIDEOS_DIR, EXPORTS_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load environment variables from .env if present
# ---------------------------------------------------------------------------
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_FILE = DATABASE_DIR / "wild_duck_farm.db"
DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("WDF_DATABASE_URL", f"sqlite:///{DATABASE_FILE}"))

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "Wild Duck Farm Management System"
APP_NAME_VI = "Hệ thống quản lý chăn nuôi & thú y vịt trời"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "WildDuckFarm"

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_SALT = os.environ.get("WDF_SECRET_SALT", "wild-duck-farm-dev-salt")

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_WIDTH = 1240
DEFAULT_WINDOW_HEIGHT = 680
MIN_WINDOW_WIDTH = 980
MIN_WINDOW_HEIGHT = 560

LOW_STOCK_WARNING_ONLY = True  # if True, low-stock uses a single threshold field
EXPIRY_WARNING_DAYS = 30  # days before expiry to raise a warning alert
VACCINATION_DUE_SOON_DAYS = 7  # days before next vaccination date to warn

# ---------------------------------------------------------------------------
# API & Offline-First Sync Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("WDF_API_BASE_URL", os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")).rstrip("/")
SYNC_ENABLED = os.environ.get("WDF_SYNC_ENABLED", os.environ.get("SYNC_ENABLED", "true")).lower() in ("true", "1", "yes")
SYNC_INTERVAL_SECONDS = int(os.environ.get("WDF_SYNC_INTERVAL_SECONDS", os.environ.get("SYNC_INTERVAL_SECONDS", "30")))
TOKEN_STORAGE_FILE = DATA_DIR / "tokens.json"


