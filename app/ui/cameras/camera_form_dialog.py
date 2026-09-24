"""
Form dialog to add or edit a surveillance camera configuration.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox,
)

from app.services.camera_service import CameraService, CameraInfo


class CameraFormDialog(QDialog):
    def __init__(self, camera: CameraInfo | None = None, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.service = CameraService()

        self.setWindowTitle("Sửa thông tin Camera" if camera else "Thêm Camera mới")
        self.setFixedWidth(450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(12)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("VD: CAM-09")
        form.addRow("Mã Camera *:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("VD: Khu Ao Bơi 02")
        form.addRow("Tên Camera *:", self.name_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("VD: Chuồng 02 / Khu B")
        form.addRow("Vị trí / Khu vực:", self.location_input)

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://192.168.1.109/stream1")
        form.addRow("RTSP Stream URL:", self.rtsp_input)

        self.res_combo = QComboBox()
        self.res_combo.addItems(["1920x1080", "1280x720", "2560x1440", "3840x2160"])
        form.addRow("Độ phân giải:", self.res_combo)

        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60", "15"])
        form.addRow("Khung hình (FPS):", self.fps_combo)

        self.ai_checkbox = QCheckBox("Bật nhận diện AI cho camera này")
        self.ai_checkbox.setChecked(True)
        form.addRow("Tích hợp AI:", self.ai_checkbox)

        layout.addLayout(form)

        if camera:
            self.code_input.setText(camera.code)
            self.code_input.setEnabled(False)
            self.name_input.setText(camera.name)
            self.location_input.setText(camera.location)
            self.rtsp_input.setText(camera.rtsp_url)
            self.ai_checkbox.setChecked(camera.ai_enabled)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Lưu thông tin")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _save(self):
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()

        if not code or not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Mã và Tên Camera.")
            return

        if not self.camera:
            new_cam = CameraInfo(
                code=code,
                name=name,
                location=self.location_input.text().strip() or "Khu vực chung",
                status="ONLINE",
                fps=int(self.fps_combo.currentText()),
                resolution=self.res_combo.currentText(),
                rtsp_url=self.rtsp_input.text().strip() or f"rtsp://192.168.1.100/{code}",
                ai_enabled=self.ai_checkbox.isChecked(),
            )
            self.service.cameras.append(new_cam)
        else:
            self.camera.name = name
            self.camera.location = self.location_input.text().strip()
            self.camera.rtsp_url = self.rtsp_input.text().strip()
            self.camera.resolution = self.res_combo.currentText()
            self.camera.fps = int(self.fps_combo.currentText())
            self.camera.ai_enabled = self.ai_checkbox.isChecked()

        self.accept()
