"""
Sync Status Widget for MainWindow status bar / bottom bar.

Displays real-time sync state using vector icons (QtAwesome):
- Green + "Đã đồng bộ với server"
- Spinner + "Đang đồng bộ..."
- Orange + "X thay đổi chờ đồng bộ (mất kết nối)"
- Red + "Có N xung đột cần xử lý"
- Server address label (e.g., "Server: localhost:8000")
"""
from __future__ import annotations

from urllib.parse import urlparse
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
)

from app.config.settings import API_BASE_URL
from app.ui.components.icons import get_icon


class SyncStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_url = API_BASE_URL
        parsed = urlparse(self.api_url)
        self.server_host = parsed.netloc or parsed.path or "localhost:8000"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        layout.addWidget(self.icon_label)

        self.status_label = QLabel("Đang kết nối API...")
        self.status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #26332A;")
        layout.addWidget(self.status_label)

        self.conflict_btn = QPushButton("Xử lý xung đột")
        self.conflict_btn.setIcon(get_icon("fa5s.exclamation-circle", color="#FFFFFF"))
        self.conflict_btn.setIconSize(QSize(11, 11))
        self.conflict_btn.setObjectName("DangerButton")
        self.conflict_btn.setFixedSize(110, 22)
        self.conflict_btn.setStyleSheet("""
            QPushButton#DangerButton {
                background-color: #D32F2F;
                color: #FFFFFF;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
            }
        """)
        self.conflict_btn.hide()
        layout.addWidget(self.conflict_btn)

        self.sync_now_btn = QPushButton(" Đồng bộ ngay")
        self.sync_now_btn.setIcon(get_icon("fa5s.sync", color="#2E7D32"))
        self.sync_now_btn.setIconSize(QSize(11, 11))
        self.sync_now_btn.setObjectName("SecondaryButton")
        self.sync_now_btn.setFixedSize(110, 22)
        self.sync_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_now_btn.setStyleSheet("""
            QPushButton#SecondaryButton {
                background-color: #FFFFFF;
                color: #2E7D32;
                border: 1px solid #D8E2DA;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #E8F3E9;
            }
        """)
        self.sync_now_btn.clicked.connect(self._trigger_manual_sync)
        layout.addWidget(self.sync_now_btn)

        layout.addStretch()

        self.server_label = QLabel(f"Server: {self.server_host}")
        self.server_label.setStyleSheet("font-size: 10px; color: #68736B; padding: 2px 6px; background-color: #E8F3E9; border-radius: 4px;")
        layout.addWidget(self.server_label)

        self.update_status(state="SYNCED", message="Đã đồng bộ với server", pending_count=0, conflict_count=0)

    def _trigger_manual_sync(self):
        from app.sync.sync_service import SyncService
        self.update_status(state="SYNCING", message="Đang kích hoạt đồng bộ...")
        service = SyncService.get_instance()
        if hasattr(service, "worker") and service.worker:
            service.worker._ensure_authenticated()
        service.trigger_sync_now()

    def update_status(self, state: str, message: str = "", pending_count: int = 0, conflict_count: int = 0) -> None:
        """
        State options: SYNCED, SYNCING, OFFLINE, CONFLICT, AUTH_ERROR
        """
        self.conflict_btn.hide()

        if conflict_count > 0 or state == "CONFLICT":
            self.icon_label.setPixmap(get_icon("fa5s.exclamation-triangle", color="#D32F2F").pixmap(QSize(14, 14)))
            self.status_label.setText(f"Có {conflict_count} xung đột cần xử lý")
            self.status_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #D32F2F;")
            self.conflict_btn.show()

        elif state == "SYNCING":
            self.icon_label.setPixmap(get_icon("fa5s.sync", color="#F4A62D").pixmap(QSize(14, 14)))
            self.status_label.setText("Đang đồng bộ...")
            self.status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #F4A62D;")

        elif state in ("OFFLINE", "DISCONNECTED"):
            self.icon_label.setPixmap(get_icon("fa5s.wifi", color="#F4A62D").pixmap(QSize(14, 14)))
            if pending_count > 0:
                self.status_label.setText(f"{pending_count} thay đổi chờ đồng bộ (mất kết nối)")
            else:
                self.status_label.setText("Ngoại tuyến (Chưa kết nối API)")
            self.status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #F4A62D;")

        elif state == "AUTH_ERROR":
            self.icon_label.setPixmap(get_icon("fa5s.lock", color="#D32F2F").pixmap(QSize(14, 14)))
            self.status_label.setText("Hết hạn phiên làm việc — Cần đăng nhập lại")
            self.status_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #D32F2F;")

        else:  # SYNCED / ONLINE
            self.icon_label.setPixmap(get_icon("fa5s.check-circle", color="#2E7D32").pixmap(QSize(14, 14)))
            self.status_label.setText("Đã đồng bộ với server")
            self.status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #2E7D32;")
