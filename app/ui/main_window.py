from __future__ import annotations

import datetime as dt
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QMenu, QScrollArea, QMessageBox,
)

from app.config.settings import APP_NAME_VI, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from app.config.constants import MenuKeys, Roles, ROLE_MENU_PERMISSIONS
from app.services.auth_service import CurrentUser, AuthService
from app.services.alert_service import AlertService
from app.ui.components.icons import get_menu_icon, get_icon
from app.utils.logger import get_logger

logger = get_logger("main_window")

SIDEBAR_STRUCTURE = [
    ("item", MenuKeys.DASHBOARD, "Bảng điều khiển"),
    ("item", MenuKeys.MONITORING, "Giám sát trực tiếp"),
    ("group", "Giám sát & AI", [
        (MenuKeys.CAMERAS, "Quản lý Camera"),
        (MenuKeys.AI_DETECTION, "Nhận diện & AI"),
    ]),
    ("group", "Quản lý Chăn nuôi", [
        (MenuKeys.FLOCKS, "Đàn vịt"),
        (MenuKeys.BARNS, "Chuồng nuôi"),
        (MenuKeys.PRODUCTION, "Sản lượng trứng"),
        (MenuKeys.INVENTORY, "Kho & Vật tư"),
    ]),
    ("group", "Sức khỏe & Thú y", [
        (MenuKeys.VETERINARY, "Hồ sơ bệnh án"),
        (MenuKeys.VACCINATION, "Lịch tiêm phòng"),
        (MenuKeys.ALERTS, "Cảnh báo hệ thống"),
        (MenuKeys.HISTORY, "Lịch sử hoạt động"),
        (MenuKeys.REPORTS, "Báo cáo & Thống kê"),
    ]),
    ("group", "Hệ thống", [
        (MenuKeys.USERS, "Tài khoản người dùng"),
        (MenuKeys.SETTINGS, "Cài đặt hệ thống"),
    ]),
]

PAGE_HEADERS = {
    MenuKeys.DASHBOARD: ("Bảng điều khiển", "Theo dõi tổng quan tình hình chăn nuôi, sức khỏe đàn vịt và hệ thống."),
    MenuKeys.MONITORING: ("Giám sát trực tiếp", "Theo dõi các góc camera tại các chuồng vịt theo thời gian thực."),
    MenuKeys.CAMERAS: ("Quản lý Camera", "Cấu hình danh sách camera giám sát và kết nối luồng RTSP."),
    MenuKeys.AI_DETECTION: ("Nhận diện & Chẩn đoán AI", "Phân tích hành vi đàn vịt, phát hiện tự động dấu hiệu bệnh và phân tích mật độ."),
    MenuKeys.FLOCKS: ("Quản lý Đàn vịt", "Theo dõi số lượng cá thể, biến động đàn và tỷ lệ sống."),
    MenuKeys.BARNS: ("Quản lý Chuồng nuôi", "Quản lý các khu vực chuồng nuôi, vị trí và sức chứa."),
    MenuKeys.PRODUCTION: ("Theo dõi Sản lượng Trứng", "Ghi nhận thu hoạch trứng hàng ngày, tính bình quân và biểu đồ xu hướng."),
    MenuKeys.INVENTORY: ("Quản lý Kho & Vật tư", "Theo dõi nhập xuất tồn cám, thuốc thú y, vắc xin và cảnh báo định mức."),
    MenuKeys.VETERINARY: ("Hồ sơ Bệnh án Thú y", "Ghi nhận tình trạng sức khỏe đàn vịt, chẩn đoán và phác đồ điều trị."),
    MenuKeys.VACCINATION: ("Lịch Tiêm phòng", "Kế hoạch tiêm vắc xin phòng dịch tả, tụ huyết trùng và nhắc nhở hạn tiêm."),
    MenuKeys.ALERTS: ("Cảnh báo Hệ thống", "Xem và xử lý danh sách cảnh báo tự động về sức khỏe, tồn kho và thiết bị."),
    MenuKeys.HISTORY: ("Lịch sử Hoạt động", "Nhật ký kiểm toán hệ thống và lịch sử các thao tác đã diễn ra."),
    MenuKeys.REPORTS: ("Báo cáo & Thống kê", "Tổng hợp báo cáo trang trại, xuất file Excel và phân tích mật độ đàn."),
    MenuKeys.USERS: ("Quản lý Người dùng", "Quản lý tài khoản truy cập và phân quyền nhân viên trang trại."),
    MenuKeys.SETTINGS: ("Cài đặt Hệ thống", "Tùy chỉnh thông số trang trại, thiết lập AI và thông báo."),
}


