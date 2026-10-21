from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDateEdit, QLineEdit, QCheckBox,
    QDoubleSpinBox, QDialogButtonBox, QMessageBox,
)

from app.services.veterinary_service import VeterinaryService
from app.services.flock_service import FlockService
from app.services.inventory_service import InventoryService
from app.services.user_management_service import UserManagementService
from app.config.constants import InventoryTransactionType, Roles
from app.utils.validators import ValidationError
from app.utils.logger import get_logger

logger = get_logger("vaccination_dialog")


class VaccinationDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = VeterinaryService()
        self._flock_service = FlockService()
        self._inventory_service = InventoryService()
        self._user_service = UserManagementService()
        self.vets_list = self._user_service.list_veterinarians()

        self.setWindowTitle("Ghi nhận tiêm phòng")
        self.setMinimumWidth(420)

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

        # Veterinarian assignment / selection
        self.veterinarian_combo = QComboBox()
        self.veterinarian_combo.setEditable(False)
        for v in self.vets_list:
            display_name = f"{v.full_name} ({v.username})" if v.full_name != v.username else v.full_name
            self.veterinarian_combo.addItem(display_name, v.full_name)

        if self.current_user.role_name == Roles.VETERINARIAN:
            self.set_veterinarian(self.current_user.full_name or self.current_user.username)
        elif self.vets_list:
            self.veterinarian_combo.setCurrentIndex(0)

        # Inventory integration fields (Requirement 7)
        self.inventory_combo = QComboBox()
        self.inventory_combo.addItem("(Không trừ kho / Chọn sau)", None)
        self._items_map = {}
        for item in self._inventory_service.list_items():
            self.inventory_combo.addItem(f"{item.code} — {item.name} (Tồn: {item.quantity} {item.unit})", item.id)
            self._items_map[item.id] = item

        self.qty_used_input = QDoubleSpinBox()
        self.qty_used_input.setRange(0.0, 10000.0)
        self.qty_used_input.setValue(1.0)
        self.qty_used_input.setSingleStep(1.0)

        form.addRow("Đàn *", self.flock_combo)
        form.addRow("Tên vắc xin *", self.vaccine_input)
        form.addRow("Ngày tiêm *", self.date_input)
        form.addRow(self.has_next_check)
        form.addRow("Ngày tiêm tiếp theo", self.next_date_input)
        form.addRow("Liều lượng", self.dosage_input)

        if self.current_user.role_name in (Roles.ADMIN, Roles.FARM_MANAGER):
            form.addRow("Phân công Bác sĩ thực hiện", self.veterinarian_combo)
        else:
            form.addRow("Bác sĩ / Cán bộ thực hiện", self.veterinarian_combo)

        form.addRow("Vật tư vắc-xin kho", self.inventory_combo)
        form.addRow("Số lượng vắc-xin sử dụng", self.qty_used_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def set_veterinarian(self, vet_name: str) -> None:
        """Helper to programmatically select or set veterinarian."""
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
        inv_item_id = self.inventory_combo.currentData()
        qty_used = self.qty_used_input.value()
        exceeds_stock = False

        if inv_item_id and qty_used > 0:
            item = self._items_map.get(inv_item_id)
            if item and qty_used > item.quantity:
                exceeds_stock = True
                res = QMessageBox.warning(
                    self,
                    "Cảnh báo tồn kho không đủ",
                    f"Số lượng vắc-xin xuất kho ({qty_used} {item.unit}) lớn hơn tồn kho hiện tại ({item.quantity} {item.unit}).\n\n"
                    "Bạn có chắc chắn muốn tiếp tục xuất kho vắc-xin này?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if res != QMessageBox.StandardButton.Yes:
                    return

        try:
            vet_val = self.veterinarian_combo.currentData()
            if not vet_val:
                vet_val = self.veterinarian_combo.currentText().strip()

            # 1. Schedule vaccination record
            vac = self._service.schedule_vaccination(
                self.current_user.username,
                flock_id=self.flock_combo.currentData(),
                vaccine_name=self.vaccine_input.text(),
                vaccination_date=self.date_input.date().toPyDate(),
                next_date=self.next_date_input.date().toPyDate() if self.has_next_check.isChecked() else None,
                dosage=self.dosage_input.text(),
                veterinarian=vet_val,
            )

            # 2. Automatically record inventory EXPORT transaction (Requirement 7)
            if inv_item_id and qty_used > 0:
                note_str = f"Xuất kho vắc-xin cho lịch tiêm #{vac.id}"
                if exceeds_stock:
                    note_str += " (vượt tồn kho)"
                    logger.warning("Vaccination #%s inventory export exceeds stock for item #%s", vac.id, inv_item_id)

                self._inventory_service.record_transaction(
                    self.current_user.username,
                    item_id=inv_item_id,
                    transaction_type=InventoryTransactionType.EXPORT,
                    quantity=qty_used,
                    transaction_date=self.date_input.date().toPyDate(),
                    reference=f"VAC-{vac.id:04d}",
                    note=note_str,
                )

            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
