from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QSpinBox, QDateEdit, QLineEdit,
    QDialogButtonBox, QMessageBox,
)

from app.config.constants import FlockEventType
from app.services.flock_service import FlockService
from app.utils.validators import ValidationError


class FlockEventDialog(QDialog):
    def __init__(self, current_user, flock_id: int, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.flock_id = flock_id
        self._service = FlockService()

        self.setWindowTitle("Ghi nhận biến động đàn")
        self.setMinimumWidth(380)

        form = QFormLayout(self)

        self.type_combo = QComboBox()
        for value, label in FlockEventType.LABELS_VI.items():
            self.type_combo.addItem(label, value)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 1_000_000)

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.reason_input = QLineEdit()

        form.addRow("Loại biến động", self.type_combo)
        form.addRow("Số lượng", self.quantity_input)
        form.addRow("Ngày", self.date_input)
        form.addRow("Lý do / ghi chú", self.reason_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        try:
            self._service.record_event(
                self.current_user.username, self.flock_id,
                event_type=self.type_combo.currentData(),
                quantity=self.quantity_input.value(),
                event_date=self.date_input.date().toPyDate(),
                reason=self.reason_input.text(),
            )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
