"""
Live Monitoring View - Surveillance Dashboard matching reference UI composition in light theme.
Features upper control toolbar, horizontal stats metric boxes, camera grid, and surveillance alert panel. No emojis!
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QComboBox, QPushButton, QScrollArea, QMessageBox,
)

from app.services.camera_service import CameraService, CameraInfo
from app.ui.components.camera_card import CameraCard
from app.ui.components.alert_feed_panel import AlertFeedPanel
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.components.layout_utils import clear_layout
from app.ui.monitoring.camera_detail_dialog import CameraDetailDialog


def _stat_box(title: str, value: str, val_color: str = "#26332A") -> QFrame:
    box = QFrame()
    box.setObjectName("Card")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(1)

    lbl = QLabel(title)
    lbl.setStyleSheet("font-size: 8px; font-weight: 700; color: #68736B; text-transform: uppercase;")
    val = QLabel(value)
    val.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {val_color};")

    layout.addWidget(lbl)
    layout.addWidget(val)
    return box


class MonitoringView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._camera_service = CameraService()
        self.camera_cards: dict[str, CameraCard] = {}
        self.active_dialog: CameraDetailDialog | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self.content = QWidget()
        scroll.setWidget(self.content)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Section Title Header --------------------------------------
        hdr_layout = QVBoxLayout()
        hdr_layout.setSpacing(0)
        title_lbl = QLabel("Giám sát đàn vịt")
        title_lbl.setObjectName("PageTitle")
        sub_lbl = QLabel("Theo dõi đồng thời nhiều camera độc lập")
        sub_lbl.setObjectName("TopbarSubtitle")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addWidget(sub_lbl)
        layout.addLayout(hdr_layout)

        # --- Control Bar & Action Buttons ------------------------------
        layout.addLayout(self._build_control_bar())

        # --- Horizontal Stats Metric Strip ------------------------------
        layout.addLayout(self._build_stats_strip())

        # --- Main Monitoring Split (Grid + Alert Panel) -----------------
        main_split = QHBoxLayout()
        main_split.setSpacing(8)

        # LEFT: Responsive Camera Grid inside Scroll Area
        grid_wrap = QWidget()
        self.grid_layout = QGridLayout(grid_wrap)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(8)

        main_split.addWidget(grid_wrap, 3)

        # RIGHT: System Alert Feed Panel
        self.alert_panel = AlertFeedPanel("Cảnh báo hệ thống")
        main_split.addWidget(self.alert_panel, 1)

        layout.addLayout(main_split, 1)

        # Start Camera Stream Worker Thread
        self._camera_service.start_worker()
        if self._camera_service.worker:
            self._camera_service.worker.frame_ready.connect(self._on_frame_ready)

        self._populate_grid()

    def _build_control_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(6)

        mode_box = QFrame()
        mode_box.setObjectName("Card")
        mb_layout = QHBoxLayout(mode_box)
        mb_layout.setContentsMargins(3, 3, 3, 3)
        mb_layout.setSpacing(3)

        btn_grid = QPushButton("GIÁM SÁT NHIỀU CAMERA")
        btn_grid.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 700; font-size: 10px; padding: 2px 8px; min-height: 20px;")
        btn_stop = QPushButton("ĐÃ DỪNG")
        btn_stop.setStyleSheet("background-color: transparent; color: #68736B; font-weight: 600; font-size: 10px; padding: 2px 8px; min-height: 20px;")

        mb_layout.addWidget(btn_grid)
        mb_layout.addWidget(btn_stop)
        bar.addWidget(mode_box)

        bar.addStretch()

        start_btn = QPushButton("Bắt đầu giám sát")
        start_btn.setIcon(get_icon("fa5s.play", color="#FFFFFF"))
        start_btn.setFixedHeight(26)
        start_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        start_btn.clicked.connect(self._start_all)
        bar.addWidget(start_btn)

        pause_btn = QPushButton("Tạm dừng hiển thị")
        pause_btn.setIcon(get_icon("fa5s.pause", color="#FFFFFF"))
        pause_btn.setObjectName("WarningButton")
        pause_btn.setFixedHeight(26)
        pause_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        pause_btn.clicked.connect(self._pause_all)
        bar.addWidget(pause_btn)

        stop_btn = QPushButton("Dừng giám sát")
        stop_btn.setIcon(get_icon("fa5s.stop", color="#FFFFFF"))
        stop_btn.setObjectName("DangerButton")
        stop_btn.setFixedHeight(26)
        stop_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        stop_btn.clicked.connect(self._stop_all)
        bar.addWidget(stop_btn)

        return bar

    def _build_stats_strip(self) -> QHBoxLayout:
        strip = QHBoxLayout()
        strip.setSpacing(6)

        c_online = self._camera_service.count_online()
        c_total = self._camera_service.count_total()
        c_offline = self._camera_service.count_offline()
        alerts = self._camera_service.count_alerts()

        strip.addWidget(_stat_box("SỐ CAMERA", f"{c_online} / {c_total}"), 1)
        strip.addWidget(_stat_box("TRỰC TUYẾN", str(c_online), val_color="#2E7D32"), 1)
        strip.addWidget(_stat_box("MẤT KẾT NỐI", str(c_offline), val_color="#D32F2F" if c_offline > 0 else "#68736B"), 1)
        strip.addWidget(_stat_box("AI STATUS", "Ready", val_color="#1B5E20"), 1)
        strip.addWidget(_stat_box("CẢNH BÁO", str(alerts), val_color="#D32F2F" if alerts > 0 else "#2E7D32"), 1)

        return strip

    def _populate_grid(self) -> None:
        clear_layout(self.grid_layout)
        self.camera_cards.clear()

        cameras = self._camera_service.get_cameras()
        cols = 2

        for idx, cam in enumerate(cameras):
            card = CameraCard(cam.code, cam.name, cam.location, cam.status)
            card.doubleClicked.connect(self._open_enlarged_camera)
            card.snapshotRequested.connect(self._take_snapshot)
            card.toggleAiRequested.connect(self._toggle_ai)

            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)
            self.camera_cards[cam.code] = card

    def _on_frame_ready(self, code: str, q_img: QImage) -> None:
        if code in self.camera_cards:
            self.camera_cards[code].update_frame(q_img)
        if self.active_dialog and self.active_dialog.camera_code == code:
            self.active_dialog.update_frame(q_img)

    def _start_all(self):
        if self._camera_service.worker:
            self._camera_service.worker.paused = False
            for card in self.camera_cards.values():
                card.set_status("ONLINE", tone="success")

    def _pause_all(self):
        if self._camera_service.worker:
            self._camera_service.worker.paused = True
            for card in self.camera_cards.values():
                card.set_status("PAUSED", tone="warning")

    def _stop_all(self):
        if self._camera_service.worker:
            self._camera_service.worker.paused = True
            for card in self.camera_cards.values():
                card.set_status("STOPPED", tone="danger")

    def _open_enlarged_camera(self, camera_code: str):
        dlg = CameraDetailDialog(camera_code, parent=self)
        self.active_dialog = dlg
        dlg.exec()
        self.active_dialog = None

    def _take_snapshot(self, camera_code: str):
        QMessageBox.information(self, "Snapshot", f"Đã lưu ảnh chụp nhanh từ {camera_code}.")

    def _toggle_ai(self, camera_code: str):
        if self._camera_service.worker:
            self._camera_service.worker.show_ai_overlay = not self._camera_service.worker.show_ai_overlay
            state = "BẬT" if self._camera_service.worker.show_ai_overlay else "TẮT"
            QMessageBox.information(self, "AI Overlay", f"Đã {state} lớp phủ AI trên camera {camera_code}.")

    def refresh(self):
        self._populate_grid()
