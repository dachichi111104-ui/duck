from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class EmptyState(QWidget):
    def __init__(self, message: str, action_text: str | None = None, on_action=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(message)
        label.setObjectName("EmptyState")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        if action_text and on_action:
            btn = QPushButton(action_text)
            btn.clicked.connect(on_action)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
