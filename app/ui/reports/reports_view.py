from __future__ import annotations

import datetime as dt

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QDateEdit, QPushButton,
    QMessageBox, QLabel,
)

from app.services.report_service import ReportService, ReportFilter
from app.services.flock_service import FlockService
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.utils.error_handling import show_info_dialog

REPORT_TYPES = {
    "flock": "Báo cáo đàn",
    "production": "Báo cáo sản lượng",
    "inventory": "Báo cáo kho",
    "veterinary": "Báo cáo thú y",
    "ai": "Báo cáo AI",
}


class ReportsView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = ReportService()
        self._flock_service = FlockService()
        self._current_rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        self.report_combo = QComboBox()
        for key, label in REPORT_TYPES.items():
            self.report_combo.addItem(label, key)
        self.report_combo.currentIndexChanged.connect(self._generate)
        toolbar.addWidget(self.report_combo)

        self.flock_filter = QComboBox()
        self.flock_filter.addItem("Tất cả đàn", None)
        for f in self._flock_service.list_flocks():
            self.flock_filter.addItem(f.flock_code, f.id)
        toolbar.addWidget(self.flock_filter)

        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        toolbar.addWidget(QLabel("Từ:"))
        toolbar.addWidget(self.date_from)

        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate())
        toolbar.addWidget(QLabel("Đến:"))
        toolbar.addWidget(self.date_to)

        generate_btn = QPushButton("Tạo báo cáo")
        generate_btn.clicked.connect(self._generate)
        toolbar.addWidget(generate_btn)

        export_btn = QPushButton("Export Excel")
        export_btn.setObjectName("SecondaryButton")
        export_btn.clicked.connect(self._export)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        self.table = build_table([])
        layout.addWidget(self.table)

        self.empty_state = EmptyState("Chưa có dữ liệu cho bộ lọc đã chọn.")
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self._generate()

    def refresh(self) -> None:
        self._generate()

    def _build_filter(self) -> ReportFilter:
        return ReportFilter(
            date_from=self.date_from.date().toPyDate(),
            date_to=self.date_to.date().toPyDate(),
            flock_id=self.flock_filter.currentData(),
        )

    def _generate(self) -> None:
        key = self.report_combo.currentData()
        filters = self._build_filter()

        if key == "flock":
            rows = self._service.flock_report_data(filters)
        elif key == "production":
            rows = self._service.production_report_data(filters)
        elif key == "inventory":
            rows = self._service.inventory_report_data(filters)
        elif key == "veterinary":
            rows = self._service.veterinary_report_data(filters)
        else:
            rows = self._service.ai_report_data(filters)

        self._current_rows = rows
        if rows:
            headers = list(rows[0].keys())
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                set_row(self.table, row_idx, [row.get(h, "") for h in headers])
        else:
            self.table.setRowCount(0)

        self.table.setVisible(bool(rows))
        self.empty_state.setVisible(not rows)

    def _export(self) -> None:
        if not self._current_rows:
            QMessageBox.information(self, "Export Excel", "Không có dữ liệu để xuất.")
            return
        key = self.report_combo.currentData()
        label = REPORT_TYPES.get(key, "report")
        path = self._service.export_to_excel(self.current_user.username, label, self._current_rows)
        show_info_dialog(self, "Xuất Excel thành công", f"Đã lưu báo cáo tại:\n{path}")
