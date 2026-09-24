from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

# Maps a semantic tone to the QSS object name defined in app.qss.
_TONE_OBJECT_NAMES = {
    "success": "BadgeSuccess",
    "warning": "BadgeWarning",
    "danger": "BadgeDanger",
    "neutral": "BadgeNeutral",
}


class StatusBadge(QLabel):
    """
    A small pill-shaped status label (e.g. "Hoạt động", "Trực tuyến",
    "Cần kiểm tra") styled with a light background fill instead of a
    solid color block — matches the Modern Farm Management design
    system rather than an "AI dashboard" look.
    """

    def __init__(self, text: str, tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.set_tone(tone)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_tone(self, tone: str) -> None:
        self.setObjectName(_TONE_OBJECT_NAMES.get(tone, "BadgeNeutral"))
        # Force style re-polish since objectName changed after construction.
        self.style().unpolish(self)
        self.style().polish(self)

    def set_text_and_tone(self, text: str, tone: str) -> None:
        self.setText(text)
        self.set_tone(tone)
