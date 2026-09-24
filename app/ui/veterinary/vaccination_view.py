from __future__ import annotations

import datetime as dt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from app.services.veterinary_service import VeterinaryService
from app.ui.components.kpi_card import KpiCard
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.ui.components.icons import get_icon
from app.config.constants import VaccinationStatus

COLUMNS = ["Đàn vịt", "Tên Vắc xin", "Ngày tiêm vừa qua", "Hạn tiêm tiếp theo", "Liều lượng", "Bác sĩ thực hiện", "Trạng thái lịch"]


def _computed_status(v) -> tuple[str, str]:
    if v.next_date is None:
        return "Hoàn thành", "success"
    today = dt.date.today()
    if v.next_date < today:
        return "Quá hạn", "danger"
    if (v.next_date - today).days <= 7:
        return "Sắp đến hạn", "warning"
    return "Đã lên lịch", "neutral"


class VaccinationView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = VeterinaryService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # KPI row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        layout.addLayout(self.kpi_layout)

        toolbar = QHBoxLayout()
        title_lbl = QLabel("Quản lý & Lịch Tiêm phòng Dịch tả / Tụ huyết trùng")
        title_lbl.setObjectName("SectionTitle")
        toolbar.addWidget(title_lbl)
        toolbar.addStretch()

        add_btn = QPushButton("Ghi nhận tiêm phòng")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_vaccination)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        self.empty_state = EmptyState("Chưa có lịch tiêm phòng nào", "Ghi nhận tiêm phòng", self._add_vaccination)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def _update_kpi_row(self, items):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(items)
        overdue = sum(1 for v in items if _computed_status(v)[0] == "Quá hạn")
        due_soon = sum(1 for v in items if _computed_status(v)[0] == "Sắp đến hạn")
        completed = sum(1 for v in items if _computed_status(v)[0] == "Hoàn thành")

        self.kpi_layout.addWidget(KpiCard("TOTAL SCHEDULED", f"{total} đợt", "fa5s.syringe", "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("OVERDUE VACCINES", f"{overdue} đợt", "fa5s.exclamation-circle", "#D32F2F" if overdue > 0 else "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("DUE WITHIN 7 DAYS", f"{due_soon} đợt", "fa5s.clock", "#F4A62D" if due_soon > 0 else "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("COMPLETED", f"{completed} đợt", "fa5s.check-circle", "#2E7D32"))

    def refresh(self) -> None:
        items = self._service.list_vaccinations()
        self._update_kpi_row(items)
        self.table.setRowCount(len(items))

        for row, v in enumerate(items):
            st_text, tone = _computed_status(v)
            set_row(self.table, row, [
                v.flock.flock_code if v.flock else "-", v.vaccine_name,
                v.vaccination_date.isoformat(), v.next_date.isoformat() if v.next_date else "-",
                v.dosage or "-", v.veterinarian or "-", st_text,
            ])

        self.table.setVisible(bool(items))
        self.empty_state.setVisible(not items)

    def _add_vaccination(self) -> None:
        from app.ui.veterinary.vaccination_dialog import VaccinationDialog
        dlg = VaccinationDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()
