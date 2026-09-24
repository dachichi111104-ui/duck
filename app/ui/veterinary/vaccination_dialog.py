from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDateEdit, QLineEdit, QCheckBox,
    QDialogButtonBox, QMessageBox,
)

from app.services.veterinary_service import VeterinaryService
from app.services.flock_service import FlockService
from app.utils.validators import ValidationError


class VaccinationDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = VeterinaryService()
        self._flock_service = FlockService()

        self.setWindowTitle("Ghi nhận tiêm phòng")
        self.setMinimumWidth(400)

        form = QFormLayout(self)

        self.flock_combo = QComboBox()
        for f in self._flock_service.list_flocks():
            self.flock_combo.addItem(f"{f.flock_code} — {f.name}", f.id)

        self.vaccine_input = QLineEdit()
        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.has_next_check = QCheckBox("Có lịch tiêm tiếp theo")
        self.has_next_check.toggled.connect(lambda checked: self.next_date_input.setEnabled(checked))
        self.next_date_input = QDateEdit(calendarPopup=True)
        self.next_date_input.setDate(QDate.currentDate().addDays(30))
        self.next_date_input.setEnabled(False)

        self.dosage_input = QLineEdit()
        self.dosage_input.setPlaceholderText("Ví dụ: 1ml/con")
        self.veterinarian_input = QLineEdit()

        form.addRow("Đàn *", self.flock_combo)
        form.addRow("Tên vắc xin *", self.vaccine_input)
        form.addRow("Ngày tiêm *", self.date_input)
        form.addRow(self.has_next_check)
        form.addRow("Ngày tiêm tiếp theo", self.next_date_input)
        form.addRow("Liều lượng", self.dosage_input)
        form.addRow("Bác sĩ thú y", self.veterinarian_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        try:
            self._service.schedule_vaccination(
                self.current_user.username,
                flock_id=self.flock_combo.currentData(),
                vaccine_name=self.vaccine_input.text(),
                vaccination_date=self.date_input.date().toPyDate(),
                next_date=self.next_date_input.date().toPyDate() if self.has_next_check.isChecked() else None,
                dosage=self.dosage_input.text(),
                veterinarian=self.veterinarian_input.text(),
            )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
