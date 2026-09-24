"""
Global exception handling so the application never crashes silently on
unexpected errors (spec section 36). Tracebacks go to the log file;
the user only ever sees a friendly message box.
"""
from __future__ import annotations

import sys
import traceback

from PyQt6.QtWidgets import QMessageBox, QWidget

from app.utils.logger import get_logger

logger = get_logger("errors")


class AppError(Exception):
    """Raised for expected/validation errors that should show a friendly message."""


def install_global_exception_hook() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Unhandled exception:\n%s", tb_text)
        try:
            show_error_dialog(
                None,
                "Đã xảy ra lỗi",
                "Ứng dụng gặp sự cố ngoài ý muốn.\nVui lòng thử lại. "
                "Chi tiết lỗi đã được ghi vào log để kiểm tra.",
            )
        except Exception:
            pass

    sys.excepthook = _hook


def show_error_dialog(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()


def show_warning_dialog(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()


def show_info_dialog(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()


def confirm_dialog(parent: QWidget | None, title: str, message: str) -> bool:
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
