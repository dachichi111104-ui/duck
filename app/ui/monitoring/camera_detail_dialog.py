"""
Enlarged Camera Detail Dialog modal for full view of single camera stream.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

from app.services.camera_service import CameraService, CameraInfo
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon


class CameraDetailDialog(QDialog):
    def __init__(self, camera_code: str, parent=None):
        super().__init__(parent)
        self.camera_code = camera_code
        self.service = CameraService()
        self.cam_info = self.service.get_camera(camera_code)

        self.setWindowTitle(f"Chi tiết Camera — {camera_code}")
        self.resize(860, 580)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header bar
        hdr_layout = QHBoxLayout()
        title_lbl = QLabel(f"<b>{camera_code}</b> • {self.cam_info.name if self.cam_info else ''}")
        title_lbl.setStyleSheet("font-size: 15px; color: #26332A;")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()

        if self.cam_info:
            tone = "success" if self.cam_info.status == "ONLINE" else "danger"
            hdr_layout.addWidget(StatusBadge(self.cam_info.status, tone=tone))

        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)
        hdr_layout.addWidget(close_btn)

        layout.addLayout(hdr_layout)

        # Video Frame (Dark #101512)
        self.video_frame = QFrame()
        self.video_frame.setObjectName("VideoFrame")
        vf_layout = QVBoxLayout(self.video_frame)
        vf_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("Đang mở tín hiệu camera HD...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color: #68736B; font-size: 13px;")
        vf_layout.addWidget(self.video_label)

        layout.addWidget(self.video_frame, 1)

        # Controls & Telemetry Footer
        ftr_layout = QHBoxLayout()
        ftr_layout.addWidget(QLabel(f"RTSP Stream: {self.cam_info.rtsp_url if self.cam_info else ''}"))
        ftr_layout.addStretch()

        snap_btn = QPushButton(" Snapshot")
        snap_btn.setIcon(get_icon("fa5s.camera", color="#2E7D32"))
        snap_btn.setIconSize(QSize(13, 13))
        snap_btn.setObjectName("SecondaryButton")
        ftr_layout.addWidget(snap_btn)

        layout.addLayout(ftr_layout)

    def update_frame(self, q_img: QImage):
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled_pixmap)
