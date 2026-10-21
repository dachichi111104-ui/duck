from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDateEdit, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox,
)

from app.services.veterinary_service import VeterinaryService
from app.services.flock_service import FlockService
from app.config.constants import VetRecordStatus
from app.utils.validators import ValidationError


class VeterinaryRecordDialog(QDialog):
    def __init__(self, current_user, record=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.record = record
        self._service = VeterinaryService()
        self._flock_service = FlockService()

        self.setWindowTitle("Sửa bệnh án" if record else "Thêm bệnh án mới")
        self.setMinimumWidth(440)

        form = QFormLayout(self)

        self.flock_combo = QComboBox()
        for f in self._flock_service.list_flocks():
            self.flock_combo.addItem(f"{f.flock_code} — {f.name}", f.id)

        self.disease_combo = QComboBox()
        self.disease_combo.addItem("(Chưa xác định)", None)
        for d in self._service.list_diseases():
            self.disease_combo.addItem(d.name, d.id)

        self.animal_ref_input = QLineEdit()
        self.animal_ref_input.setPlaceholderText("Ví dụ: Cá thể #12 (tùy chọn)")

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.symptoms_input = QTextEdit()
        self.symptoms_input.setMaximumHeight(60)
        self.diagnosis_input = QTextEdit()
        self.diagnosis_input.setMaximumHeight(60)
        self.treatment_input = QTextEdit()
        self.treatment_input.setMaximumHeight(60)
        self.medication_input = QLineEdit()
        self.veterinarian_input = QLineEdit()

        self.status_combo = QComboBox()
        for value, label in VetRecordStatus.LABELS_VI.items():
            self.status_combo.addItem(label, value)

        form.addRow("Đàn *", self.flock_combo)
        form.addRow("Bệnh", self.disease_combo)
        form.addRow("Cá thể", self.animal_ref_input)
        form.addRow("Ngày chẩn đoán *", self.date_input)
        form.addRow("Triệu chứng", self.symptoms_input)
        form.addRow("Chẩn đoán", self.diagnosis_input)
        form.addRow("Điều trị", self.treatment_input)
        form.addRow("Thuốc", self.medication_input)
        form.addRow("Bác sĩ thú y *", self.veterinarian_input)
        form.addRow("Trạng thái", self.status_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if record:
            idx = self.flock_combo.findData(record.flock_id)
            if idx >= 0:
                self.flock_combo.setCurrentIndex(idx)
            self.flock_combo.setEnabled(False)
            if record.disease_id:
                idx = self.disease_combo.findData(record.disease_id)
                if idx >= 0:
                    self.disease_combo.setCurrentIndex(idx)
            self.animal_ref_input.setText(record.animal_reference or "")
            self.symptoms_input.setPlainText(record.symptoms or "")
            self.diagnosis_input.setPlainText(record.diagnosis or "")
            self.treatment_input.setPlainText(record.treatment or "")
            self.medication_input.setText(record.medication or "")
            self.veterinarian_input.setText(record.veterinarian or "")
            idx = self.status_combo.findData(record.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

    def _save(self) -> None:
        try:
            if self.record:
                self._service.update_record(
                    self.current_user.username, self.record.id,
                    symptoms=self.symptoms_input.toPlainText(),
                    diagnosis=self.diagnosis_input.toPlainText(),
                    treatment=self.treatment_input.toPlainText(),
                    medication=self.medication_input.text(),
                    veterinarian=self.veterinarian_input.text(),
                    status=self.status_combo.currentData(),
                    disease_id=self.disease_combo.currentData(),
                )
            else:
                self._service.create_record(
                    self.current_user.username,
                    flock_id=self.flock_combo.currentData(),
                    disease_id=self.disease_combo.currentData(),
                    diagnosis_date=self.date_input.date().toPyDate(),
                    symptoms=self.symptoms_input.toPlainText(),
                    diagnosis=self.diagnosis_input.toPlainText(),
                    treatment=self.treatment_input.toPlainText(),
                    medication=self.medication_input.text(),
                    veterinarian=self.veterinarian_input.text(),
                    status=self.status_combo.currentData(),
                    animal_reference=self.animal_ref_input.text(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
