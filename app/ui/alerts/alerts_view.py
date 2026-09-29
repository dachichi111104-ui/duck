"""
Dedicated System Alerts & Event Log View.
Allows filtering real-time alerts by severity (RED, ORANGE, GREEN) and status.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox,
)

from app.services.alert_service import AlertService
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.config.constants import AlertSeverity, AlertStatus

COLUMNS = ["Thời gian", "Loại cảnh báo", "Nguồn / Camera / Đàn", "Nội dung cảnh báo", "Mức độ", "Trạng thái"]


class AlertsView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = AlertService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title = QLabel("Nhật ký Cảnh báo & Sự cố Hệ thống")
        title.setObjectName("SectionTitle")
        toolbar.addWidget(title)

        self.severity_combo = QComboBox()
        self.severity_combo.addItem("Tất cả mức độ", None)
        self.severity_combo.addItem("Nguy cơ cao (RED)", AlertSeverity.RED)
        self.severity_combo.addItem("Cảnh báo (ORANGE)", AlertSeverity.ORANGE)
        self.severity_combo.addItem("Thông tin (GREEN)", AlertSeverity.GREEN)
        self.severity_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.severity_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Tất cả trạng thái", None)
        self.status_combo.addItem("Chưa đọc (UNREAD)", AlertStatus.UNREAD)
        self.status_combo.addItem("Đã đọc (READ)", AlertStatus.READ)
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.status_combo)

        toolbar.addStretch()

        mark_btn = QPushButton("Đánh dấu đã đọc tất cả")
        mark_btn.setIcon(get_icon("fa5s.check", color="#2E7D32"))
        mark_btn.setObjectName("SecondaryButton")
        mark_btn.clicked.connect(self._mark_all_read)
        toolbar.addWidget(mark_btn)

        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        self.empty_state = EmptyState("Không có cảnh báo nào phù hợp với bộ lọc")
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def refresh(self) -> None:
        self._apply_filter()

    def _apply_filter(self) -> None:
        sev = self.severity_combo.currentData()
        st = self.status_combo.currentData()

        notifications = self._service.list_notifications(limit=200)

        filtered = [
            n for n in notifications
            if (not sev or n.severity == sev) and (not st or n.status == st)
        ]

        self.table.setRowCount(len(filtered))
        for row, n in enumerate(filtered):
            ref_str = f"{n.reference_type or ''} #{n.reference_id or ''}".strip() or "System"
            set_row(self.table, row, [
                n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else "-",
                n.alert_type,
                ref_str,
                f"{n.title} — {n.message}",
                n.severity,
                "Chưa đọc" if n.status == AlertStatus.UNREAD else "Đã đọc",
            ], row_data=n.id)

        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _mark_all_read(self) -> None:
        self._service.mark_all_read()
        self.refresh()
        QMessageBox.information(self, "Thông báo", "Đã đánh dấu tất cả cảnh báo là đã đọc.")
