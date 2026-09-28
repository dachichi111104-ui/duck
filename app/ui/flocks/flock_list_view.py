from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton,
    QStackedWidget, QMessageBox, QLabel, QFrame,
)

from app.services.flock_service import FlockService
from app.ui.components.kpi_card import KpiCard
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.flocks.flock_form_dialog import FlockFormDialog
from app.ui.flocks.flock_detail_view import FlockDetailView
from app.utils.validators import ValidationError
from app.config.constants import FlockStatus

COLUMNS = ["Tên đàn", "Chuồng", "SL ban đầu", "SL hiện tại", "Hao hụt", "Tỷ lệ sống", "Ngày nhập", "Trạng thái sức khỏe"]


class FlockListView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = FlockService()
        self._all_flocks = []

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.stack)

        self.list_page = QWidget()
        self._build_list_page()
        self.stack.addWidget(self.list_page)

        self.refresh()

    def _build_list_page(self) -> None:
        layout = QVBoxLayout(self.list_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Top KPI Summary Cards Row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        layout.addLayout(self.kpi_layout)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên đàn...")
        self.search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_input, 2)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Tất cả trạng thái", None)
        for s in (FlockStatus.ACTIVE, FlockStatus.COMPLETED, FlockStatus.CANCELLED):
            self.status_filter.addItem(s, s)
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.status_filter, 1)

        add_btn = QPushButton("Thêm đàn vịt")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_flock)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        self.table.cellDoubleClicked.connect(self._open_detail)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        view_btn = QPushButton("Xem chi tiết")
        view_btn.setObjectName("SecondaryButton")
        view_btn.clicked.connect(self._view_selected_detail)
        actions.addWidget(view_btn)

        edit_btn = QPushButton("Sửa")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        actions.addWidget(edit_btn)

        delete_btn = QPushButton("Xóa")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(delete_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.empty_state = EmptyState("Chưa có dữ liệu đàn vịt", "+ Thêm đàn vịt", self._add_flock)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

    def _update_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_ducks = sum(f.current_count for f in self._all_flocks)
        active_flocks = sum(1 for f in self._all_flocks if f.status == FlockStatus.ACTIVE)
        total_initial = sum(f.initial_count for f in self._all_flocks)
        total_current = sum(f.current_count for f in self._all_flocks)
        avg_survival = round((total_current / total_initial * 100), 1) if total_initial > 0 else 100.0
        watch_count = sum(1 for f in self._all_flocks if f.dead_count > 0)

        self.kpi_layout.addWidget(KpiCard("TOTAL BIRDS", f"{total_ducks:,} con", "fa5s.feather-alt", "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("ACTIVE FLOCKS", f"{active_flocks} đàn", "fa5s.clipboard-list", "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("SURVIVAL RATE", f"{avg_survival}%", "fa5s.chart-line", "#2E7D32" if avg_survival >= 95 else "#F4A62D"))
        self.kpi_layout.addWidget(KpiCard("HEALTH WATCH", f"{watch_count} đàn", "fa5s.user-md", "#D32F2F" if watch_count > 0 else "#2E7D32"))

    def refresh(self) -> None:
        if self.stack.currentIndex() != 0:
            self.stack.setCurrentIndex(0)
        self._all_flocks = self._service.list_flocks()
        self._update_kpi_cards()
        self._apply_filters()

    def _apply_filters(self) -> None:
        text = self.search_input.text().strip().lower()
        status = self.status_filter.currentData()

        filtered = [
            f for f in self._all_flocks
            if (not text or text in f.flock_code.lower() or text in f.name.lower())
            and (not status or f.status == status)
        ]

        self.table.setRowCount(len(filtered))
        for row, f in enumerate(filtered):
            survival = f.survival_rate
            health_badge = "Healthy" if f.dead_count == 0 else "Monitoring"
            set_row(self.table, row, [
                f.name, f.barn.name if f.barn else "-",
                f.initial_count, f.current_count, f.dead_count,
                f"{survival}%", f.start_date.isoformat(), health_badge,
            ], row_data=f.id)

        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_flock_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return get_row_data(self.table, row)

    def _add_flock(self) -> None:
        dlg = FlockFormDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        flock_id = self._selected_flock_id()
        if flock_id is None:
            QMessageBox.information(self, "Sửa đàn", "Vui lòng chọn một đàn.")
            return
        flock = next((f for f in self._all_flocks if f.id == flock_id), None)
        dlg = FlockFormDialog(self.current_user, flock=flock, parent=self)
        if dlg.exec():
            self.refresh()

    def _delete_selected(self) -> None:
        flock_id = self._selected_flock_id()
        if flock_id is None:
            QMessageBox.information(self, "Xóa đàn", "Vui lòng chọn một đàn.")
            return
        confirm = QMessageBox.question(
            self, "Xác nhận xóa", "Bạn có chắc muốn xóa đàn này? Hành động không thể hoàn tác.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self._service.delete_flock(self.current_user.username, flock_id)
                self.refresh()
            except ValidationError as exc:
                QMessageBox.warning(self, "Không thể xóa", str(exc))

    def _view_selected_detail(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self._open_detail(row, 0)
        else:
            QMessageBox.information(self, "Xem chi tiết", "Vui lòng chọn một đàn từ danh sách.")

    def _open_detail(self, row: int, _col: int) -> None:
        flock_id = get_row_data(self.table, row)
        if flock_id is None:
            return
        detail = FlockDetailView(self.current_user, flock_id, on_back=self._back_to_list)
        self.stack.addWidget(detail)
        self.stack.setCurrentWidget(detail)

    def _back_to_list(self) -> None:
        widget = self.stack.currentWidget()
        self.stack.setCurrentIndex(0)
        self.stack.removeWidget(widget)
        widget.deleteLater()
        self.refresh()
