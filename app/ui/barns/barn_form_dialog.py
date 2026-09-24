from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QTextEdit, QDialogButtonBox, QMessageBox,
)

from app.services.barn_service import BarnService
from app.utils.validators import ValidationError


class BarnFormDialog(QDialog):
    def __init__(self, current_user, barn=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.barn = barn
        self._service = BarnService()

        self.setWindowTitle("Sửa chuồng" if barn else "Thêm chuồng mới")
        self.setMinimumWidth(380)

        form = QFormLayout(self)

        self.code_input = QLineEdit()
        self.name_input = QLineEdit()
        self.location_input = QLineEdit()
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(1, 1_000_000)
        self.capacity_input.setValue(100)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(70)

        form.addRow("Mã chuồng *", self.code_input)
        form.addRow("Tên chuồng *", self.name_input)
        form.addRow("Vị trí", self.location_input)
        form.addRow("Sức chứa *", self.capacity_input)
        form.addRow("Mô tả", self.description_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if barn:
            self.code_input.setText(barn.code)
            self.code_input.setEnabled(False)
            self.name_input.setText(barn.name)
            self.location_input.setText(barn.location or "")
            self.capacity_input.setValue(barn.capacity)
            self.description_input.setPlainText(barn.description or "")

    def _save(self) -> None:
        try:
            if self.barn:
                self._service.update_barn(
                    self.current_user.username, self.barn.id,
                    name=self.name_input.text(), location=self.location_input.text(),
                    capacity=self.capacity_input.value(),
                    description=self.description_input.toPlainText(),
                )
            else:
                self._service.create_barn(
                    self.current_user.username,
                    code=self.code_input.text(), name=self.name_input.text(),
                    location=self.location_input.text(), capacity=self.capacity_input.value(),
                    description=self.description_input.toPlainText(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
