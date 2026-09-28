"""
Production Tracking View - Track egg yields, flock efficiency and trends.
"""
from __future__ import annotations

import datetime as dt
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QMessageBox, QDialog, QFormLayout, QComboBox, QDateEdit,
    QSpinBox, QDoubleSpinBox, QSizePolicy,
)

import pyqtgraph as pg

from app.database.connection import session_scope
from app.repositories.flock_repository import FlockRepository, ProductionRecordRepository
from app.ui.components.kpi_card import KpiCard
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.ui.components.icons import get_icon
from app.ui.components.layout_utils import clear_layout

pg.setConfigOption("background", "#FFFFFF")
pg.setConfigOption("foreground", "#26332A")


class ProductionRecordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ghi nhận Sản lượng Trứng")
        self.setFixedWidth(380)

        self._flock_repo = FlockRepository()
        self._prod_repo = ProductionRecordRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setSpacing(10)

        self.flock_combo = QComboBox()
        with session_scope() as session:
            flocks = self._flock_repo.get_active(session)
            for f in flocks:
                self.flock_combo.addItem(f"{f.flock_code} — {f.name}", f.id)
        form.addRow("Đàn vịt *:", self.flock_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(dt.date.today())
        form.addRow("Ngày thu hoạch *:", self.date_edit)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 10000)
        self.qty_spin.setValue(150)
        form.addRow("Số quả trứng *:", self.qty_spin)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 500.0)
        self.weight_spin.setValue(2.1)
        self.weight_spin.setSuffix(" kg / 10 quả")
        form.addRow("Trọng lượng TB:", self.weight_spin)

        self.feed_spin = QDoubleSpinBox()
        self.feed_spin.setRange(0.0, 5000.0)
        self.feed_spin.setValue(45.0)
        self.feed_spin.setSuffix(" kg")
        form.addRow("Lượng cám tiêu thụ:", self.feed_spin)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Lưu sản lượng")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _save(self):
        flock_id = self.flock_combo.currentData()
        if not flock_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một đàn vịt.")
            return

        with session_scope() as session:
            from app.database.models import ProductionRecord
            rec = ProductionRecord(
                flock_id=flock_id,
                record_date=self.date_edit.date().toPyDate(),
                egg_quantity=self.qty_spin.value(),
                average_weight=self.weight_spin.value(),
                feed_consumption=self.feed_spin.value(),
            )
            session.add(rec)

        self.accept()


class ProductionView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._flock_repo = FlockRepository()
        self._prod_repo = ProductionRecordRepository()

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
        self.content_layout.setContentsMargins(10, 8, 10, 10)
        self.content_layout.setSpacing(6)

        self.refresh()

    def refresh(self) -> None:
        clear_layout(self.content_layout)

        today = dt.date.today()
        since = today - dt.timedelta(days=14)

        record_data = []
        with session_scope() as session:
            records = self._prod_repo.get_since(session, since)
            for r in records:
                record_data.append({
                    "date": r.record_date,
                    "egg_quantity": r.egg_quantity,
                    "avg_weight": r.average_weight,
                    "feed_consumption": r.feed_consumption,
                    "flock_code": r.flock.flock_code if r.flock else f"Flock #{r.flock_id}",
                    "flock_name": r.flock.name if r.flock else "-",
                })

        today_eggs = sum(r["egg_quantity"] for r in record_data if r["date"] == today)
        total_14_days = sum(r["egg_quantity"] for r in record_data)
        avg_daily = round(total_14_days / 14.0, 1) if record_data else 0

        # Toolbar & Title
        tb = QHBoxLayout()
        tb_title = QLabel("Báo cáo & Theo dõi Sản lượng Trứng")
        tb_title.setObjectName("SectionTitle")
        tb.addWidget(tb_title)
        tb.addStretch()

        add_btn = QPushButton("Ghi nhận sản lượng")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.setFixedHeight(26)
        add_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        add_btn.clicked.connect(self._add_record)
        tb.addWidget(add_btn)
        self.content_layout.addLayout(tb)

        # KPI Row with vector icons
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(6)
        kpi_row.addWidget(KpiCard("TODAY PRODUCTION", f"{today_eggs:,} quả", "fa5s.egg", "#2E7D32"))
        kpi_row.addWidget(KpiCard("14-DAY TOTAL", f"{total_14_days:,} quả", "fa5s.chart-bar", "#2E7D32"))
        kpi_row.addWidget(KpiCard("DAILY AVERAGE", f"{avg_daily:,} quả/ngày", "fa5s.chart-line", "#F4A62D"))
        kpi_row.addWidget(KpiCard("TOP PRODUCING FLOCK", "VD-001", "fa5s.trophy", "#2E7D32"))
        self.content_layout.addLayout(kpi_row)

        # Production Trend Chart (Clean Compact PyQtGraph)
        chart_frame = QFrame()
        chart_frame.setObjectName("Card")
        cf_layout = QVBoxLayout(chart_frame)
        cf_layout.setContentsMargins(8, 6, 8, 6)
        cf_layout.setSpacing(2)
        cf_layout.addWidget(QLabel("<b>Xu hướng sản lượng trứng 14 ngày qua (Daily Production Trend)</b>"))

        if record_data:
            plot = pg.PlotWidget()
            plot.setFixedHeight(125)
            plot.showGrid(x=True, y=True, alpha=0.15)
            by_day: dict[dt.date, int] = {}
            for r in record_data:
                by_day[r["date"]] = by_day.get(r["date"], 0) + r["egg_quantity"]
            sorted_days = sorted(by_day.items())

            x = list(range(len(sorted_days)))
            y = [qty for _, qty in sorted_days]
            plot.plot(x, y, pen=pg.mkPen("#2E7D32", width=2), symbol="o", symbolSize=4, symbolBrush="#2E7D32")

            axis = plot.getAxis("bottom")
            axis.setTicks([[(i, d.strftime("%d/%m")) for i, (d, _) in enumerate(sorted_days)]])
            cf_layout.addWidget(plot)
        else:
            cf_layout.addWidget(EmptyState("Chưa có dữ liệu sản lượng"))

        self.content_layout.addWidget(chart_frame)

        # Production History Table - Expanded to fit viewport
        table_frame = QFrame()
        table_frame.setObjectName("Card")
        tf_layout = QVBoxLayout(table_frame)
        tf_layout.setContentsMargins(8, 6, 8, 6)
        tf_layout.setSpacing(4)
        tf_layout.addWidget(QLabel("<b>Nhật ký thu hoạch sản lượng (Production Log)</b>"))

        table = build_table(["Ngày thu hoạch", "Tên đàn", "Số trứng (Quả)", "Trọng lượng TB", "Lượng cám (kg)"])
        table.setRowCount(len(record_data))
        for row, r in enumerate(reversed(record_data)):
            set_row(table, row, [
                r["date"].isoformat(), r["flock_name"],
                f"{r['egg_quantity']:,}", f"{r['avg_weight'] or '-'} kg", f"{r['feed_consumption'] or '-'} kg",
            ])
        table.setMinimumHeight(180)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tf_layout.addWidget(table, 1)

        self.content_layout.addWidget(table_frame, 1)

    def _add_record(self):
        dlg = ProductionRecordDialog(parent=self)
        if dlg.exec():
            self.refresh()
