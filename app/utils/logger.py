"""
Application logging setup.

Logs to both a rotating file under logs/ and the console. Used for
login/logout, CRUD operations, DB errors, AI analysis, and exports
(see spec section 35).
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import LOGS_DIR

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return

    log_file = LOGS_DIR / "wild_duck_farm.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger("wdf")
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"wdf.{name}")


def log_action(actor: str, action: str, detail: str = "") -> None:
    """Convenience helper for audit-style log lines (login, CRUD, export...)."""
    get_logger("audit").info("user=%s action=%s detail=%s", actor, action, detail)
