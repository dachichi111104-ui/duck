from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDateEdit, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox,
)

from app.services.veterinary_service import VeterinaryService
from app.services.flock_service import FlockService
from app.services.user_management_service import UserManagementService
from app.config.constants import VetRecordStatus, Roles
from app.utils.validators import ValidationError


class VeterinaryRecordDialog(QDialog):
    def __init__(self, current_user, record=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.record = record
        self._service = VeterinaryService()
        self._flock_service = FlockService()
        self._user_service = UserManagementService()
        self.vets_list = self._user_service.list_veterinarians()

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

        # Veterinarian selection / assignment
        self.veterinarian_combo = QComboBox()
        self.veterinarian_combo.setEditable(False)
        for v in self.vets_list:
            display_name = f"{v.full_name} ({v.username})" if v.full_name != v.username else v.full_name
            self.veterinarian_combo.addItem(display_name, v.full_name)

        self.status_combo = QComboBox()
        for value, label in VetRecordStatus.CANONICAL_CHOICES:
            self.status_combo.addItem(label, value)

        form.addRow("Đàn *", self.flock_combo)
        form.addRow("Bệnh", self.disease_combo)
        form.addRow("Cá thể", self.animal_ref_input)
        form.addRow("Ngày chẩn đoán *", self.date_input)
        form.addRow("Triệu chứng", self.symptoms_input)
        form.addRow("Chẩn đoán", self.diagnosis_input)
        form.addRow("Điều trị", self.treatment_input)
        form.addRow("Thuốc", self.medication_input)

        if self.current_user.role_name in (Roles.ADMIN, Roles.FARM_MANAGER):
            form.addRow("Phân công Bác sĩ phụ trách *", self.veterinarian_combo)
        else:
            form.addRow("Bác sĩ phụ trách *", self.veterinarian_combo)

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
            if record.veterinarian:
                idx = -1
                for i in range(self.veterinarian_combo.count()):
                    if self.veterinarian_combo.itemData(i) == record.veterinarian or self.veterinarian_combo.itemText(i) == record.veterinarian:
                        idx = i
                        break
                if idx >= 0:
                    self.veterinarian_combo.setCurrentIndex(idx)
                else:
                    self.veterinarian_combo.addItem(record.veterinarian, record.veterinarian)
                    self.veterinarian_combo.setCurrentText(record.veterinarian)
            idx = self.status_combo.findData(record.status)
            if idx < 0:
                s_up = str(record.status or "").upper()
                if s_up in ("THEO_DOI", "MONITORING", "UNDER_MONITORING"):
                    idx = self.status_combo.findData(VetRecordStatus.THEO_DOI)
                elif s_up in ("DANG_DIEU_TRI", "TREATING", "ACTIVE_TREATMENT"):
                    idx = self.status_combo.findData(VetRecordStatus.DANG_DIEU_TRI)
                elif s_up in ("DA_KHOI", "RECOVERED", "HEALED"):
                    idx = self.status_combo.findData(VetRecordStatus.DA_KHOI)
                elif s_up in ("CAN_TAI_KHAM", "CULLED", "REEXAMINE"):
                    idx = self.status_combo.findData(VetRecordStatus.CAN_TAI_KHAM)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
        else:
            if self.current_user.role_name == Roles.VETERINARIAN:
                self.set_veterinarian(self.current_user.full_name or self.current_user.username)
            elif self.vets_list:
                self.veterinarian_combo.setCurrentIndex(0)

    def set_veterinarian(self, vet_name: str) -> None:
        """Helper to programmatically select or set attending veterinarian."""
        if not vet_name:
            return
        target = str(vet_name).strip().lower()
        idx = -1
        for i in range(self.veterinarian_combo.count()):
            val = str(self.veterinarian_combo.itemData(i) or "").strip().lower()
            txt = self.veterinarian_combo.itemText(i).strip().lower()
            if target == val or target == txt or target in txt:
                idx = i
                break
        if idx >= 0:
            self.veterinarian_combo.setCurrentIndex(idx)
        else:
            self.veterinarian_combo.addItem(vet_name, vet_name)
            self.veterinarian_combo.setCurrentIndex(self.veterinarian_combo.count() - 1)

    @property
    def veterinarian_input(self):
        """Backward-compatibility adapter for callers expecting a QLineEdit-like interface."""
        class _VetInputWrapper:
            def __init__(self, dialog):
                self._dialog = dialog
            def setText(self, text):
                self._dialog.set_veterinarian(text)
            def text(self):
                return self._dialog.veterinarian_combo.currentData() or self._dialog.veterinarian_combo.currentText().strip()
        return _VetInputWrapper(self)

    def _save(self) -> None:
        try:
            vet_val = self.veterinarian_combo.currentData()
            if not vet_val:
                vet_val = self.veterinarian_combo.currentText().strip()

            if self.record:
                self._service.update_record(
                    self.current_user.username, self.record.id,
                    symptoms=self.symptoms_input.toPlainText(),
                    diagnosis=self.diagnosis_input.toPlainText(),
                    treatment=self.treatment_input.toPlainText(),
                    medication=self.medication_input.text(),
                    veterinarian=vet_val,
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
                    veterinarian=vet_val,
                    status=self.status_combo.currentData(),
                    animal_reference=self.animal_ref_input.text(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
