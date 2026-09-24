from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDateEdit, QLineEdit,
    QDialogButtonBox, QMessageBox,
)

from app.services.flock_service import FlockService
from app.utils.validators import ValidationError


class ProductionRecordDialog(QDialog):
    def __init__(self, current_user, flock_id: int, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.flock_id = flock_id
        self._service = FlockService()

        self.setWindowTitle("Ghi nhận sản lượng")
        self.setMinimumWidth(360)

        form = QFormLayout(self)

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.egg_input = QSpinBox()
        self.egg_input.setRange(0, 100_000)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 20)
        self.weight_input.setSuffix(" kg")
        self.weight_input.setDecimals(2)

        self.feed_input = QDoubleSpinBox()
        self.feed_input.setRange(0, 100_000)
        self.feed_input.setSuffix(" kg")

        self.notes_input = QLineEdit()

        form.addRow("Ngày", self.date_input)
        form.addRow("Sản lượng trứng", self.egg_input)
        form.addRow("Trọng lượng TB", self.weight_input)
        form.addRow("Thức ăn tiêu thụ", self.feed_input)
        form.addRow("Ghi chú", self.notes_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        try:
            self._service.add_production_record(
                self.current_user.username, self.flock_id,
                record_date=self.date_input.date().toPyDate(),
                egg_quantity=self.egg_input.value(),
                average_weight=self.weight_input.value() or None,
                feed_consumption=self.feed_input.value() or None,
                notes=self.notes_input.text(),
            )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
