from __future__ import annotations

from PyQt6.QtWidgets import QLayout

def clear_layout(layout: QLayout | None) -> None:
    """
    Recursively remove and delete all widgets and sub-layouts from a QLayout.
    Prevents floating/overlapping widgets when refreshing views in PyQt.
    """
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        sub_layout = item.layout()
        if sub_layout is not None:
            clear_layout(sub_layout)
