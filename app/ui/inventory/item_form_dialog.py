from __future__ import annotations

import datetime as dt

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit,
    QCheckBox, QDialogButtonBox, QMessageBox, QTextEdit, QLabel,
)
from sqlalchemy import select, func

from app.database.connection import session_scope
from app.database.models import InventoryItem
from app.services.inventory_service import InventoryService
from app.utils.validators import ValidationError


class ItemFormDialog(QDialog):
    def __init__(self, current_user, item=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.item = item
        self._service = InventoryService()

        self.setWindowTitle("Sửa vật tư" if item else "Thêm vật tư mới")
        self.setMinimumWidth(400)

        form = QFormLayout(self)

        self.category_combo = QComboBox()
        for cat in self._service.list_categories():
            self.category_combo.addItem(cat.name, cat.id)

        self.code_label = QLabel()
        self.code_label.setStyleSheet("font-weight: bold; color: #2E7D32;")
        self.name_input = QLineEdit()
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("kg, chai, cái, ...")
        self.min_qty_input = QDoubleSpinBox()
        self.min_qty_input.setRange(0, 1_000_000)
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 1_000_000_000)
        self.price_input.setSuffix(" đ")
        self.supplier_input = QLineEdit()

        self.has_expiry_check = QCheckBox("Có hạn sử dụng")
        self.has_expiry_check.toggled.connect(self._toggle_expiry)
        self.expiry_input = QDateEdit(calendarPopup=True)
        self.expiry_input.setDate(QDate.currentDate().addMonths(6))
        self.expiry_input.setEnabled(False)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)

        form.addRow("Danh mục *", self.category_combo)
        form.addRow("Mã vật tư *", self.code_label)
        form.addRow("Tên vật tư *", self.name_input)
        form.addRow("Đơn vị *", self.unit_input)
        form.addRow("Định mức tối thiểu", self.min_qty_input)
        form.addRow("Đơn giá", self.price_input)
        form.addRow("Nhà cung cấp", self.supplier_input)
        form.addRow(self.has_expiry_check)
        form.addRow("Hạn sử dụng", self.expiry_input)
        form.addRow("Mô tả", self.description_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if item:
            idx = self.category_combo.findData(item.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            self.code_label.setText(item.code)
            self.name_input.setText(item.name)
            self.unit_input.setText(item.unit)
            self.min_qty_input.setValue(item.minimum_quantity)
            self.price_input.setValue(item.unit_price)
            self.supplier_input.setText(item.supplier or "")
            self.description_input.setPlainText(item.description or "")
            if item.expiry_date:
                self.has_expiry_check.setChecked(True)
                self.expiry_input.setDate(QDate(item.expiry_date.year, item.expiry_date.month, item.expiry_date.day))
        else:
            with session_scope() as session:
                max_id = session.execute(select(func.max(InventoryItem.id))).scalar() or 0
            self.code_label.setText(f"VT{max_id + 1:03d}")

    def _toggle_expiry(self, checked: bool) -> None:
        self.expiry_input.setEnabled(checked)

    def _save(self) -> None:
        expiry = self.expiry_input.date().toPyDate() if self.has_expiry_check.isChecked() else None
        try:
            if self.item:
                self._service.update_item(
                    self.current_user.username, self.item.id,
                    name=self.name_input.text(), unit=self.unit_input.text(),
                    minimum_quantity=self.min_qty_input.value(), unit_price=self.price_input.value(),
                    supplier=self.supplier_input.text(), description=self.description_input.toPlainText(),
                    expiry_date=expiry, category_id=self.category_combo.currentData(),
                )
            else:
                self._service.create_item(
                    self.current_user.username,
                    category_id=self.category_combo.currentData(),
                    code=self.code_label.text(), name=self.name_input.text(),
                    unit=self.unit_input.text(), minimum_quantity=self.min_qty_input.value(),
                    unit_price=self.price_input.value(), expiry_date=expiry,
                    supplier=self.supplier_input.text(), description=self.description_input.toPlainText(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
