"""
Webcam Direct Capture Dialog for AI Analysis.
Captures live footage from local webcam (OpenCV VideoCapture(0)), saves video to data/videos/,
and passes recorded clip to AI Analysis Pipeline. No emojis!
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
)
import cv2

from app.ui.components.icons import get_icon
from app.config.settings import VIDEOS_DIR


class WebcamRecorderDialog(QDialog):
    video_recorded = pyqtSignal(str)  # Emits recorded video file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quay clip trực tiếp từ Camera / Webcam")
        self.setFixedSize(680, 520)

        self._cap: cv2.VideoCapture | None = None
        self._writer: cv2.VideoWriter | None = None
        self._is_recording = False
        self._recorded_frames = 0
        self._output_path: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Title
        hdr_box = QFrame()
        hdr_box.setObjectName("Card")
        hb_layout = QHBoxLayout(hdr_box)
        hb_layout.setContentsMargins(10, 8, 10, 8)

        lbl_title = QLabel("Quay video từ Camera / Webcam để phân tích AI")
        lbl_title.setObjectName("SectionTitle")
        hb_layout.addWidget(lbl_title)
        hb_layout.addStretch()

        self.status_lbl = QLabel("Đang mở Camera...")
        self.status_lbl.setStyleSheet("color: #1B5E20; font-weight: 700; font-size: 11px;")
        hb_layout.addWidget(self.status_lbl)
        layout.addWidget(hdr_box)

        # Video Preview Feed Frame (Dark #101512)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("VideoFrame")
        pf_layout = QVBoxLayout(self.preview_frame)
        pf_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("Đang kết nối tín hiệu Camera (VideoCapture)...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color: #68736B; font-size: 12px; background: transparent;")
        pf_layout.addWidget(self.video_label)
        layout.addWidget(self.preview_frame, 1)

        # Control Bar Buttons
        ctrl_box = QHBoxLayout()
        ctrl_box.setSpacing(10)

        self.rec_btn = QPushButton("Bắt đầu quay clip (10 giây)")
        self.rec_btn.setIcon(get_icon("fa5s.video", color="#FFFFFF"))
        self.rec_btn.setObjectName("DangerButton")
        self.rec_btn.setFixedHeight(34)
        self.rec_btn.clicked.connect(self._toggle_recording)
        ctrl_box.addWidget(self.rec_btn)

        self.analyze_btn = QPushButton("Sử dụng clip này để Phân tích AI")
        self.analyze_btn.setIcon(get_icon("fa5s.microchip", color="#FFFFFF"))
        self.analyze_btn.setFixedHeight(34)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._finish_and_analyze)
        ctrl_box.addWidget(self.analyze_btn)

        cancel_btn = QPushButton("Đóng")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.close)
        ctrl_box.addWidget(cancel_btn)

        layout.addLayout(ctrl_box)

        # Timer for live frame update
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)

        # Start Camera
        self._start_camera()

    def _start_camera(self) -> None:
        try:
            self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self._cap or not self._cap.isOpened():
                self._cap = cv2.VideoCapture(0)
        except Exception:
            self._cap = None

        if self._cap and self._cap.isOpened():
            self.status_lbl.setText("Camera Sẵn sàng")
            self._timer.start(33)  # ~30 FPS
        else:
            self.status_lbl.setText("Không tìm thấy Webcam (Tạo clip giả lập)")
            self.status_lbl.setStyleSheet("color: #D32F2F; font-weight: 700;")
            self.video_label.setText("Không tìm thấy Webcam trên máy tính này.\n\nNhấn nút bên dưới để tạo clip mẫu từ bộ nhớ.")
            self.rec_btn.setText("Tạo clip mẫu 10s")

    def _update_frame(self) -> None:
        if not self._cap or not self._cap.isOpened():
            return

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return

        if self._is_recording and self._writer:
            self._writer.write(frame)
            self._recorded_frames += 1
            rec_sec = self._recorded_frames // 30
            self.status_lbl.setText(f"Đang quay clip: {rec_sec}s / 10s")

            # Auto-stop after 10s (~300 frames)
            if self._recorded_frames >= 300:
                self._stop_recording()

        # Render on Qt QLabel
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _toggle_recording(self) -> None:
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_path = str(VIDEOS_DIR / f"webcam_recording_{timestamp}.mp4")

        w, h = 640, 480
        if self._cap and self._cap.isOpened():
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(self._output_path, fourcc, 30.0, (w, h))

        self._is_recording = True
        self._recorded_frames = 0
        self.rec_btn.setText("Dừng quay ngay")
        self.status_lbl.setText("Đang quay clip...")
        self.status_lbl.setStyleSheet("color: #D32F2F; font-weight: 700;")

    def _stop_recording(self) -> None:
        self._is_recording = False
        if self._writer:
            self._writer.release()
            self._writer = None

        self.rec_btn.setText("Quay lại clip mới")
        self.status_lbl.setText("Đã lưu clip thành công")
        self.status_lbl.setStyleSheet("color: #1B5E20; font-weight: 700;")
        self.analyze_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Đã ghi clip thành công",
            f"Đã lưu video clip từ camera vào hệ thống tại:\n{self._output_path}\n\nNhấn 'Sử dụng clip này' để đưa vào phân tích AI."
        )

    def _finish_and_analyze(self) -> None:
        if self._output_path:
            self.video_recorded.emit(self._output_path)
            self.accept()

    def closeEvent(self, event):
        self._timer.stop()
        if self._writer:
            self._writer.release()
        if self._cap and self._cap.isOpened():
            self._cap.release()
        super().closeEvent(event)
