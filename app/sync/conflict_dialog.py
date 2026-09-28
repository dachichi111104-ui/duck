"""
Conflict Resolution Dialog for Desktop App.

Allows user to choose between keeping their local changes or overriding
with the remote server version when a sync conflict occurs.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit,
)

from app.ui.components.icons import get_icon


class ConflictResolutionDialog(QDialog):
    """
    Conflict Resolution: Last Write Wins strategy with manual fallback choice.
    Presents user with options:
    - Keep Local: re-flags sync_status=PENDING to overwrite server.
    - Use Remote: overwrites local SQLite record with server version and sets sync_status=SYNCED.
    """
    def __init__(self, entity_name: str, local_info: str, remote_info: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xử lý xung đột đồng bộ (Sync Conflict)")
        self.setFixedSize(520, 380)
        self.result_choice = None  # "keep_local" or "use_remote"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("fa5s.exclamation-triangle", color="#D32F2F").pixmap(QSize(24, 24)))
        header_row.addWidget(icon_lbl)

        title = QLabel(f"Xung đột dữ liệu: {entity_name}")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #D32F2F;")
        header_row.addWidget(title, 1)
        layout.addLayout(header_row)

        desc = QLabel(
            "Bản ghi trên máy tính của bạn và bản ghi trên Máy chủ Web đã bị chỉnh sửa khác nhau. "
            "Vui lòng chọn phiên bản dữ liệu bạn muốn ưu tiên giữ lại:"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #26332A; font-size: 11px;")
        layout.addWidget(desc)

        cols = QHBoxLayout()

        # Local Card
        local_card = QFrame()
        local_card.setStyleSheet("border: 1px solid #D8E2DA; background-color: #F7FAF7; border-radius: 6px; padding: 8px;")
        local_v = QVBoxLayout(local_card)
        l_title = QLabel("Bản ghi Cục bộ (Local)")
        l_title.setStyleSheet("font-weight: 700; color: #2E7D32;")
        local_v.addWidget(l_title)
        l_txt = QTextEdit()
        l_txt.setReadOnly(True)
        l_txt.setText(local_info)
        local_v.addWidget(l_txt)
        cols.addWidget(local_card)

        # Remote Card
        remote_card = QFrame()
        remote_card.setStyleSheet("border: 1px solid #D8E2DA; background-color: #FFF4DD; border-radius: 6px; padding: 8px;")
        remote_v = QVBoxLayout(remote_card)
        r_title = QLabel("Bản ghi Máy chủ (Remote Server)")
        r_title.setStyleSheet("font-weight: 700; color: #F4A62D;")
        remote_v.addWidget(r_title)
        r_txt = QTextEdit()
        r_txt.setReadOnly(True)
        r_txt.setText(remote_info)
        remote_v.addWidget(r_txt)
        cols.addWidget(remote_card)

        layout.addLayout(cols, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_local = QPushButton("Giữ bản của tôi (Local)")
        btn_local.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 700; padding: 8px 16px; border-radius: 5px;")
        btn_local.clicked.connect(self._choose_local)
        btn_row.addWidget(btn_local)

        btn_remote = QPushButton("Lấy bản trên Server (Remote)")
        btn_remote.setStyleSheet("background-color: #F4A62D; color: #26332A; font-weight: 700; padding: 8px 16px; border-radius: 5px;")
        btn_remote.clicked.connect(self._choose_remote)
        btn_row.addWidget(btn_remote)

        layout.addLayout(btn_row)

    def _choose_local(self):
        self.result_choice = "keep_local"
        self.accept()

    def _choose_remote(self):
        self.result_choice = "use_remote"
        self.accept()
