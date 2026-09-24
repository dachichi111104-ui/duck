from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel, QLineEdit,
)

from app.services.user_management_service import UserManagementService
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.icons import get_icon
from app.ui.users.user_form_dialog import UserFormDialog
from app.config.constants import Roles, UserStatus

COLUMNS = ["Tên đăng nhập", "Họ và tên", "Vai trò hệ thống", "Điện thoại", "Email", "Trạng thái tài khoản"]


class UsersView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = UserManagementService()
        self._all_users = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên đăng nhập hoặc họ tên...")
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input, 2)

        add_btn = QPushButton("Thêm người dùng mới")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_user)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        edit_btn = QPushButton("Sửa thông tin")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        actions.addWidget(edit_btn)

        delete_btn = QPushButton("Xóa tài khoản")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(delete_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.empty_state = EmptyState("Chưa có người dùng nào", "+ Thêm người dùng mới", self._add_user)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def refresh(self) -> None:
        self._all_users = self._service.list_users()
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()
        filtered = [
            u for u in self._all_users
            if not text or text in u.username.lower() or text in u.full_name.lower()
        ]

        self.table.setRowCount(len(filtered))
        for row, u in enumerate(filtered):
            st_text = "Hoạt động" if u.status == UserStatus.ACTIVE else "Vô hiệu hóa"
            set_row(self.table, row, [
                u.username, u.full_name,
                Roles.LABELS_VI.get(u.role.name, u.role.name) if u.role else "-",
                u.phone or "-", u.email or "-",
                st_text,
            ], row_data=u.id)

        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        user_id = get_row_data(self.table, row)
        return next((u for u in self._all_users if u.id == user_id), None)

    def _add_user(self) -> None:
        dlg = UserFormDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Sửa người dùng", "Vui lòng chọn một người dùng.")
            return
        dlg = UserFormDialog(self.current_user, user=user, parent=self)
        if dlg.exec():
            self.refresh()

    def _delete_selected(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "Xóa người dùng", "Vui lòng chọn một người dùng.")
            return
        if user.username == self.current_user.username:
            QMessageBox.warning(self, "Không thể xóa", "Không thể xóa chính tài khoản đang đăng nhập.")
            return
        confirm = QMessageBox.question(self, "Xác nhận xóa", f"Xóa người dùng '{user.username}'?")
        if confirm == QMessageBox.StandardButton.Yes:
            self._service.delete_user(self.current_user.username, user.id)
            self.refresh()
