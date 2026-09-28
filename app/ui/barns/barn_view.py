from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox

from app.services.barn_service import BarnService
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.icons import get_icon
from app.ui.barns.barn_form_dialog import BarnFormDialog
from app.utils.validators import ValidationError

COLUMNS = ["Tên chuồng", "Vị trí", "Sức chứa", "Hiện tại", "Trạng thái"]


class BarnView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = BarnService()
        self._all_barns = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên chuồng hoặc vị trí...")
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input, 2)

        add_btn = QPushButton("Thêm chuồng")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_barn)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
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

        self.empty_state = EmptyState("Chưa có dữ liệu chuồng", "Thêm chuồng", self._add_barn)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def refresh(self) -> None:
        self._all_barns = self._service.list_barns()
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()
        filtered = [
            b for b in self._all_barns
            if not text or text in b.code.lower() or text in b.name.lower()
        ]
        self.table.setRowCount(len(filtered))
        for row, b in enumerate(filtered):
            set_row(self.table, row, [
                b.name, b.location or "-", b.capacity, b.current_count, b.status,
            ], row_data=b.id)
        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_barn_id(self):
        row = self.table.currentRow()
        return get_row_data(self.table, row) if row >= 0 else None

    def _add_barn(self) -> None:
        dlg = BarnFormDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        barn_id = self._selected_barn_id()
        if barn_id is None:
            QMessageBox.information(self, "Sửa chuồng", "Vui lòng chọn một chuồng.")
            return
        barn = next((b for b in self._all_barns if b.id == barn_id), None)
        dlg = BarnFormDialog(self.current_user, barn=barn, parent=self)
        if dlg.exec():
            self.refresh()

    def _delete_selected(self) -> None:
        barn_id = self._selected_barn_id()
        if barn_id is None:
            QMessageBox.information(self, "Xóa chuồng", "Vui lòng chọn một chuồng.")
            return
        confirm = QMessageBox.question(self, "Xác nhận xóa", "Bạn có chắc muốn xóa chuồng này?")
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self._service.delete_barn(self.current_user.username, barn_id)
                self.refresh()
            except ValidationError as exc:
                QMessageBox.warning(self, "Không thể xóa", str(exc))
