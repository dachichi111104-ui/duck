from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)

import pyqtgraph as pg

from app.services.dashboard_service import DashboardService
from app.services.camera_service import CameraService
from app.ui.components.kpi_card import KpiCard
from app.ui.components.empty_state import EmptyState
from app.ui.components.alert_feed_panel import AlertFeedPanel
from app.ui.components.status_badge import StatusBadge
from app.ui.components.layout_utils import clear_layout

pg.setConfigOption("background", "#FFFFFF")
pg.setConfigOption("foreground", "#26332A")


def _section_frame(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setObjectName("SectionTitle")
    layout.addWidget(label)
    return frame, layout


class DashboardView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = DashboardService()
        self._camera_service = CameraService()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer.addWidget(scroll)

        self.content = QWidget()
        scroll.setWidget(self.content)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 8, 10, 8)
        self.content_layout.setSpacing(6)

        self.refresh()

    def refresh(self) -> None:
        clear_layout(self.content_layout)

        data = self._service.get_dashboard_data()
        cam_online = self._camera_service.count_online()
        cam_total = self._camera_service.count_total()

        # --- Top KPI Cards (5 compact cards with vector icons) -------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(6)

        kpi_row.addWidget(KpiCard("TOTAL BIRDS", f"{data.total_ducks:,} con", "fa5s.feather-alt", "#2E7D32", f"{data.total_flocks} đàn"))
        kpi_row.addWidget(KpiCard("ACTIVE CAMERAS", f"{cam_online} / {cam_total}", "fa5s.video", "#2E7D32", f"{cam_online} trực tuyến"))
        kpi_row.addWidget(KpiCard("ONLINE CAMERAS", str(cam_online), "fa5s.broadcast-tower", "#2E7D32", "0 mất kết nối"))
        kpi_row.addWidget(KpiCard("ACTIVE ALERTS", f"{data.active_alerts:02d}", "fa5s.exclamation-triangle", "#D32F2F" if data.active_alerts > 0 else "#2E7D32", "Cần xử lý"))
        kpi_row.addWidget(KpiCard("PRODUCTION", f"{data.today_egg_production:,} quả", "fa5s.egg", "#F4A62D", "Hôm nay"))

        self.content_layout.addLayout(kpi_row)

        # --- Main Grid: Left Chart + Right System Alerts Panel ----------
        main_row = QHBoxLayout()
        main_row.setSpacing(6)

        # LEFT LARGE: Egg production trend chart
        chart_frame, chart_layout = _section_frame("Sản lượng trứng 14 ngày gần nhất")
        if data.production_series:
            plot = pg.PlotWidget()
            plot.setFixedHeight(125)
            plot.showGrid(x=True, y=True, alpha=0.15)
            plot.getAxis("left").setPen("#D8E2DA")
            plot.getAxis("bottom").setPen("#D8E2DA")

            x = list(range(len(data.production_series)))
            y = [qty for _, qty in data.production_series]
            plot.plot(x, y, pen=pg.mkPen("#2E7D32", width=2), symbol="o", symbolSize=4, symbolBrush="#2E7D32")
            axis = plot.getAxis("bottom")
            axis.setTicks([[(i, d) for i, (d, _) in enumerate(data.production_series)]])
            chart_layout.addWidget(plot)
        else:
            chart_layout.addWidget(EmptyState("Chưa có dữ liệu sản lượng"))
        main_row.addWidget(chart_frame, 2)

        # RIGHT SMALL: System Alert Feed
        alert_feed = AlertFeedPanel("System Alerts")
        main_row.addWidget(alert_feed, 1)

        self.content_layout.addLayout(main_row)

        # --- Bottom Grid: Health Overview + Camera Status + Activity ------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        # 1. Flock Health Overview
        health_frame, health_layout = _section_frame("Tình trạng sức khỏe đàn")
        total_health = sum(data.health_distribution.values()) if data.health_distribution else 0
        if total_health:
            for label, count in data.health_distribution.items():
                pct = round(count / total_health * 100, 1)
                row_layout = QHBoxLayout()
                row_layout.setSpacing(4)
                row_layout.addWidget(QLabel(f"<b>{label}:</b> {count} đàn ({pct}%)"))
                tone = "success" if label == "Bình thường" else "warning"
                row_layout.addWidget(StatusBadge(label, tone=tone))
                health_layout.addLayout(row_layout)
        else:
            health_layout.addWidget(EmptyState("Chưa có dữ liệu sức khỏe"))
        bottom_row.addWidget(health_frame, 1)

        # 2. Camera Status Summary
        cam_frame, cam_layout = _section_frame("Trạng thái camera")
        cam_list = self._camera_service.get_cameras()
        for c in cam_list[:4]:
            c_row = QHBoxLayout()
            c_row.setSpacing(4)
            c_row.addWidget(QLabel(f"<b>{c.code}</b> • {c.location}"))
            c_row.addStretch()
            tone = "success" if c.status == "ONLINE" else "danger"
            c_row.addWidget(StatusBadge(c.status, tone=tone))
            cam_layout.addLayout(c_row)
        bottom_row.addWidget(cam_frame, 1)

        # 3. Recent Farm Activity
        act_frame, act_layout = _section_frame("Nhắc nhở thú y sắp tới")
        if data.upcoming_vaccinations:
            for v in data.upcoming_vaccinations[:3]:
                code = v.flock.flock_code if v.flock else f"Flock #{v.flock_id}"
                act_layout.addWidget(QLabel(f"<b>{code}</b>: {v.vaccine_name} ({v.next_date})"))
        else:
            act_layout.addWidget(EmptyState("Không có nhắc nhở thú y"))
        bottom_row.addWidget(act_frame, 1)

        self.content_layout.addLayout(bottom_row)
