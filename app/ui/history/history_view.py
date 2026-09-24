"""
Flock Event & System Audit History View.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
)

from app.database.connection import session_scope
from app.repositories.flock_repository import FlockRepository
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.config.constants import FlockEventType

COLUMNS = ["Thời gian", "Mã đàn", "Tên đàn", "Loại sự kiện", "Số lượng", "Lý do / Ghi chú", "Người thực hiện"]


class HistoryView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._flock_repo = FlockRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title = QLabel("Lịch sử Sự kiện & Nhật ký Hoạt động Trang trại")
        title.setObjectName("SectionTitle")
        toolbar.addWidget(title)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Tất cả loại sự kiện", None)
        for code, label in FlockEventType.LABELS_VI.items():
            self.type_combo.addItem(label, code)
        self.type_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.type_combo)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = build_table(COLUMNS)
        layout.addWidget(self.table)

        self.empty_state = EmptyState("Chưa có lịch sử sự kiện nào")
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.refresh()

    def refresh(self) -> None:
        event_type = self.type_combo.currentData()

        events_list = []
        with session_scope() as session:
            flocks = self._flock_repo.get_all(session)
            for f in flocks:
                for ev in f.events:
                    if not event_type or ev.event_type == event_type:
                        events_list.append((ev, f))
            session.expunge_all()

        events_list.sort(key=lambda x: x[0].created_at or x[0].event_date, reverse=True)

        self.table.setRowCount(len(events_list))
        for row, (ev, f) in enumerate(events_list):
            type_label = FlockEventType.LABELS_VI.get(ev.event_type, ev.event_type)
            dt_str = ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else ev.event_date.isoformat()
            set_row(self.table, row, [
                dt_str, f.flock_code, f.name,
                type_label, f"{ev.quantity:,} con", ev.reason or "-", ev.created_by or "System",
            ])

        self.table.setVisible(bool(events_list))
        self.empty_state.setVisible(not events_list)
