from __future__ import annotations

import datetime as dt

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDateEdit, QSpinBox,
    QTextEdit, QDialogButtonBox, QMessageBox, QLabel,
)
from sqlalchemy import select, func

from app.database.connection import session_scope
from app.database.models import Flock
from app.services.flock_service import FlockService
from app.services.barn_service import BarnService
from app.utils.validators import ValidationError


class FlockFormDialog(QDialog):
    def __init__(self, current_user, flock=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.flock = flock
        self._flock_service = FlockService()
        self._barn_service = BarnService()

        self.setWindowTitle("Sửa đàn" if flock else "Thêm đàn mới")
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.name_input = QLineEdit()
        self.breed_input = QLineEdit()
        self.barn_combo = QComboBox()
        self.barn_combo.addItem("(Chưa gán chuồng)", None)
        for barn in self._barn_service.list_barns():
            self.barn_combo.addItem(f"{barn.name} (còn {barn.available_capacity})", barn.id)

        self.start_date_input = QDateEdit(calendarPopup=True)
        self.start_date_input.setDate(QDate.currentDate())

        self.initial_count_input = QSpinBox()
        self.initial_count_input.setRange(1, 1_000_000)
        self.initial_count_input.setValue(100)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(70)

        form.addRow("Tên đàn *", self.name_input)
        form.addRow("Giống", self.breed_input)
        form.addRow("Chuồng", self.barn_combo)
        form.addRow("Ngày nhập *", self.start_date_input)
        form.addRow("Số lượng ban đầu *", self.initial_count_input)
        form.addRow("Ghi chú", self.notes_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if flock:
            self._code = flock.flock_code
            self.name_input.setText(flock.name)
            self.breed_input.setText(flock.breed or "")
            self.initial_count_input.setValue(flock.initial_count)
            self.initial_count_input.setEnabled(False)
            self.start_date_input.setEnabled(False)
            self.notes_input.setPlainText(flock.notes or "")
            if flock.barn_id:
                idx = self.barn_combo.findData(flock.barn_id)
                if idx >= 0:
                    self.barn_combo.setCurrentIndex(idx)
        else:
            with session_scope() as session:
                max_id = session.execute(select(func.max(Flock.id))).scalar() or 0
            self._code = f"DV{max_id + 1:03d}"

    def _save(self) -> None:
        try:
            if self.flock:
                self._flock_service.update_flock(
                    self.current_user.username, self.flock.id,
                    name=self.name_input.text(), breed=self.breed_input.text(),
                    notes=self.notes_input.toPlainText(),
                )
            else:
                self._flock_service.create_flock(
                    self.current_user.username,
                    flock_code=self._code,
                    name=self.name_input.text(),
                    barn_id=self.barn_combo.currentData(),
                    breed=self.breed_input.text(),
                    start_date=self.start_date_input.date().toPyDate(),
                    initial_count=self.initial_count_input.value(),
                    notes=self.notes_input.toPlainText(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
