from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QLabel, QFrame, QMessageBox, QDoubleSpinBox, QCheckBox, QScrollArea,
)

from app.services.settings_service import SettingsService


class SettingsView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = SettingsService()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self.content = QWidget()
        scroll.setWidget(self.content)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(16)

        self._build_settings_form()
        self._load()

    def _build_settings_form(self):
        # Card 1: Farm Preferences
        farm_card = QFrame()
        farm_card.setObjectName("Card")
        farm_layout = QFormLayout(farm_card)
        farm_layout.setContentsMargins(18, 16, 18, 16)
        farm_layout.setSpacing(12)

        self.farm_name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Metric (kg, ml)", "Imperial (lb, oz)"])

        farm_layout.addRow(QLabel("<b>Thông tin Trang trại & Đơn vị tính</b>"))
        farm_layout.addRow("Tên trang trại *:", self.farm_name_input)
        farm_layout.addRow("Địa chỉ cơ sở:", self.address_input)
        farm_layout.addRow("Số điện thoại liên hệ:", self.phone_input)
        farm_layout.addRow("Hệ thống đơn vị:", self.unit_combo)

        self.content_layout.addWidget(farm_card)

        # Card 2: AI & Camera Parameters
        ai_card = QFrame()
        ai_card.setObjectName("Card")
        ai_layout = QFormLayout(ai_card)
        ai_layout.setContentsMargins(18, 16, 18, 16)
        ai_layout.setSpacing(12)

        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 0.99)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.75)

        self.auto_alert_cb = QCheckBox("Tự động tạo thông báo khi phát hiện vịt lật ngửa / té ngã")
        self.auto_alert_cb.setChecked(True)

        self.fps_limit_combo = QComboBox()
        self.fps_limit_combo.addItems(["24 FPS (Mặc định)", "30 FPS", "15 FPS (Tiết kiệm)"])

        ai_layout.addRow(QLabel("<b>Cấu hình Giám sát AI & Camera</b>"))
        ai_layout.addRow("Ngưỡng tin cậy AI (Confidence):", self.conf_spin)
        ai_layout.addRow("Tự động phát cảnh báo:", self.auto_alert_cb)
        ai_layout.addRow("Tốc độ khung hình xử lý:", self.fps_limit_combo)

        self.content_layout.addWidget(ai_card)

        # Card 3: Save button
        save_bar = QHBoxLayout()
        save_btn = QPushButton("Lưu tất cả thay đổi Cài đặt")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        save_bar.addWidget(save_btn)
        save_bar.addStretch()
        self.content_layout.addLayout(save_bar)

        # Card 4: System info
        info_card = QFrame()
        info_card.setObjectName("Card")
        info_layout = QFormLayout(info_card)
        info_layout.setContentsMargins(18, 16, 18, 16)

        app_info = self._service.app_info()
        info_layout.addRow(QLabel("<b>Thông tin Hệ thống & Cơ sở Dữ liệu</b>"))
        info_layout.addRow("Phần mềm:", QLabel(app_info["name"]))
        info_layout.addRow("Phiên bản:", QLabel(app_info["version"]))
        info_layout.addRow("Đường dẫn Database:", QLabel(app_info["database_path"]))

        self.content_layout.addWidget(info_card)
        self.content_layout.addStretch()

    def refresh(self) -> None:
        self._load()

    def _load(self) -> None:
        data = self._service.load()
        self.farm_name_input.setText(data.get("farm_name", "Wild Duck Farm"))
        self.address_input.setText(data.get("address", ""))
        self.phone_input.setText(data.get("phone", ""))
        idx = self.unit_combo.findText(data.get("unit_system", "Metric (kg, ml)"))
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)

    def _save(self) -> None:
        self._service.save(
            self.current_user.username,
            farm_name=self.farm_name_input.text(), address=self.address_input.text(),
            phone=self.phone_input.text(), unit_system=self.unit_combo.currentText(),
        )
        QMessageBox.information(self, "Cài đặt", "Đã lưu cài đặt hệ thống thành công.")
