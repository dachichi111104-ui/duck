from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDateEdit, QLineEdit,
    QDialogButtonBox, QMessageBox, QLabel,
)

from app.services.inventory_service import InventoryService
from app.config.constants import InventoryTransactionType
from app.utils.validators import ValidationError

TYPE_LABELS = {
    InventoryTransactionType.IMPORT: "Nhập kho",
    InventoryTransactionType.EXPORT: "Xuất kho",
    InventoryTransactionType.ADJUSTMENT: "Điều chỉnh",
}


class TransactionDialog(QDialog):
    def __init__(self, current_user, item, default_type: str = InventoryTransactionType.IMPORT, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.item = item
        self._service = InventoryService()

        self.setWindowTitle(f"{TYPE_LABELS.get(default_type, 'Giao dịch')} — {item.name}")
        self.setMinimumWidth(360)

        form = QFormLayout(self)

        form.addRow(QLabel(f"Tồn kho hiện tại: <b>{item.quantity} {item.unit}</b>"))

        self.type_combo = QComboBox()
        for value, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, value)
        idx = self.type_combo.findData(default_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.01, 1_000_000)
        self.quantity_input.setSuffix(f" {item.unit}")

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Số phiếu (tùy chọn)")

        self.note_input = QLineEdit()

        form.addRow("Loại giao dịch", self.type_combo)
        form.addRow("Số lượng", self.quantity_input)
        form.addRow("Ngày", self.date_input)
        form.addRow("Tham chiếu", self.reference_input)
        form.addRow("Ghi chú", self.note_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        try:
            self._service.record_transaction(
                self.current_user.username, self.item.id,
                transaction_type=self.type_combo.currentData(),
                quantity=self.quantity_input.value(),
                transaction_date=self.date_input.date().toPyDate(),
                reference=self.reference_input.text(), note=self.note_input.text(),
            )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
