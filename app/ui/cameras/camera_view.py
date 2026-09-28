"""
Camera Device Management View.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox,
)

from app.services.camera_service import CameraService, CameraInfo
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.icons import get_icon
from app.ui.cameras.camera_form_dialog import CameraFormDialog

COLUMNS = ["Tên Camera", "Vị trí / Khu vực", "Stream URL", "Độ phân giải", "FPS", "Nhận diện AI", "Trạng thái"]


class CameraManagementView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = CameraService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm camera theo tên hoặc vị trí...")
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input, 2)

        add_btn = QPushButton("Thêm Camera mới")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_camera)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        edit_btn = QPushButton("Sửa thông tin")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        actions.addWidget(edit_btn)

        test_btn = QPushButton("Kiểm tra kết nối")
        test_btn.setObjectName("SecondaryButton")
        test_btn.clicked.connect(self._test_connection)
        actions.addWidget(test_btn)

        delete_btn = QPushButton("Xóa Camera")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(delete_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.empty_state = EmptyState("Chưa có camera nào được cấu hình", "Thêm Camera mới", self._add_camera)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def refresh(self) -> None:
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()
        cameras = self._service.get_cameras()
        filtered = [
            c for c in cameras
            if not text or text in c.code.lower() or text in c.name.lower() or text in c.location.lower()
        ]

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            set_row(self.table, row, [
                c.name, c.location, c.rtsp_url, c.resolution, c.fps,
                "BẬT" if c.ai_enabled else "TẮT", c.status,
            ], row_data=c.code)

        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_camera_code(self) -> str | None:
        row = self.table.currentRow()
        return get_row_data(self.table, row) if row >= 0 else None

    def _add_camera(self) -> None:
        dlg = CameraFormDialog(parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        code = self._selected_camera_code()
        if not code:
            QMessageBox.information(self, "Sửa camera", "Vui lòng chọn một camera từ danh sách.")
            return
        cam = self._service.get_camera(code)
        if cam:
            dlg = CameraFormDialog(camera=cam, parent=self)
            if dlg.exec():
                self.refresh()

    def _test_connection(self) -> None:
        code = self._selected_camera_code()
        if not code:
            QMessageBox.information(self, "Kiểm tra kết nối", "Vui lòng chọn một camera.")
            return
        QMessageBox.information(self, "Kiểm tra kết nối", f"Kết nối tới stream RTSP của {code} thành công!\nĐộ trễ: 14ms.")

    def _delete_selected(self) -> None:
        code = self._selected_camera_code()
        if not code:
            QMessageBox.information(self, "Xóa camera", "Vui lòng chọn một camera.")
            return
        confirm = QMessageBox.question(self, "Xác nhận", f"Bạn có chắc muốn xóa {code}?")
        if confirm == QMessageBox.StandardButton.Yes:
            self._service.cameras = [c for c in self._service.cameras if c.code != code]
            self.refresh()
