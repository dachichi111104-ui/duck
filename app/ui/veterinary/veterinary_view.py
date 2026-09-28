from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QMessageBox, QTabWidget, QFrame,
)

from app.services.veterinary_service import VeterinaryService
from app.services.flock_service import FlockService
from app.ui.components.kpi_card import KpiCard
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.veterinary.veterinary_record_dialog import VeterinaryRecordDialog
from app.config.constants import VetRecordStatus

COLUMNS = ["Ngày chẩn đoán", "Tên đàn", "Cá thể / Thẻ", "Bệnh nghi ngờ", "Triệu chứng", "Phác đồ điều trị", "Bác sĩ thú y", "Trạng thái", "Nguồn"]


class VeterinaryView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = VeterinaryService()
        self._flock_service = FlockService()
        self._all_records = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # KPI Summary Row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        layout.addLayout(self.kpi_layout)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.flock_filter = QComboBox()
        self.flock_filter.addItem("Tất cả các đàn vịt", None)
        for f in self._flock_service.list_flocks():
            self.flock_filter.addItem(f"{f.flock_code} — {f.name}", f.id)
        self.flock_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.flock_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Tất cả trạng thái bệnh án", None)
        for value, label in VetRecordStatus.LABELS_VI.items():
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.status_filter)

        edit_btn = QPushButton("Sửa bệnh án")
        edit_btn.setIcon(get_icon("fa5s.edit", color="#2E7D32"))
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        toolbar.addWidget(edit_btn)

        add_btn = QPushButton("Thêm Bệnh án mới")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_record)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        note = QLabel(
            "<b>Ghi chú Thú y:</b> Hồ sơ bệnh án ghi nhận tình trạng sức khỏe cá thể và theo dõi dịch bệnh theo đàn. "
            "Cảnh báo có nguồn <i>AI Analysis</i> thể hiện nghi vấn phát hiện tự động."
        )
        note.setStyleSheet("color: #68736B; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        self.empty_state = EmptyState("Chưa có hồ sơ bệnh án nào", "+ Thêm Bệnh án mới", self._add_record)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def _update_kpi_row(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(self._all_records)
        theo_doi = sum(1 for r in self._all_records if r.status in (VetRecordStatus.THEO_DOI, "UNDER_MONITORING"))
        dieu_tri = sum(1 for r in self._all_records if r.status == VetRecordStatus.DANG_DIEU_TRI)
        da_khoi = sum(1 for r in self._all_records if r.status == VetRecordStatus.DA_KHOI)

        self.kpi_layout.addWidget(KpiCard("TOTAL HEALTH RECORDS", f"{total} bệnh án", "fa5s.user-md", "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("UNDER MONITORING", f"{theo_doi} cá thể", "fa5s.eye", "#F4A62D" if theo_doi > 0 else "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("ACTIVE TREATMENT", f"{dieu_tri} cá thể", "fa5s.pills", "#D32F2F" if dieu_tri > 0 else "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("RECOVERED", f"{da_khoi} cá thể", "fa5s.check-circle", "#2E7D32"))

    def refresh(self) -> None:
        self._all_records = self._service.list_records()
        self._update_kpi_row()
        self._apply_filter()

    def _apply_filter(self) -> None:
        flock_id = self.flock_filter.currentData()
        status = self.status_filter.currentData()
        filtered = [
            r for r in self._all_records
            if (not flock_id or r.flock_id == flock_id) and
               (not status or r.status == status or (status == VetRecordStatus.THEO_DOI and r.status in (VetRecordStatus.THEO_DOI, "UNDER_MONITORING")))
        ]
        self.table.setRowCount(len(filtered))

        for row, r in enumerate(filtered):
            source_label = "AI Analysis" if r.source == "AI_ANALYSIS" else "Thủ công"
            st_text = VetRecordStatus.LABELS_VI.get(r.status, "Theo dõi" if r.status == "UNDER_MONITORING" else r.status)

            set_row(self.table, row, [
                r.diagnosis_date.isoformat(),
                r.flock.name if r.flock else "-",
                r.animal_reference or "Đàn chung",
                r.disease.name if r.disease else (r.diagnosis or "-"),
                r.symptoms or "-",
                r.treatment or "-",
                r.veterinarian or "-",
                st_text,
                source_label,
            ], row_data=r.id)

        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        rec_id = get_row_data(self.table, row)
        return next((r for r in self._all_records if r.id == rec_id), None)

    def _add_record(self) -> None:
        dlg = VeterinaryRecordDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "Sửa bệnh án", "Vui lòng chọn một bệnh án từ danh sách.")
            return
        dlg = VeterinaryRecordDialog(self.current_user, record=record, parent=self)
        if dlg.exec():
            self.refresh()
