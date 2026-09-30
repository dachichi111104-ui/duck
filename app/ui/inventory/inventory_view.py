from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTabWidget, QMessageBox, QLabel, QComboBox, QFrame,
)

from app.services.inventory_service import InventoryService
from app.ui.components.kpi_card import KpiCard
from app.ui.components.table_helpers import build_table, set_row, get_row_data
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.inventory.item_form_dialog import ItemFormDialog
from app.ui.inventory.transaction_dialog import TransactionDialog
from app.config.constants import InventoryTransactionType

ITEM_COLUMNS = ["Tên vật tư", "Danh mục", "Tồn kho hiện tại", "Định mức tối thiểu", "Đơn giá", "Hạn sử dụng", "Trạng thái kho"]


class InventoryView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = InventoryService()
        self._all_items = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # KPI Metrics Row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        layout.addLayout(self.kpi_layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.items_tab = QWidget()
        self.transactions_tab = QWidget()
        self.alerts_tab = QWidget()

        self.tabs.addTab(self.items_tab, "Danh mục Kho & Vật tư")
        self.tabs.addTab(self.transactions_tab, "Nhật ký Nhập / Xuất kho")
        self.tabs.addTab(self.alerts_tab, "Cảnh báo Tồn kho & Hạn dùng")

        self._build_items_tab()
        self._build_transactions_tab()
        self._build_alerts_tab()

        self.refresh()

    def _update_kpi_row(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_items = len(self._all_items)
        low_stock = sum(1 for i in self._all_items if i.is_low_stock)
        out_of_stock = sum(1 for i in self._all_items if i.quantity == 0)

        self.kpi_layout.addWidget(KpiCard("TOTAL ITEMS", f"{total_items} loại", "fa5s.boxes", "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("LOW STOCK WARNINGS", f"{low_stock} món", "fa5s.exclamation-triangle", "#F4A62D" if low_stock > 0 else "#2E7D32"))
        self.kpi_layout.addWidget(KpiCard("OUT OF STOCK", f"{out_of_stock} món", "fa5s.times-circle", "#D32F2F" if out_of_stock > 0 else "#2E7D32"))

    # --- Items tab -------------------------------------------------------
    def _build_items_tab(self) -> None:
        layout = QVBoxLayout(self.items_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên vật tư hoặc mã...")
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input, 2)

        self.category_filter = QComboBox()
        self.category_filter.addItem("Tất cả danh mục", None)
        self.category_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.category_filter, 1)

        add_btn = QPushButton("Thêm vật tư mới")
        add_btn.setIcon(get_icon("fa5s.plus", color="#FFFFFF"))
        add_btn.clicked.connect(self._add_item)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = build_table(ITEM_COLUMNS)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        import_btn = QPushButton("Nhập kho")
        import_btn.clicked.connect(lambda: self._open_transaction(InventoryTransactionType.IMPORT))
        actions.addWidget(import_btn)

        export_btn = QPushButton("Xuất kho")
        export_btn.setObjectName("SecondaryButton")
        export_btn.clicked.connect(lambda: self._open_transaction(InventoryTransactionType.EXPORT))
        actions.addWidget(export_btn)

        adjust_btn = QPushButton("Điều chỉnh")
        adjust_btn.setObjectName("SecondaryButton")
        adjust_btn.clicked.connect(lambda: self._open_transaction(InventoryTransactionType.ADJUSTMENT))
        actions.addWidget(adjust_btn)

        edit_btn = QPushButton("Sửa thông tin")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        actions.addWidget(edit_btn)

        delete_btn = QPushButton("Xóa vật tư")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(delete_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.empty_state = EmptyState("Chưa có vật tư nào trong kho", "+ Thêm vật tư mới", self._add_item)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

    def _apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()
        cat_id = self.category_filter.currentData()

        filtered = [
            i for i in self._all_items
            if (not text or text in getattr(i, "code", "").lower() or text in i.name.lower() or (i.category and text in i.category.name.lower()))
            and (not cat_id or i.category_id == cat_id)
        ]
        self.table.setRowCount(len(filtered))
        for row, i in enumerate(filtered):
            if i.quantity == 0:
                status_str, tone = "Out of Stock", "danger"
            elif i.is_low_stock:
                status_str, tone = "Low Stock", "warning"
            else:
                status_str, tone = "In Stock", "success"

            set_row(self.table, row, [
                i.name, i.category.name if i.category else "-",
                f"{i.quantity} {i.unit}", f"{i.minimum_quantity} {i.unit}",
                f"{i.unit_price:,.0f} đ", i.expiry_date.isoformat() if i.expiry_date else "-",
                status_str,
            ], row_data=i.id)
        self.table.setVisible(bool(filtered))
        self.empty_state.setVisible(not filtered)

    def _selected_item(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item_id = get_row_data(self.table, row)
        return next((i for i in self._all_items if i.id == item_id), None)

    def _add_item(self) -> None:
        dlg = ItemFormDialog(self.current_user, parent=self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Sửa vật tư", "Vui lòng chọn một vật tư.")
            return
        dlg = ItemFormDialog(self.current_user, item=item, parent=self)
        if dlg.exec():
            self.refresh()

    def _delete_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Xóa vật tư", "Vui lòng chọn một vật tư.")
            return
        confirm = QMessageBox.question(self, "Xác nhận xóa", f"Xóa vật tư '{item.name}'?")
        if confirm == QMessageBox.StandardButton.Yes:
            self._service.delete_item(self.current_user.username, item.id)
            self.refresh()

    def _open_transaction(self, txn_type: str) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Giao dịch kho", "Vui lòng chọn một vật tư từ danh sách.")
            return
        dlg = TransactionDialog(self.current_user, item, default_type=txn_type, parent=self)
        if dlg.exec():
            self.refresh()

    # --- Transactions tab ------------------------------------------------
    def _build_transactions_tab(self) -> None:
        layout = QVBoxLayout(self.transactions_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self.txn_table = build_table(["Thời gian", "Tên vật tư", "Loại giao dịch", "Số lượng", "Mã tham chiếu", "Ghi chú"])
        layout.addWidget(self.txn_table)

    def _refresh_transactions(self) -> None:
        txns = self._service.recent_transactions(limit=100)
        self.txn_table.setRowCount(len(txns))
        for row, t in enumerate(txns):
            set_row(self.txn_table, row, [
                t.transaction_date.isoformat(), t.item.name if t.item else "-",
                t.transaction_type, t.quantity, t.reference or "-", t.note or "-",
            ])

    # --- Alerts tab ----------------------------------------------------
    def _build_alerts_tab(self) -> None:
        self._alerts_layout = QVBoxLayout(self.alerts_tab)
        self._alerts_layout.setContentsMargins(10, 10, 10, 10)

    def _refresh_alerts(self) -> None:
        while self._alerts_layout.count():
            item = self._alerts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        low_stock = self._service.get_low_stock_items()
        expiring = self._service.get_expiring_items(within_days=30)

        card1 = QFrame()
        card1.setObjectName("Card")
        c1_layout = QVBoxLayout(card1)
        c1_layout.addWidget(QLabel("<b>Vật tư chạm ngưỡng tồn tối thiểu (Low Stock Alerts)</b>"))
        if low_stock:
            for item in low_stock:
                c1_layout.addWidget(QLabel(f"● <b>{item.name}</b>: còn {item.quantity} {item.unit} (định mức: {item.minimum_quantity})"))
        else:
            c1_layout.addWidget(QLabel("Tất cả vật tư đều đạt định mức an toàn."))
        self._alerts_layout.addWidget(card1)

        card2 = QFrame()
        card2.setObjectName("Card")
        c2_layout = QVBoxLayout(card2)
        c2_layout.addWidget(QLabel("<b>Vật tư thuốc / vắc xin sắp hết hạn trong 30 ngày (Expiring Items)</b>"))
        if expiring:
            for item in expiring:
                c2_layout.addWidget(QLabel(f"● <b>{item.name}</b>: ngày hết hạn {item.expiry_date}"))
        else:
            c2_layout.addWidget(QLabel("Không có vật tư nào sắp hết hạn."))
        self._alerts_layout.addWidget(card2)

        self._alerts_layout.addStretch()

    def refresh(self) -> None:
        self._all_items = self._service.list_items()

        # Populate Category Filter Dropdown
        curr_cat_id = self.category_filter.currentData()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Tất cả danh mục", None)
        try:
            for cat in self._service.list_categories():
                self.category_filter.addItem(cat.name, cat.id)
        except Exception:
            pass
        if curr_cat_id is not None:
            idx = self.category_filter.findData(curr_cat_id)
            if idx >= 0:
                self.category_filter.setCurrentIndex(idx)
        self.category_filter.blockSignals(False)

        self._update_kpi_row()
        self._apply_filter()
        self._refresh_transactions()
        self._refresh_alerts()
