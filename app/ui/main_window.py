from __future__ import annotations

import datetime as dt
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QMenu, QScrollArea,
)

from app.config.settings import APP_NAME_VI, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from app.config.constants import MenuKeys, Roles, ROLE_MENU_PERMISSIONS
from app.services.auth_service import CurrentUser, AuthService
from app.services.alert_service import AlertService
from app.ui.components.icons import get_menu_icon, get_icon
from app.utils.logger import get_logger

logger = get_logger("main_window")

SIDEBAR_STRUCTURE = [
    ("item", MenuKeys.DASHBOARD, "Dashboard"),
    ("item", MenuKeys.MONITORING, "Live Monitoring"),
    ("group", "Giám sát & AI", [
        (MenuKeys.CAMERAS, "Cameras"),
        (MenuKeys.AI_DETECTION, "AI Detection"),
    ]),
    ("group", "Quản lý Chăn nuôi", [
        (MenuKeys.FLOCKS, "Flocks"),
        (MenuKeys.BARNS, "Barns"),
        (MenuKeys.PRODUCTION, "Production"),
        (MenuKeys.INVENTORY, "Inventory"),
    ]),
    ("group", "Sức khỏe & Thú y", [
        (MenuKeys.VETERINARY, "Veterinary"),
        (MenuKeys.VACCINATION, "Vaccinations"),
        (MenuKeys.ALERTS, "Alerts"),
        (MenuKeys.HISTORY, "History"),
        (MenuKeys.REPORTS, "Reports"),
    ]),
    ("group", "Hệ thống", [
        (MenuKeys.USERS, "Users"),
        (MenuKeys.SETTINGS, "Settings"),
    ]),
]

PAGE_HEADERS = {
    MenuKeys.DASHBOARD: ("Dashboard", "Monitor flock health, farm activity and system status."),
    MenuKeys.MONITORING: ("Live Monitoring", "Monitor multiple farm cameras in real time."),
    MenuKeys.CAMERAS: ("Camera Management", "Configure and manage surveillance camera streams."),
    MenuKeys.AI_DETECTION: ("AI Detection", "Analyze duck behavior and identify abnormal activity."),
    MenuKeys.FLOCKS: ("Flock Management", "Overview flock statistics and manage duck populations."),
    MenuKeys.BARNS: ("Barn Management", "Manage duck barns, locations and housing capacity."),
    MenuKeys.PRODUCTION: ("Production Tracking", "Track egg production, weight averages and trends."),
    MenuKeys.INVENTORY: ("Inventory Management", "Track feed, medicine, supplies and stock alerts."),
    MenuKeys.VETERINARY: ("Veterinary Records", "Track duck health condition, diagnoses and treatments."),
    MenuKeys.VACCINATION: ("Vaccination Schedule", "Manage vaccination plans and upcoming due dates."),
    MenuKeys.ALERTS: ("System Alerts", "View and filter real-time farm alerts and warnings."),
    MenuKeys.HISTORY: ("Event History", "Audit logs and system activity history."),
    MenuKeys.REPORTS: ("Farm Reports", "Generate and export analytical farm management reports."),
    MenuKeys.USERS: ("User Management", "Manage application accounts and system access roles."),
    MenuKeys.SETTINGS: ("System Settings", "Configure farm preferences, camera options and system rules."),
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

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        root_layout.addWidget(right_wrap, 1)

        self._select_menu(MenuKeys.DASHBOARD)

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

    def _logout(self) -> None:
        self._auth_service.logout(self.current_user)
        self._on_logout()
