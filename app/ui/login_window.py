from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QCheckBox, QMessageBox,
)

from app.config.settings import APP_NAME_VI, APP_VERSION
from app.services.auth_service import AuthService, AuthError, CurrentUser
from app.ui.components.icons import get_icon


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self._auth_service = AuthService()
        self._on_success = on_success

        self.setWindowTitle("DUCK AI — Đăng nhập hệ thống")
        self.resize(420, 480)
        self.setMinimumSize(380, 440)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(350)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(12)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        feather_icon = QLabel()
        feather_icon.setPixmap(get_icon("fa5s.feather-alt", color="#1B5E20").pixmap(QSize(24, 24)))
        logo_row.addWidget(feather_icon)

        logo_lbl = QLabel("DUCK AI")
        logo_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #1B5E20; letter-spacing: -0.3px;")
        logo_row.addWidget(logo_lbl)

        card_layout.addLayout(logo_row)

        subtitle = QLabel("Wild Duck Farm Monitoring System")
        subtitle.setStyleSheet("font-size: 11px; color: #68736B; font-weight: 500;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        version_label = QLabel(f"Hệ thống Quản lý & Giám sát AI v{APP_VERSION}")
        version_label.setStyleSheet("color: #9AA39D; font-size: 10px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(version_label)
        card_layout.addSpacing(6)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Tên đăng nhập (username)")
        card_layout.addWidget(self.username_input)

        pw_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mật khẩu")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        pw_row.addWidget(self.password_input)

        self.show_pw_btn = QPushButton()
        self.show_pw_btn.setIcon(get_icon("fa5s.eye", color="#2E7D32"))
        self.show_pw_btn.setIconSize(QSize(14, 14))
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setFixedWidth(34)
        self.show_pw_btn.setObjectName("SecondaryButton")
        self.show_pw_btn.toggled.connect(self._toggle_password_visibility)
        pw_row.addWidget(self.show_pw_btn)
        card_layout.addLayout(pw_row)

        self.remember_checkbox = QCheckBox("Ghi nhớ tài khoản trên thiết bị này")
        card_layout.addWidget(self.remember_checkbox)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #D32F2F; font-size: 11px; font-weight: 600;")
        self.error_label.setWordWrap(True)
        card_layout.addWidget(self.error_label)

        login_btn = QPushButton("Đăng nhập hệ thống")
        login_btn.setFixedHeight(36)
        login_btn.clicked.connect(self._attempt_login)
        card_layout.addWidget(login_btn)

        hint = QLabel("Demo accounts: admin / admin123 | manager / manager123")
        hint.setStyleSheet("color: #68736B; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(hint)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        self.password_input.returnPressed.connect(self._attempt_login)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())

        self._load_remembered_username()

    def _toggle_password_visibility(self, checked: bool) -> None:
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _load_remembered_username(self) -> None:
        from app.services.settings_service import SettingsService
        settings = SettingsService().load()
        remembered = settings.get("remembered_username")
        if remembered:
            self.username_input.setText(remembered)
            self.remember_checkbox.setChecked(True)
            self.password_input.setFocus()

    def _attempt_login(self) -> None:
        self.error_label.setText("")
        username = self.username_input.text().strip()
        password = self.password_input.text()

        try:
            current_user: CurrentUser = self._auth_service.login(username, password)
        except AuthError as exc:
            self.error_label.setText(str(exc))
            return
        except Exception:
            self.error_label.setText("Không thể kết nối cơ sở dữ liệu. Vui lòng thử lại.")
            return

        from app.services.settings_service import SettingsService
        SettingsService().save(
            current_user.username,
            remembered_username=username if self.remember_checkbox.isChecked() else "",
        )

        self._on_success(current_user)
