"""
Wild Duck Farm Management System — entry point.

Run with:  python main.py
"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.config.settings import APP_NAME, ORGANIZATION_NAME, STYLES_DIR
from app.utils.logger import setup_logging, get_logger
from app.utils.error_handling import install_global_exception_hook
from app.database.connection import init_database
from app.database.seed import seed_database, run_alert_scan_after_seed

logger = get_logger("main")


def load_stylesheet() -> str:
    qss_path = STYLES_DIR / "app.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def bootstrap() -> None:
    """
    Create the database tables if needed, then seed demo data.

    seed_database() is idempotent (it checks whether roles already exist
    before inserting anything), so it is safe — and necessary — to call
    on every startup rather than only "on first run". Gating it behind a
    first-run flag meant that if seeding ever failed once (e.g. a
    dependency error while hashing a password), the tables would already
    exist and every later launch would skip seeding forever, leaving an
    empty database with no accounts. Always attempting it here means a
    previous failed seed self-heals on the next launch.
    """
    init_database()
    try:
        seed_database()
        run_alert_scan_after_seed()
    except Exception:
        logger.exception("Seeding demo data failed.")
        raise


def main() -> int:
    setup_logging()
    install_global_exception_hook()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setStyleSheet(load_stylesheet())

    try:
        bootstrap()
    except Exception as exc:
        logger.exception("Failed to initialize database/seed data.")
        QMessageBox.critical(
            None,
            "Lỗi khởi tạo dữ liệu",
            "Không thể khởi tạo hoặc nạp dữ liệu mẫu cho hệ thống.\n\n"
            f"Chi tiết: {exc}\n\n"
            "Vui lòng kiểm tra file log tại thư mục 'logs/' để biết thêm chi tiết.\n"
            "Ứng dụng vẫn sẽ mở, nhưng một số dữ liệu mẫu (tài khoản demo, "
            "đàn/chuồng/kho mẫu...) có thể chưa có sẵn.",
        )
        # Do not exit — the tables (if created) still let the app open;
        # the person can retry seeding by restarting once the underlying
        # issue (e.g. a missing dependency) is fixed.

    # Local import so PyQt6 / Qt is initialized before other Qt-dependent modules load.
    from app.ui.login_window import LoginWindow
    from app.ui.main_window import MainWindow

    state = {"main_window": None, "login_window": None}

    def show_login() -> None:
        state["login_window"] = LoginWindow(on_success=on_login_success)
        state["login_window"].show()

    def on_login_success(current_user) -> None:
        state["login_window"].close()
        state["login_window"] = None
        state["main_window"] = MainWindow(current_user, on_logout=on_logout)
        state["main_window"].show()

    def on_logout() -> None:
        state["main_window"].close()
        state["main_window"] = None
        show_login()

    show_login()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