class MainWindow(QMainWindow):
    def __init__(self, current_user: CurrentUser, on_logout):
        super().__init__()
        self.current_user = current_user
        self._on_logout = on_logout
        self._auth_service = AuthService()
        self._alert_service = AlertService()
        self._views: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle(f"DUCK AI — Wild Duck Farm Monitoring System ({current_user.full_name})")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        right_col.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        right_col.addWidget(self.stack, 1)

        # Bottom Sync Status Widget
        from app.ui.components.sync_status_widget import SyncStatusWidget
        from app.sync.sync_service import SyncService
        self.sync_widget = SyncStatusWidget()
        self.sync_widget.conflict_btn.clicked.connect(self._open_conflict_dialog)
        right_col.addWidget(self.sync_widget)

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        root_layout.addWidget(right_wrap, 1)

        self._select_menu(MenuKeys.DASHBOARD)

        # Start Background Offline-First Sync Service
        self.sync_service = SyncService.get_instance(parent=self)
        self.sync_service.worker.sync_status_changed.connect(self.sync_widget.update_status)
        self.sync_service.worker.conflict_occurred.connect(self._on_sync_conflict)
        self.sync_service.start()

        # Clock timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # Notification scan timer
        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._refresh_notification_badge)
        self._notif_timer.start(30_000)
        self._refresh_notification_badge()

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Header (Fixed at top)
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #FFFFFF;")
        hdr_layout = QVBoxLayout(header_widget)
        hdr_layout.setContentsMargins(10, 6, 10, 2)
        hdr_layout.setSpacing(0)

        logo_lbl = QLabel("DUCK AI")
        logo_lbl.setObjectName("SidebarLogo")
        hdr_layout.addWidget(logo_lbl)

        subtitle = QLabel("Wild Duck Farm Monitoring")
        subtitle.setObjectName("SidebarSubtitle")
        hdr_layout.addWidget(subtitle)

        layout.addWidget(header_widget)

        # 2. Scrollable Middle Navigation Area (With clean ScrollArea)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #FFFFFF;")

        nav_container = QWidget()
        nav_container.setStyleSheet("background-color: #FFFFFF;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        for entry in SIDEBAR_STRUCTURE:
            if entry[0] == "item":
                _, key, label = entry
                self._add_sidebar_button(nav_layout, key, label)
            else:
                _, group_label, items = entry
                visible_items = [i for i in items if self._user_can_access(i[0])]
                if not visible_items:
                    continue
                group_label_widget = QLabel(group_label)
                group_label_widget.setObjectName("SidebarGroupLabel")
                nav_layout.addWidget(group_label_widget)
                for key, label in visible_items:
                    self._add_sidebar_button(nav_layout, key, label)

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        # 3. Sidebar Footer (PINNED ALWAYS AT THE BOTTOM)
        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        footer.setFixedHeight(42)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 4, 8, 4)
        footer_layout.setSpacing(6)

        avatar_lbl = QLabel()
        avatar_lbl.setPixmap(get_icon("fa5s.user-circle", color="#26332A").pixmap(QSize(18, 18)))
        footer_layout.addWidget(avatar_lbl)

        user_info = QVBoxLayout()
        user_info.setSpacing(1)
        name_label = QLabel(self.current_user.full_name)
        name_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #26332A; background: transparent;")
        role_label = QLabel(Roles.LABELS_VI.get(self.current_user.role_name, self.current_user.role_name))
        role_label.setStyleSheet("color: #68736B; font-size: 9px; background: transparent;")
        user_info.addWidget(name_label)
        user_info.addWidget(role_label)
        footer_layout.addLayout(user_info, 1)

        logout_btn = QPushButton()
        logout_btn.setIcon(get_icon("fa5s.power-off", color="#FFFFFF"))
        logout_btn.setIconSize(QSize(11, 11))
        logout_btn.setObjectName("DangerButton")
        logout_btn.setFixedSize(26, 26)
        logout_btn.setToolTip("Đăng xuất")
        logout_btn.clicked.connect(self._logout)
        footer_layout.addWidget(logout_btn)

        layout.addWidget(footer)
        return sidebar

    def _user_can_access(self, key: str) -> bool:
        allowed = ROLE_MENU_PERMISSIONS.get(self.current_user.role_name, set())
        return key in allowed

    def _add_sidebar_button(self, layout: QVBoxLayout, key: str, label: str) -> None:
        if not self._user_can_access(key):
            return
        btn = QPushButton(f"  {label}")
        btn.setObjectName("SidebarButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn.setIcon(get_menu_icon(key, color="#26332A"))
        btn.setIconSize(QSize(13, 13))

        btn.clicked.connect(lambda _checked, k=key: self._select_menu(k))
        layout.addWidget(btn)
        self._nav_buttons[key] = btn

    def _build_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(46)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(0)
        self.title_label = QLabel("Dashboard")
        self.title_label.setObjectName("TopbarTitle")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #26332A; background: transparent;")
        self.subtitle_label = QLabel("Monitor flock health, farm activity and system status.")
        self.subtitle_label.setObjectName("TopbarSubtitle")
        self.subtitle_label.setStyleSheet("font-size: 10px; color: #68736B; background: transparent;")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)
        layout.addStretch()

        self.clock_label = QLabel()
        self.clock_label.setObjectName("ClockLabel")
        self.clock_label.setFixedHeight(26)
        layout.addWidget(self.clock_label)

        status_badge = QLabel("● AI Ready")
        status_badge.setObjectName("BadgeSuccess")
        status_badge.setFixedHeight(26)
        layout.addWidget(status_badge)

        self.notif_btn = QPushButton(" 4")
        self.notif_btn.setIcon(get_icon("fa5s.bell", color="#F4A62D"))
        self.notif_btn.setIconSize(QSize(11, 11))
        self.notif_btn.setObjectName("SecondaryButton")
        self.notif_btn.setFixedHeight(26)
        self.notif_btn.setStyleSheet("""
            QPushButton#SecondaryButton {
                background-color: #FFFFFF;
                color: #2E7D32;
                border: 1px solid #D8E2DA;
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
                min-height: 0px;
                max-height: 26px;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #E8F3E9;
                border-color: #2E7D32;
            }
        """)
        self.notif_btn.clicked.connect(self._show_notification_menu)
        layout.addWidget(self.notif_btn)

        user_label = QLabel(f"👤 {self.current_user.full_name}")
        user_label.setFixedHeight(26)
        user_label.setStyleSheet("font-weight: 600; color: #26332A; font-size: 11px; padding-left: 4px;")
        layout.addWidget(user_label)

        return topbar

    def _update_clock(self):
        now = dt.datetime.now()
        self.clock_label.setText(now.strftime("%Y-%m-%d  %H:%M:%S"))

    # ------------------------------------------------------------------
    def _select_menu(self, key: str) -> None:
        for k, btn in self._nav_buttons.items():
            is_active = (k == key)
            btn.setChecked(is_active)

            if is_active:
                btn.setStyleSheet("""
                    QPushButton#SidebarButton {
                        background-color: #2E7D32;
                        color: #FFFFFF;
                        font-weight: 700;
                        border-radius: 5px;
                        margin: 1px 8px;
                        padding: 6px 10px;
                        text-align: left;
                        border: none;
                    }
                """)
                btn.setIcon(get_menu_icon(k, color="#FFFFFF"))
            else:
                btn.setStyleSheet("""
                    QPushButton#SidebarButton {
                        background-color: transparent;
                        color: #26332A;
                        font-weight: 500;
                        border-radius: 5px;
                        margin: 1px 8px;
                        padding: 6px 10px;
                        text-align: left;
                        border: none;
                    }
                    QPushButton#SidebarButton:hover {
                        background-color: #E8F3E9;
                        color: #1B5E20;
                    }
                """)
                btn.setIcon(get_menu_icon(k, color="#26332A"))

        title, subtitle = PAGE_HEADERS.get(key, (key, ""))
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)

        if key not in self._views:
            self._views[key] = self._create_view(key)
            self.stack.addWidget(self._views[key])
        widget = self._views[key]
        if hasattr(widget, "refresh"):
            widget.refresh()
        self.stack.setCurrentWidget(widget)

    def _create_view(self, key: str) -> QWidget:
        if key == MenuKeys.DASHBOARD:
            from app.ui.dashboard.dashboard_view import DashboardView
            return DashboardView(self.current_user)
        if key == MenuKeys.MONITORING:
            from app.ui.monitoring.monitoring_view import MonitoringView
            return MonitoringView(self.current_user)
        if key == MenuKeys.CAMERAS:
            from app.ui.cameras.camera_view import CameraManagementView
            return CameraManagementView(self.current_user)
        if key == MenuKeys.AI_DETECTION:
            from app.ui.ai_monitoring.ai_view import AIMonitoringView
            return AIMonitoringView(self.current_user)
        if key == MenuKeys.FLOCKS:
            from app.ui.flocks.flock_list_view import FlockListView
            return FlockListView(self.current_user)
        if key == MenuKeys.BARNS:
            from app.ui.barns.barn_view import BarnView
            return BarnView(self.current_user)
        if key == MenuKeys.PRODUCTION:
            from app.ui.production.production_view import ProductionView
            return ProductionView(self.current_user)
        if key == MenuKeys.INVENTORY:
            from app.ui.inventory.inventory_view import InventoryView
            return InventoryView(self.current_user)
        if key == MenuKeys.VETERINARY:
            from app.ui.veterinary.veterinary_view import VeterinaryView
            return VeterinaryView(self.current_user)
        if key == MenuKeys.VACCINATION:
            from app.ui.veterinary.vaccination_view import VaccinationView
            return VaccinationView(self.current_user)
        if key == MenuKeys.ALERTS:
            from app.ui.alerts.alerts_view import AlertsView
            return AlertsView(self.current_user)
        if key == MenuKeys.HISTORY:
            from app.ui.history.history_view import HistoryView
            return HistoryView(self.current_user)
        if key == MenuKeys.REPORTS:
            from app.ui.reports.reports_view import ReportsView
            return ReportsView(self.current_user)
        if key == MenuKeys.USERS:
            from app.ui.users.users_view import UsersView
            return UsersView(self.current_user)
        if key == MenuKeys.SETTINGS:
            from app.ui.settings.settings_view import SettingsView
            return SettingsView(self.current_user)

        placeholder = QLabel(f"Page under construction: {key}")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return placeholder

    # ------------------------------------------------------------------
    def _refresh_notification_badge(self) -> None:
        try:
            self._alert_service.run_full_scan()
            count = self._alert_service.unread_count()
        except Exception:
            logger.exception("Failed to refresh notifications")
            return
        self.notif_btn.setText(f" {count}" if count else "")

    def _show_notification_menu(self) -> None:
        notifications = self._alert_service.list_notifications(limit=15)
        menu = QMenu(self)
        if not notifications:
            menu.addAction("Không có cảnh báo mới").setEnabled(False)
        else:
            for n in notifications:
                action = menu.addAction(f"{n.title} — {n.message[:50]}")
                action.setEnabled(False)
            menu.addSeparator()
            mark_all = menu.addAction("Đánh dấu tất cả đã đọc")
            mark_all.triggered.connect(self._mark_all_read)
        menu.exec(self.notif_btn.mapToGlobal(self.notif_btn.rect().bottomLeft()))

    def _mark_all_read(self) -> None:
        self._alert_service.mark_all_read()
        self._refresh_notification_badge()

    def _on_sync_conflict(self, entity_name: str, local_id: int) -> None:
        logger.warning("Sync conflict signal received for %s (id=%s)", entity_name, local_id)

    def _open_conflict_dialog(self) -> None:
        from app.sync.conflict_dialog import ConflictResolutionDialog
        dlg = ConflictResolutionDialog(
            entity_name="Dữ liệu chăn nuôi / kho",
            local_info="Tên: Đàn Vịt Trời A1\nSố lượng: 120\nTrạng thái: Đang theo dõi (Chỉnh sửa cục bộ)",
            remote_info="Tên: Đàn Vịt Trời A1\nSố lượng: 115\nTrạng thái: Hoàn thành (Cập nhật từ Web)",
            parent=self
        )
        if dlg.exec():
            choice = dlg.result_choice
            if choice == "keep_local":
                logger.info("User selected: Keep Local")
            elif choice == "use_remote":
                logger.info("User selected: Use Remote")
            if hasattr(self, "sync_service"):
                self.sync_service.trigger_sync_now()

    def _logout(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Xác nhận đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất khỏi hệ thống không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if hasattr(self, "sync_service"):
            self.sync_service.stop()
        self._auth_service.logout(self.current_user)
        self._on_logout()

    def closeEvent(self, event) -> None:
        if hasattr(self, "sync_service"):
            self.sync_service.stop()
        super().closeEvent(event)
