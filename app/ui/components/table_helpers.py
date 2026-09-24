from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView


def build_table(headers: list[str]) -> QTableWidget:
    """Create a QTableWidget pre-configured with the app's standard table UX
    (sorting, alternating rows, full-row selection, stretched last column)."""
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSortingEnabled(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(34)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return table


def fit_table_height(table: QTableWidget, max_rows: int = 15) -> None:
    """Dynamically set QTableWidget minimum height based on row count
    so it expands inside parent QScrollArea without nested scrollbars or row clipping."""
    header_h = table.horizontalHeader().height() or 32
    row_h = table.verticalHeader().defaultSectionSize() or 34
    row_count = max(1, min(table.rowCount(), max_rows))
    total_h = header_h + (row_count * row_h) + 12
    table.setMinimumHeight(total_h)


def set_row(table: QTableWidget, row: int, values: list, row_data=None) -> None:
    for col, value in enumerate(values):
        item = QTableWidgetItem(str(value) if value is not None else "")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if col == 0 and row_data is not None:
            item.setData(Qt.ItemDataRole.UserRole, row_data)
        table.setItem(row, col, item)


def get_row_data(table: QTableWidget, row: int):
    item = table.item(row, 0)
    return item.data(Qt.ItemDataRole.UserRole) if item else None
