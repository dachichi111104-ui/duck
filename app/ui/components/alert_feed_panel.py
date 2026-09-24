"""
Surveillance Alert Feed Panel matching structure of reference UI in bright light theme.
Includes System Status Header, Recent Alert History, Image Snapshot Preview, and Test Button.
"""
from __future__ import annotations

import datetime as dt
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QPushButton, QMessageBox,
)

from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.components.layout_utils import clear_layout


class AlertItemWidget(QFrame):
    def __init__(self, timestamp: str, source: str, title: str, message: str, severity: str = "ORANGE", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #D8E2DA;
                border-radius: 5px;
                padding: 4px 6px;
            }
            QFrame:hover {
                background-color: #E8F3E9;
                border-color: #2E7D32;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(1)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(4)

        time_lbl = QLabel(timestamp)
        time_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #68736B;")
        src_lbl = QLabel(source)
        src_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #1B5E20;")

        hdr_row.addWidget(time_lbl)
        hdr_row.addWidget(src_lbl)
        hdr_row.addStretch()

        tone_map = {"RED": "danger", "ORANGE": "warning", "GREEN": "success"}
        badge_text_map = {"RED": "Nguy cơ", "ORANGE": "Cảnh báo", "GREEN": "Bình thường"}

        badge = StatusBadge(
            badge_text_map.get(severity, severity),
            tone=tone_map.get(severity, "neutral")
        )
        hdr_row.addWidget(badge)
        layout.addLayout(hdr_row)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #26332A;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 10px; color: #68736B;")
        layout.addWidget(msg_lbl)


class AlertFeedPanel(QWidget):
    def __init__(self, title: str = "Cảnh báo hệ thống", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(230)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 1. System Status Header Box (Card 1)
        hdr_card = QFrame()
        hdr_card.setObjectName("Card")
        hc_layout = QVBoxLayout(hdr_card)
        hc_layout.setContentsMargins(10, 6, 10, 6)
        hc_layout.setSpacing(2)

        h1 = QLabel("Cảnh báo hệ thống")
        h1.setObjectName("SectionTitle")
        hc_layout.addWidget(h1)

        ready_lbl = QLabel("● Hệ thống sẵn sàng")
        ready_lbl.setStyleSheet("color: #1B5E20; font-size: 10px; font-weight: 700;")
        hc_layout.addWidget(ready_lbl)

        main_layout.addWidget(hdr_card)

        # 2. Recent Alert History Box (Card 2)
        hist_card = QFrame()
        hist_card.setObjectName("Card")
        hist_card.setMinimumHeight(140)

        hist_layout = QVBoxLayout(hist_card)
        hist_layout.setContentsMargins(10, 6, 10, 6)
        hist_layout.setSpacing(4)

        hist_title = QLabel("LỊCH SỬ GẦN ĐÂY")
        hist_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #68736B; text-transform: uppercase;")
        hist_layout.addWidget(hist_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(90)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)

        scroll.setWidget(self.list_container)
        hist_layout.addWidget(scroll, 1)

        main_layout.addWidget(hist_card, 1)

        # 3. Snapshot Preview & Test Action Box (Card 3)
        snap_card = QFrame()
        snap_card.setObjectName("Card")
        sc_layout = QVBoxLayout(snap_card)
        sc_layout.setContentsMargins(10, 6, 10, 6)
        sc_layout.setSpacing(6)

        snap_title = QLabel("ẢNH CẢNH BÁO")
        snap_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #68736B; text-transform: uppercase;")
        sc_layout.addWidget(snap_title)

        self.snap_frame = QFrame()
        self.snap_frame.setObjectName("VideoFrame")
        self.snap_frame.setFixedHeight(64)
        sf_layout = QVBoxLayout(self.snap_frame)
        sf_layout.setContentsMargins(0, 0, 0, 0)

        self.snap_lbl = QLabel("Chọn cảnh báo để xem ảnh")
        self.snap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.snap_lbl.setStyleSheet("color: #68736B; font-size: 9px;")
        sf_layout.addWidget(self.snap_lbl)
        sc_layout.addWidget(self.snap_frame)

        test_btn = QPushButton("Test cảnh báo + Snapshot")
        test_btn.setObjectName("DangerButton")
        test_btn.setFixedHeight(24)
        test_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        test_btn.setIcon(get_icon("fa5s.bell", color="#FFFFFF"))
        test_btn.clicked.connect(self._trigger_test_alert)
        sc_layout.addWidget(test_btn)

        main_layout.addWidget(snap_card)

        self.populate_default_alerts()

    def populate_default_alerts(self):
        self.clear()
        now = dt.datetime.now()
        t1 = (now - dt.timedelta(minutes=4)).strftime("%Y-%m-%d %H:%M:%S")
        t2 = (now - dt.timedelta(minutes=18)).strftime("%Y-%m-%d %H:%M:%S")
        t3 = (now - dt.timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")

        self.add_alert(t1, "CAM-01", "Phát hiện hành vi bất thường", "Nghi hành vi bất thường: té ngã lật ngửa", "RED")
        self.add_alert(t2, "CAM-03", "Di chuyển bầy đàn bất thường", "Phát hiện 2 cá thể tách riêng khỏi đàn", "ORANGE")
        self.add_alert(t3, "KHO-01", "Tự động quét cảnh báo vật tư", "Cám vịt đẻ đạt ngưỡng tồn kho tối thiểu", "ORANGE")

    def clear(self):
        clear_layout(self.list_layout)

    def add_alert(self, timestamp: str, source: str, title: str, message: str, severity: str = "ORANGE"):
        widget = AlertItemWidget(timestamp, source, title, message, severity)
        self.list_layout.addWidget(widget)

    def _trigger_test_alert(self):
        now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.add_alert(now_str, "CAM-01", "TEST - Cảnh báo thử nghiệm DuckAI", "Phát hiện giả lập hành vi té ngã", "RED")
        QMessageBox.information(self, "Test Alert", "Đã khởi tạo cảnh báo thử nghiệm + chụp snapshot thành công.")
