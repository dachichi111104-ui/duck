"""
Camera Card / Tile component for Live Monitoring Grid.
Features a light card frame container, dark video area, status badges, and telemetry. No emojis!
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)

from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon


class CameraCard(QFrame):
    """
    Light theme camera tile component.
    Header & container are light (#FFFFFF), video display region is dark (#101512).
    """

    doubleClicked = pyqtSignal(str)  # camera_code
    snapshotRequested = pyqtSignal(str)
    toggleAiRequested = pyqtSignal(str)

    def __init__(self, camera_code: str, title: str, location: str, status: str = "ONLINE", parent=None):
        super().__init__(parent)
        self.camera_code = camera_code
        self.title = title
        self.location = location
        self.status = status

        self.setObjectName("Card")
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # --- Card Header (Light) ----------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)

        self.code_label = QLabel(f"{camera_code} • {title}")
        self.code_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #26332A;")
        self.loc_label = QLabel(location)
        self.loc_label.setStyleSheet("font-size: 9px; color: #68736B;")
        title_col.addWidget(self.code_label)
        title_col.addWidget(self.loc_label)
        header_layout.addLayout(title_col, 1)

        tone = "success" if status == "ONLINE" else ("warning" if status == "CONNECTING" else "danger")
        self.status_badge = StatusBadge(status, tone=tone)
        header_layout.addWidget(self.status_badge)

        layout.addLayout(header_layout)

        # --- Video Preview Area (Dark #101512) ---------------------------
        self.video_frame = QFrame()
        self.video_frame.setObjectName("VideoFrame")
        self.video_frame.setMinimumHeight(115)

        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("Đang tải tín hiệu camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color: #68736B; font-size: 10px; background: transparent;")
        video_layout.addWidget(self.video_label)

        layout.addWidget(self.video_frame, 1)

        # --- Footer Telemetry Bar (Light) --------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(4)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.telemetry_label = QLabel("FPS 24.0 • 1920×1080 • Nhấp đúp để phóng lớn")
        self.telemetry_label.setStyleSheet("font-size: 9px; color: #68736B; font-weight: 600;")
        footer_layout.addWidget(self.telemetry_label, 1)

        action_btn_style = """
            QPushButton#SecondaryButton {
                background-color: #FFFFFF;
                color: #2E7D32;
                border: 1px solid #D8E2DA;
                border-radius: 4px;
                min-height: 0px;
                max-height: 24px;
                min-width: 0px;
                padding: 0;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #E8F3E9;
                border-color: #2E7D32;
            }
        """

        self.ai_btn = QPushButton("AI")
        self.ai_btn.setFixedSize(28, 24)
        self.ai_btn.setStyleSheet(action_btn_style)
        self.ai_btn.setToolTip("Bật/tắt AI overlay")
        self.ai_btn.setObjectName("SecondaryButton")
        self.ai_btn.clicked.connect(lambda: self.toggleAiRequested.emit(self.camera_code))
        footer_layout.addWidget(self.ai_btn)

        self.snap_btn = QPushButton()
        self.snap_btn.setIcon(get_icon("fa5s.camera", color="#2E7D32"))
        self.snap_btn.setIconSize(QSize(12, 12))
        self.snap_btn.setFixedSize(28, 24)
        self.snap_btn.setStyleSheet(action_btn_style)
        self.snap_btn.setToolTip("Chụp ảnh snapshot")
        self.snap_btn.setObjectName("SecondaryButton")
        self.snap_btn.clicked.connect(lambda: self.snapshotRequested.emit(self.camera_code))
        footer_layout.addWidget(self.snap_btn)

        self.enlarge_btn = QPushButton()
        self.enlarge_btn.setIcon(get_icon("fa5s.expand", color="#2E7D32"))
        self.enlarge_btn.setIconSize(QSize(12, 12))
        self.enlarge_btn.setFixedSize(28, 24)
        self.enlarge_btn.setStyleSheet(action_btn_style)
        self.enlarge_btn.setToolTip("Phóng to camera")
        self.enlarge_btn.setObjectName("SecondaryButton")
        self.enlarge_btn.clicked.connect(lambda: self.doubleClicked.emit(self.camera_code))
        footer_layout.addWidget(self.enlarge_btn)

        layout.addLayout(footer_layout)

    def update_frame(self, q_img: QImage):
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled_pixmap)

    def set_status(self, status: str, tone: str = "success"):
        self.status = status
        self.status_badge.set_text_and_tone(status, tone)
        self.telemetry_label.setText(f"FPS 24.0 • 1920×1080 • {status}")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.camera_code)
        super().mouseDoubleClickEvent(event)
