from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox,
)

from app.services.user_management_service import UserManagementService
from app.config.constants import UserStatus, Roles
from app.utils.validators import ValidationError


class UserFormDialog(QDialog):
    def __init__(self, current_user, user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.user = user
        self._service = UserManagementService()

        self.setWindowTitle("Sửa người dùng" if user else "Thêm người dùng mới")
        self.setMinimumWidth(380)

        form = QFormLayout(self)

        self.username_input = QLineEdit()
        self.full_name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        self.role_combo = QComboBox()
        for role in self._service.list_roles():
            self.role_combo.addItem(Roles.LABELS_VI.get(role.name, role.name), role.id)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Hoạt động", UserStatus.ACTIVE)
        self.status_combo.addItem("Vô hiệu hóa", UserStatus.INACTIVE)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(
            "Để trống nếu không đổi mật khẩu" if user else "Mật khẩu ban đầu"
        )

        form.addRow("Tên đăng nhập *", self.username_input)
        form.addRow("Họ tên *", self.full_name_input)
        form.addRow("Điện thoại", self.phone_input)
        form.addRow("Email", self.email_input)
        form.addRow("Vai trò *", self.role_combo)
        if user:
            form.addRow("Trạng thái", self.status_combo)
        form.addRow("Mật khẩu" + (" *" if not user else ""), self.password_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if user:
            self.username_input.setText(user.username)
            self.username_input.setEnabled(False)
            self.full_name_input.setText(user.full_name)
            self.phone_input.setText(user.phone or "")
            self.email_input.setText(user.email or "")
            idx = self.role_combo.findData(user.role_id)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
            idx = self.status_combo.findData(user.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

    def _save(self) -> None:
        try:
            if self.user:
                fields = dict(
                    full_name=self.full_name_input.text(), phone=self.phone_input.text(),
                    email=self.email_input.text(), role_id=self.role_combo.currentData(),
                    status=self.status_combo.currentData(),
                )
                if self.password_input.text():
                    fields["new_password"] = self.password_input.text()
                self._service.update_user(self.current_user.username, self.user.id, **fields)
            else:
                self._service.create_user(
                    self.current_user.username,
                    username=self.username_input.text(), password=self.password_input.text(),
                    full_name=self.full_name_input.text(), role_id=self.role_combo.currentData(),
                    phone=self.phone_input.text(), email=self.email_input.text(),
                )
            self.accept()
        except ValidationError as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))
