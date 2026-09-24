from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFileDialog, QFrame, QMessageBox, QGridLayout, QComboBox, QScrollArea,
)

from app.services.ai_analysis_service import AIAnalysisService
from app.ai.video_processor import extract_metadata, generate_thumbnail, is_supported_video
from app.ui.components.table_helpers import build_table, set_row
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.config.settings import VIDEOS_DIR


class AIMonitoringView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = AIAnalysisService()
        self._selected_video_path: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self.content = QWidget()
        scroll.setWidget(self.content)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.analysis_tab = QWidget()
        self.history_tab = QWidget()

        self.tabs.addTab(self.analysis_tab, "Phân tích Video / Stream AI")
        self.tabs.addTab(self.history_tab, "Lịch sử Nhận diện & Phân tích")

        self._build_analysis_tab()
        self._build_history_tab()

        self.refresh()

    # --- Video / Stream analysis tab -------------------------------------
    def _build_analysis_tab(self) -> None:
        layout = QHBoxLayout(self.analysis_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # LEFT COLUMN: Video Player & Control Panel
        left_col = QVBoxLayout()
        left_col.setSpacing(6)

        # Video Preview Box (Dark #101512)
        preview_frame = QFrame()
        preview_frame.setObjectName("VideoFrame")
        preview_frame.setMinimumHeight(200)

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel("Khu vực xem trước Video / Stream AI\n\n(Vui lòng chọn video hoặc camera bên dưới)")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #68736B; font-size: 11px; font-weight: 500;")
        self.preview_label.setMinimumHeight(180)
        preview_layout.addWidget(self.preview_label)

        left_col.addWidget(preview_frame, 1)

        # Control Bar below video
        ctrl_card = QFrame()
        ctrl_card.setObjectName("Card")
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)
        ctrl_layout.setSpacing(6)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["Tệp Video cục bộ", "CAM-01 (Khu A)", "CAM-03 (Khu Nước)"])
        ctrl_layout.addWidget(self.source_combo)

        choose_btn = QPushButton("Upload Video")
        choose_btn.setIcon(get_icon("fa5s.folder-open", color="#2E7D32"))
        choose_btn.setObjectName("SecondaryButton")
        choose_btn.setFixedHeight(24)
        choose_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        choose_btn.clicked.connect(self._choose_video)
        ctrl_layout.addWidget(choose_btn)

        self.analyze_btn = QPushButton("Bắt đầu phân tích AI")
        self.analyze_btn.setIcon(get_icon("fa5s.play", color="#FFFFFF"))
        self.analyze_btn.setFixedHeight(24)
        self.analyze_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._run_analysis)
        ctrl_layout.addWidget(self.analyze_btn)

        stop_btn = QPushButton("Dừng")
        stop_btn.setObjectName("SecondaryButton")
        stop_btn.setFixedHeight(24)
        stop_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        stop_btn.clicked.connect(self._reset_analysis)
        ctrl_layout.addWidget(stop_btn)

        left_col.addWidget(ctrl_card)
        layout.addLayout(left_col, 2)

        # RIGHT COLUMN: Technical Analysis Results & AI Status Panel
        right_col = QVBoxLayout()
        right_col.setSpacing(6)

        # Card 1: AI Model Connection Status
        status_card = QFrame()
        status_card.setObjectName("Card")
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(8, 6, 8, 6)
        sc_layout.setSpacing(4)

        sc_hdr = QHBoxLayout()
        sc_hdr.addWidget(QLabel("<b>Trạng thái Model AI</b>"))
        sc_hdr.addStretch()
        sc_hdr.addWidget(StatusBadge("MODEL READY", tone="warning"))
        sc_layout.addLayout(sc_hdr)

        info_lbl = QLabel(
            "<b>Mô hình tích hợp:</b> Sẵn sàng cho YOLOv8 + ByteTrack<br>"
            "<b>Nhiệm vụ:</b> Nhận diện cá thể & Phát hiện hành vi bất thường (Té ngã/Lật ngửa)<br>"
            "<b>Trạng thái pipeline:</b> Chờ kết nối model trọng số (.pt / .onnx)"
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 10px; color: #68736B;")
        sc_layout.addWidget(info_lbl)
        right_col.addWidget(status_card)

        # Card 2: Metadata
        meta_card = QFrame()
        meta_card.setObjectName("Card")
        meta_layout = QGridLayout(meta_card)
        meta_layout.setContentsMargins(8, 6, 8, 6)
        meta_layout.setSpacing(4)

        self.meta_labels = {}
        for i, key in enumerate(["Thời lượng", "Độ phân giải", "Tốc độ FPS", "Dung lượng tệp"]):
            meta_layout.addWidget(QLabel(f"<b>{key}:</b>"), i // 2, (i % 2) * 2)
            val = QLabel("--")
            self.meta_labels[key] = val
            meta_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
        right_col.addWidget(meta_card)

        # Card 3: Realtime Detection Statistics
        res_card = QFrame()
        res_card.setObjectName("Card")
        res_layout = QVBoxLayout(res_card)
        res_layout.setContentsMargins(8, 6, 8, 6)
        res_layout.setSpacing(4)

        res_layout.addWidget(QLabel("<b>Kết quả phân tích nhận diện (Detection Output)</b>"))

        self.result_label = QLabel(
            "AI MODEL NOT CONNECTED\n\n"
            "Giao diện đã chuẩn bị sẵn sàng cho việc tích hợp mô hình AI.\n"
            "Các thông số nhận diện thực tế sẽ được hiển thị khi kết nối model.\n\n"
            "• Tổng số cá thể phát hiện: --\n"
            "• Cá thể di chuyển bình thường: --\n"
            "• Cá thể nghi vấn bệnh / bất thường: --\n"
            "• Độ tin cậy trung bình (Confidence): --"
        )
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 10px; color: #68736B;")
        res_layout.addWidget(self.result_label)

        right_col.addWidget(res_card, 1)

        layout.addLayout(right_col, 1)

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Video phân tích", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        if not path:
            return
        if not is_supported_video(path):
            QMessageBox.warning(self, "Định dạng không hỗ trợ", "Vui lòng chọn tệp video hợp lệ.")
            return

        self._selected_video_path = path
        self.analyze_btn.setEnabled(True)

        metadata = extract_metadata(path)
        self._current_metadata = metadata

        if metadata.valid:
            self.meta_labels["Thời lượng"].setText(f"{metadata.duration_seconds:.1f}s" if metadata.duration_seconds else "--")
            self.meta_labels["Độ phân giải"].setText(metadata.resolution or "--")
            self.meta_labels["Tốc độ FPS"].setText(str(metadata.fps) if metadata.fps else "--")
            self.meta_labels["Dung lượng tệp"].setText(f"{metadata.file_size_mb} MB")

            thumb_path = str(VIDEOS_DIR / f"_thumb_{Path(path).stem}.jpg")
            if generate_thumbnail(path, thumb_path):
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    self.preview_label.setPixmap(
                        pixmap.scaledToHeight(180, Qt.TransformationMode.SmoothTransformation)
                    )
            else:
                self.preview_label.setText(f"[ VIDEO LOADED ]\n\n{Path(path).name}")

    def _run_analysis(self) -> None:
        if not self._selected_video_path:
            return
        metadata = getattr(self, "_current_metadata", None) or extract_metadata(self._selected_video_path)

        try:
            session = self._service.run_analysis(self.current_user.username, self._selected_video_path, metadata)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi phân tích", f"Không thể lưu phiên phân tích: {exc}")
            return

        self.result_label.setText(
            f"<b>Phiên phân tích đã khởi tạo:</b> {session.model_version}<br>"
            "<b>Trạng thái:</b> Sẵn sàng cho tích hợp AI (Ready for YOLOv8 model pipeline)<br>"
            "Đã ghi nhận dữ liệu video vào lịch sử nhận diện."
        )
        self._refresh_history()
        QMessageBox.information(self, "AI Placeholder", "Đã khởi tạo phiên làm việc cho video. Khung nhận diện AI đã sẵn sàng.")

    def _reset_analysis(self) -> None:
        self._selected_video_path = None
        self.analyze_btn.setEnabled(False)
        self.preview_label.setText("Khu vực xem trước Video / Stream AI\n\n(Vui lòng chọn video hoặc camera bên dưới)")
        for val in self.meta_labels.values():
            val.setText("--")

    # --- History tab -----------------------------------------------------
    def _build_history_tab(self) -> None:
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.history_table = build_table(
            ["Tệp Video", "Thời lượng", "Độ phân giải", "FPS", "Thời gian phân tích", "Trạng thái Pipeline", "Phiên bản Model"]
        )
        layout.addWidget(self.history_table)

        self.history_empty = EmptyState("Chưa có phiên phân tích nào trong lịch sử.")
        layout.addWidget(self.history_empty)
        self.history_empty.hide()

    def _refresh_history(self) -> None:
        sessions = self._service.list_sessions()
        self.history_table.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            set_row(self.history_table, row, [
                s.file_name, f"{s.duration:.1f}s" if s.duration else "-",
                s.resolution or "-", s.fps or "-",
                s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "-",
                s.status, s.model_version,
            ])
        self.history_table.setVisible(bool(sessions))
        self.history_empty.setVisible(not sessions)

    def refresh(self) -> None:
        self._refresh_history()
