from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from app.ui.components.icons import get_icon


class KpiCard(QFrame):
    """
    Compact KPI Metric Card following the Duck AI Light Theme specification.
    Uses vector icons from QtAwesome (FontAwesome 5). No emojis!
    """

    def __init__(
        self,
        title: str,
        value: str,
        icon_name: str = "fa5s.chart-line",
        accent: str = "#2E7D32",
        subtext: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(60)
        self.setMaximumHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("KpiLabel")
        top_row.addWidget(self.title_label)
        top_row.addStretch()

        icon_label = QLabel()
        icon_label.setPixmap(get_icon(icon_name, color=accent).pixmap(QSize(14, 14)))
        top_row.addWidget(icon_label)
        layout.addLayout(top_row)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("KpiValue")
        self.value_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #26332A;")
        layout.addWidget(self.value_label)

        if subtext:
            self.subtext_label = QLabel(subtext)
            self.subtext_label.setObjectName("KpiSubtext")
            layout.addWidget(self.subtext_label)
        else:
            self.subtext_label = None

    def set_value(self, value: str, subtext: str = "") -> None:
        self.value_label.setText(value)
        if subtext and self.subtext_label:
            self.subtext_label.setText(subtext)
