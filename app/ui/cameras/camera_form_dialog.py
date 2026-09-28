"""
Form dialog to add or edit a surveillance camera configuration.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QLabel, QFileDialog,
)
from sqlalchemy import select, func

from app.database.connection import session_scope
from app.database.models import Camera
from app.services.camera_service import CameraService


class CameraFormDialog(QDialog):
    def __init__(self, camera: Camera | None = None, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.service = CameraService()

        self.setWindowTitle("Sửa thông tin Camera" if camera else "Thêm Camera mới")
        self.setFixedWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("VD: Khu Ao Bơi 02")
        form.addRow("Tên Camera *:", self.name_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("VD: Chuồng 02 / Khu B")
        form.addRow("Vị trí / Khu vực:", self.location_input)

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://192.168.1.109/stream1")
        form.addRow("RTSP Stream URL:", self.rtsp_input)

        # Video File for simulation source
        video_box = QHBoxLayout()
        self.video_path_input = QLineEdit()
        self.video_path_input.setPlaceholderText("Tệp video mp4/avi mô phỏng (tùy chọn)")
        browse_btn = QPushButton("Chọn...")
        browse_btn.setFixedWidth(60)
        browse_btn.clicked.connect(self._browse_video)
        video_box.addWidget(self.video_path_input)
        video_box.addWidget(browse_btn)
        form.addRow("Tệp video mô phỏng:", video_box)

        self.res_combo = QComboBox()
        self.res_combo.addItems(["1920x1080", "1280x720", "2560x1440", "3840x2160"])
        form.addRow("Độ phân giải:", self.res_combo)

        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30", "24", "60", "15"])
        form.addRow("Khung hình (FPS):", self.fps_combo)

        self.ai_checkbox = QCheckBox("Bật nhận diện AI cho camera này")
        self.ai_checkbox.setChecked(True)
        form.addRow("Tích hợp AI:", self.ai_checkbox)

        layout.addLayout(form)

        if camera:
            self._code = camera.code
            self.name_input.setText(camera.name)
            self.location_input.setText(camera.location or "")
            self.rtsp_input.setText(camera.rtsp_url or "")
            self.video_path_input.setText(camera.video_file_path or "")
            self.ai_checkbox.setChecked(camera.ai_enabled)
            idx_res = self.res_combo.findText(camera.resolution or "1920x1080")
            if idx_res >= 0:
                self.res_combo.setCurrentIndex(idx_res)
            idx_fps = self.fps_combo.findText(str(camera.fps or 30))
            if idx_fps >= 0:
                self.fps_combo.setCurrentIndex(idx_fps)
        else:
            with session_scope() as session:
                max_id = session.execute(select(func.max(Camera.id))).scalar() or 0
            self._code = f"CAM{max_id + 1:02d}"

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

    def _browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn tệp video mô phỏng", "", "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        if file_path:
            self.video_path_input.setText(file_path)

    def _save(self):
        code = self._code
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Tên Camera.")
            return

        if not self.camera:
            self.service.create_camera(
                code=code,
                name=name,
                location=self.location_input.text().strip() or "Khu vực chung",
                rtsp_url=self.rtsp_input.text().strip() or f"rtsp://192.168.1.100/{code}",
                video_file_path=self.video_path_input.text().strip() or None,
                resolution=self.res_combo.currentText(),
                fps=int(self.fps_combo.currentText()),
                ai_enabled=self.ai_checkbox.isChecked(),
            )
        else:
            self.service.update_camera(
                self.camera.id,
                name=name,
                location=self.location_input.text().strip(),
                rtsp_url=self.rtsp_input.text().strip(),
                video_file_path=self.video_path_input.text().strip() or None,
                resolution=self.res_combo.currentText(),
                fps=int(self.fps_combo.currentText()),
                ai_enabled=self.ai_checkbox.isChecked(),
            )

        self.accept()
