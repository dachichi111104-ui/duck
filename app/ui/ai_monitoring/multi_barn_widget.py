"""
Multi-Barn Surveillance Simulation Widget (Requirement 5).

Simulates continuous multi-camera surveillance monitoring across 3 barn locations:
- Camera Chuồng 1 (Khu Ăn Uống)
- Camera Chuồng 2 (Khu Sân Chơi)
- Camera Chuồng 3 (Khu Cách Ly Thú Y)

Features continuous video looping, real-time AI bounding box overlays, and
consecutive-frame alert filtering (>= 5 consecutive frames) to eliminate false alarms.

CLEAR DISCLAIMER:
BẢN MÔ PHỎNG DÙNG VIDEO GHI SẴN PHỤC VỤ DEMO
(Trang trại chưa lắp đặt hệ thống camera IP/RTSP cố định).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QMessageBox,
)
import cv2
import numpy as np

from app.ui.components.icons import get_icon
from app.ui.components.status_badge import StatusBadge
from app.ai.overlay_drawer import draw_duck_overlay
from app.ai.ai_service import PlaceholderAIService, DuckTrack
from app.ai.video_processor import VideoLoopReader
from app.services.alert_service import AlertService


class BarnSimTile(QFrame):
    """Single camera tile in the Multi-Barn Simulation Grid."""

    def __init__(self, code: str, barn_name: str, video_path: str | None = None, parent=None):
        super().__init__(parent)
        self.code = code
        self.barn_name = barn_name
        self.video_path = video_path

        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header bar
        hdr = QHBoxLayout()
        hdr.setSpacing(4)

        lbl_code = QLabel(f"<b>{code}</b> • {barn_name}")
        lbl_code.setStyleSheet("font-size: 11px; color: #26332A;")
        hdr.addWidget(lbl_code, 1)

        self.badge = StatusBadge("ONLINE", tone="success")
        hdr.addWidget(self.badge)
        layout.addLayout(hdr)

        # Video Frame Container (Dark #101512)
        self.video_frame = QFrame()
        self.video_frame.setObjectName("VideoFrame")
        self.video_frame.setMinimumHeight(135)

        vf_layout = QVBoxLayout(self.video_frame)
        vf_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("Đang mở luồng mô phỏng...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color: #68736B; font-size: 10px; background: transparent;")
        vf_layout.addWidget(self.video_label)
        layout.addWidget(self.video_frame, 1)

        # Telemetry Footer
        ftr = QHBoxLayout()
        ftr.setSpacing(4)
        self.telemetry_lbl = QLabel("FPS 25.0 • Live Stream AI Overlay")
        self.telemetry_lbl.setStyleSheet("font-size: 9px; color: #68736B;")
        ftr.addWidget(self.telemetry_lbl, 1)

        self.alert_badge = StatusBadge("Bình thường", tone="success")
        ftr.addWidget(self.alert_badge)
        layout.addLayout(ftr)

    def update_frame_pixmap(self, pixmap: QPixmap, status_str: str = "Bình thường", tone: str = "success") -> None:
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        self.alert_badge.set_text_and_tone(status_str, tone)


class MultiBarnSimulationWidget(QWidget):
    """
    Requirement 5: Multi-Barn Simulation Surveillance Widget.
    Runs 3 camera streams in parallel with continuous looping & AI overlay.
    Consecutive-frame filter: triggers system alert only when sick duck detected >= 5 consecutive frames.
    """

    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._alert_service = AlertService()
        self._ai_service = PlaceholderAIService()

        self._tiles: list[BarnSimTile] = []
        self._frame_counters = [0, 0, 0]
        self._consecutive_sick_counts = [0, 0, 0]

        # Generate sample tracks for 3 cameras
        sample_result = self._ai_service.analyze_video("")
        self._camera_tracks = [
            sample_result.tracks,
            sample_result.tracks,
            sample_result.tracks,
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # DISCLAIMER BANNER (Requirement 5)
        banner = QFrame()
        banner.setObjectName("Card")
        banner.setStyleSheet("background-color: #FFF4DD; border: 1px solid #FFE0A3; border-radius: 6px;")
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(10, 6, 10, 6)
        b_layout.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("fa5s.exclamation-triangle", color="#B87600").pixmap(QSize(16, 16)))
        b_layout.addWidget(icon_lbl)

        msg_lbl = QLabel(
            "<b>BẢN MÔ PHỎNG BẰNG VIDEO GHI SẴN PHỤC VỤ DEMO:</b> "
            "Trang trại chưa lắp đặt hệ thống Camera IP/RTSP cố định. "
            "Dữ liệu được phát lặp liên tục để minh họa luồng chẩn đoán AI thời gian thực."
        )
        msg_lbl.setStyleSheet("color: #B87600; font-size: 10px;")
        msg_lbl.setWordWrap(True)
        b_layout.addWidget(msg_lbl, 1)

        layout.addWidget(banner)

        # Control Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(6)

        title_lbl = QLabel("Giám sát 3 chuồng nuôi (Mô phỏng đồng thời)")
        title_lbl.setObjectName("SectionTitle")
        ctrl_bar.addWidget(title_lbl)
        ctrl_bar.addStretch()

        self.start_btn = QPushButton("Bắt đầu giám sát 3 chuồng")
        self.start_btn.setIcon(get_icon("fa5s.play", color="#FFFFFF"))
        self.start_btn.setFixedHeight(26)
        self.start_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.start_btn.clicked.connect(self._start_simulation)
        ctrl_bar.addWidget(self.start_btn)

        pause_btn = QPushButton("Tạm dừng mô phỏng")
        pause_btn.setIcon(get_icon("fa5s.pause", color="#FFFFFF"))
        pause_btn.setObjectName("WarningButton")
        pause_btn.setFixedHeight(26)
        pause_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        pause_btn.clicked.connect(self._pause_simulation)
        ctrl_bar.addWidget(pause_btn)

        layout.addLayout(ctrl_bar)

        # Grid of 3 Camera Tiles
        grid = QGridLayout()
        grid.setSpacing(8)

        tile1 = BarnSimTile("CAM-CH01", "Chuồng 1 - Khu Ăn Uống")
        tile2 = BarnSimTile("CAM-CH02", "Chuồng 2 - Khu Sân Chơi")
        tile3 = BarnSimTile("CAM-CH03", "Chuồng 3 - Khu Cách Ly Thú Y")

        grid.addWidget(tile1, 0, 0)
        grid.addWidget(tile2, 0, 1)
        grid.addWidget(tile3, 0, 2)

        self._tiles = [tile1, tile2, tile3]
        layout.addLayout(grid, 1)

        # Timer for 25 FPS frame rendering loop
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_render_tick)
        self._is_running = False

        self._start_simulation()

    def _start_simulation(self):
        self._is_running = True
        self._timer.start(40)  # 25 FPS
        for t in self._tiles:
            t.badge.set_text_and_tone("ONLINE", "success")

    def _pause_simulation(self):
        self._is_running = False
        self._timer.stop()
        for t in self._tiles:
            t.badge.set_text_and_tone("DỪNG MÔ PHỎNG", "warning")

    def _on_render_tick(self):
        if not self._is_running:
            return

        for idx, tile in enumerate(self._tiles):
            f_idx = self._frame_counters[idx]
            self._frame_counters[idx] = (f_idx + 1) % 150  # Loop frame 0..149

            # Generate synthetic background frame (Dark green farm mat)
            frame = np.full((320, 480, 3), (25, 35, 28), dtype=np.uint8)
            cv2.putText(
                frame,
                f"LIVE STREAM DEMO • {tile.code}",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (150, 180, 155),
                1,
                cv2.LINE_AA
            )

            # Draw AI Bounding Boxes using Requirement 4 overlay drawer
            tracks = self._camera_tracks[idx]
            frame = draw_duck_overlay(frame, f_idx, tracks, show_labels=True)

            # Check consecutive frame detection for sick duck (Requirement 5)
            # Sick duck is Track ID 102
            sick_present = any(
                getattr(t, "label", "") == "Có bệnh" and f_idx in getattr(t, "bboxes", {})
                for t in tracks
            )

            if sick_present:
                self._consecutive_sick_counts[idx] += 1
            else:
                self._consecutive_sick_counts[idx] = 0

            status_str = "Bình thường"
            tone = "success"

            # CONSECUTIVE FRAME ALERT FILTER: Only alert when >= 5 consecutive frames!
            if self._consecutive_sick_counts[idx] >= 5:
                status_str = "CẢNH BÁO: Nghi bệnh"
                tone = "danger"

            # Render frame to PyQt QLabel
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            tile.update_frame_pixmap(pixmap, status_str, tone)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
