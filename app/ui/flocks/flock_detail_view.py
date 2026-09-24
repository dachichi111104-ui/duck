from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QFrame,
)

from app.services.flock_service import FlockService
from app.services.veterinary_service import VeterinaryService
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.ui.flocks.flock_event_dialog import FlockEventDialog
from app.ui.flocks.production_dialog import ProductionRecordDialog
from app.config.constants import FlockEventType, VetRecordStatus


class FlockDetailView(QWidget):
    def __init__(self, current_user, flock_id: int, on_back, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.flock_id = flock_id
        self._on_back = on_back
        self._flock_service = FlockService()
        self._vet_service = VeterinaryService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        back_btn = QPushButton("← Quay lại")
        back_btn.setObjectName("SecondaryButton")
        back_btn.clicked.connect(self._on_back)
        header.addWidget(back_btn)
        header.addStretch()
        layout.addLayout(header)

        self.title_label = QLabel()
        self.title_label.setObjectName("SectionTitle")
        layout.addWidget(self.title_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.overview_tab = QWidget()
        self.events_tab = QWidget()
        self.production_tab = QWidget()
        self.vet_tab = QWidget()
        self.vaccination_tab = QWidget()
        self.ai_tab = QWidget()

        self.tabs.addTab(self.overview_tab, "Tổng quan")
        self.tabs.addTab(self.events_tab, "Biến động")
        self.tabs.addTab(self.production_tab, "Sản lượng")
        self.tabs.addTab(self.vet_tab, "Bệnh án")
        self.tabs.addTab(self.vaccination_tab, "Tiêm phòng")
        self.tabs.addTab(self.ai_tab, "AI")

        self._build_overview_tab()
        self._build_events_tab()
        self._build_production_tab()
        self._build_vet_tab()
        self._build_vaccination_tab()
        self._build_ai_tab()

        self.load_data()

    # ------------------------------------------------------------------
    def load_data(self) -> None:
        flock = self._flock_service.get_flock_details(self.flock_id)
        if flock is None:
            self.title_label.setText("Không tìm thấy đàn")
            return
        self.flock = flock
        self.title_label.setText(f"{flock.flock_code} — {flock.name}")
        self._refresh_overview()
        self._refresh_events()
        self._refresh_production()
        self._refresh_vet()
        self._refresh_vaccination()
        self._refresh_ai()

    # --- Overview -----------------------------------------------------
    def _build_overview_tab(self) -> None:
        self._overview_layout = QVBoxLayout(self.overview_tab)

    def _refresh_overview(self) -> None:
        while self._overview_layout.count():
            item = self._overview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        f = self.flock
        rows = [
            ("Mã đàn", f.flock_code), ("Tên đàn", f.name),
            ("Loài", f.species), ("Giống", f.breed or "-"),
            ("Chuồng", f.barn.code if f.barn else "-"),
            ("Ngày nhập", f.start_date.isoformat()),
            ("Số lượng ban đầu", f.initial_count),
            ("Số lượng hiện tại", f.current_count),
            ("Số chết", f.dead_count),
            ("Tỷ lệ sống", f"{f.survival_rate}%"),
            ("Trạng thái", f.status),
            ("Ghi chú", f.notes or "-"),
        ]
        for label, value in rows:
            row_widget = QLabel(f"<b>{label}:</b> {value}")
            self._overview_layout.addWidget(row_widget)
        self._overview_layout.addStretch()

    # --- Events ---------------------------------------------------------
    def _build_events_tab(self) -> None:
        layout = QVBoxLayout(self.events_tab)
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("+ Ghi nhận biến động")
        add_btn.clicked.connect(self._add_event)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.events_table = build_table(["Ngày", "Loại", "Số lượng", "Lý do"])
        layout.addWidget(self.events_table)

    def _refresh_events(self) -> None:
        events = sorted(self.flock.events, key=lambda e: e.event_date, reverse=True)
        self.events_table.setRowCount(len(events))
        for row, e in enumerate(events):
            set_row(self.events_table, row, [
                e.event_date.isoformat(), FlockEventType.LABELS_VI.get(e.event_type, e.event_type),
                e.quantity, e.reason or "",
            ])

    def _add_event(self) -> None:
        dlg = FlockEventDialog(self.current_user, self.flock_id, parent=self)
        if dlg.exec():
            self.load_data()

    # --- Production -------------------------------------------------------
    def _build_production_tab(self) -> None:
        layout = QVBoxLayout(self.production_tab)
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("+ Ghi nhận sản lượng")
        add_btn.clicked.connect(self._add_production)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.production_table = build_table(["Ngày", "Sản lượng trứng", "Trọng lượng TB", "Thức ăn (kg)"])
        layout.addWidget(self.production_table)

    def _refresh_production(self) -> None:
        records = sorted(self.flock.production_records, key=lambda r: r.record_date, reverse=True)
        self.production_table.setRowCount(len(records))
        for row, r in enumerate(records):
            set_row(self.production_table, row, [
                r.record_date.isoformat(), r.egg_quantity,
                r.average_weight or "-", r.feed_consumption or "-",
            ])

    def _add_production(self) -> None:
        dlg = ProductionRecordDialog(self.current_user, self.flock_id, parent=self)
        if dlg.exec():
            self.load_data()

    # --- Veterinary ---------------------------------------------------
    def _build_vet_tab(self) -> None:
        layout = QVBoxLayout(self.vet_tab)
        self.vet_table = build_table(["Ngày", "Bệnh", "Triệu chứng", "Trạng thái", "Nguồn"])
        layout.addWidget(self.vet_table)

    def _refresh_vet(self) -> None:
        records = sorted(self.flock.veterinary_records, key=lambda r: r.diagnosis_date, reverse=True)
        self.vet_table.setRowCount(len(records))
        for row, r in enumerate(records):
            set_row(self.vet_table, row, [
                r.diagnosis_date.isoformat(), r.disease.name if r.disease else "-",
                r.symptoms or "-", VetRecordStatus.LABELS_VI.get(r.status, r.status), r.source,
            ])

    # --- Vaccination --------------------------------------------------
    def _build_vaccination_tab(self) -> None:
        layout = QVBoxLayout(self.vaccination_tab)
        self.vaccination_table = build_table(["Ngày tiêm", "Vắc xin", "Lần sau", "Trạng thái"])
        layout.addWidget(self.vaccination_table)

    def _refresh_vaccination(self) -> None:
        items = sorted(self.flock.vaccinations, key=lambda v: v.vaccination_date, reverse=True)
        self.vaccination_table.setRowCount(len(items))
        for row, v in enumerate(items):
            set_row(self.vaccination_table, row, [
                v.vaccination_date.isoformat(), v.vaccine_name,
                v.next_date.isoformat() if v.next_date else "-", v.status,
            ])

    # --- AI -------------------------------------------------------------
    def _build_ai_tab(self) -> None:
        layout = QVBoxLayout(self.ai_tab)
        layout.addWidget(EmptyState(
            "Chưa có phiên phân tích AI nào liên kết trực tiếp với đàn này.\n"
            "Xem lịch sử đầy đủ tại menu 'Nhận diện AI'."
        ))

    def _refresh_ai(self) -> None:
        pass
