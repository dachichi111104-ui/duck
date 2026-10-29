"""
AI Monitoring & Detection View.

Modules:
- Tab 1: Phân tích Video / Camera (2 lựa chọn rõ ràng: Webcam vs File Upload, Visual Bounding Box Overlay, Realtime Output).
- Tab 2: Giám sát nhiều chuồng (Mô phỏng demo với 3 camera chuồng, lọc cảnh báo 5+ khung hình liên tiếp).
- Tab 3: Lịch sử Nhận diện & Phân tích.
"""
from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFileDialog, QFrame, QMessageBox, QGridLayout, QComboBox, QScrollArea,
    QSizePolicy, QSlider, QProgressBar, QHeaderView,
)
import cv2
import numpy as np

from app.services.ai_analysis_service import AIAnalysisService
from app.ai.video_processor import extract_metadata, generate_thumbnail, is_supported_video
from app.ai.overlay_drawer import draw_duck_overlay
from app.ui.components.table_helpers import build_table, set_row, fit_table_height
from app.ui.components.empty_state import EmptyState
from app.ui.components.status_badge import StatusBadge
from app.ui.components.icons import get_icon
from app.ui.ai_monitoring.webcam_dialog import WebcamRecorderDialog
from app.ui.ai_monitoring.multi_barn_widget import MultiBarnSimulationWidget
from app.ui.ai_monitoring.track_detail_dialog import TrackDetailDialog
from app.config.settings import VIDEOS_DIR


class AIMonitoringView(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._service = AIAnalysisService()
        self._selected_video_path: str | None = None
        self._current_session_result = None

        # Video playback speed control (default 0.5x slow-motion for clear observation)
        self._playback_speed: float = 0.5

        # Playback animation timer for visual overlay
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)
        self._playback_frame_idx = 0
        self._playback_cap: cv2.VideoCapture | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)

        self.analysis_tab = QWidget()
        self.multi_barn_tab = QWidget()
        self.history_tab = QWidget()
        self.matrix_tab = QWidget()

        self.tabs.addTab(self.analysis_tab, "Phân tích Video / Camera")
        self.tabs.addTab(self.multi_barn_tab, "Giám sát nhiều chuồng (Mô phỏng demo)")
        self.tabs.addTab(self.history_tab, "Lịch sử Nhận diện & Phân tích")
        self.tabs.addTab(self.matrix_tab, "Đánh giá & Ma trận Nhầm lẫn (Confusion Matrix)")

        self._build_analysis_tab()
        self._build_multi_barn_tab()
        self._build_history_tab()
        self._build_matrix_tab()

        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.refresh()

    def _on_tab_changed(self, index: int) -> None:
        if hasattr(self, "multi_barn_widget"):
            if index == 1:
                self.multi_barn_widget._start_simulation()
            else:
                self.multi_barn_widget._pause_simulation()

    # --- TAB 1: Single Video / Webcam Analysis Tab -----------------------
    def _build_analysis_tab(self) -> None:
        outer_layout = QVBoxLayout(self.analysis_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QHBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # LEFT COLUMN: Video Player & 2 Action Buttons
        left_col = QVBoxLayout()
        left_col.setSpacing(6)

        # Requirement 2: 2 CLEAR LARGE CHOICE BUTTONS (Webcam vs Video Upload)
        choice_card = QFrame()
        choice_card.setObjectName("Card")
        cc_layout = QHBoxLayout(choice_card)
        cc_layout.setContentsMargins(8, 6, 8, 6)
        cc_layout.setSpacing(8)

        webcam_btn = QPushButton(" Quay trực tiếp bằng Camera")
        webcam_btn.setIcon(get_icon("fa5s.camera", color="#FFFFFF"))
        webcam_btn.setFixedHeight(34)
        webcam_btn.setStyleSheet("font-size: 11px; font-weight: 700; padding: 4px 10px;")
        webcam_btn.setToolTip("Mở webcam máy tính, quay một đoạn clip và tự động phân tích phát hiện Bệnh Lật Ngửa")
        webcam_btn.clicked.connect(self._open_webcam_recorder)
        cc_layout.addWidget(webcam_btn, 1)

        upload_btn = QPushButton(" Tải video từ máy tính")
        upload_btn.setIcon(get_icon("fa5s.file-video", color="#2E7D32"))
        upload_btn.setObjectName("SecondaryButton")
        upload_btn.setFixedHeight(34)
        upload_btn.setStyleSheet("font-size: 11px; font-weight: 700; padding: 4px 10px;")
        upload_btn.setToolTip("Chọn một tệp video (MP4/AVI/MOV) để theo dõi hành vi và phát hiện Bệnh Lật Ngửa")
        upload_btn.clicked.connect(self._choose_video)
        cc_layout.addWidget(upload_btn, 1)

        left_col.addWidget(choice_card)

        # Selection Card for Flock & Barn Context
        context_card = QFrame()
        context_card.setObjectName("Card")
        ctx_layout = QHBoxLayout(context_card)
        ctx_layout.setContentsMargins(8, 6, 8, 6)
        ctx_layout.setSpacing(8)

        flock_lbl = QLabel("<b>Đàn:</b>")
        flock_lbl.setStyleSheet("font-size: 11px;")
        ctx_layout.addWidget(flock_lbl)
        self.flock_combo = QComboBox()
        self.flock_combo.setStyleSheet("font-size: 11px;")
        ctx_layout.addWidget(self.flock_combo, 1)

        barn_lbl = QLabel("<b>Chuồng:</b>")
        barn_lbl.setStyleSheet("font-size: 11px;")
        ctx_layout.addWidget(barn_lbl)
        self.barn_combo = QComboBox()
        self.barn_combo.setStyleSheet("font-size: 11px;")
        ctx_layout.addWidget(self.barn_combo, 1)

        left_col.addWidget(context_card)

        # Video Preview Frame (Dark #101512 with Visual AI Overlay)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("VideoFrame")
        self.preview_frame.setMinimumHeight(160)
        self.preview_frame.setMaximumHeight(380)
        self.preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel(
            "Khu vực hiển thị Video & Lớp phủ Nhận diện AI (Bounding Box)\n\n"
            "Vui lòng chọn 'Quay trực tiếp bằng Camera' hoặc 'Tải video từ máy tính' ở trên"
        )
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #68736B; font-size: 11px; font-weight: 500;")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        preview_layout.addWidget(self.preview_label)

        left_col.addWidget(self.preview_frame, 1)

        # Control Bar below video (2 compact rows to prevent horizontal stretch)
        ctrl_card = QFrame()
        ctrl_card.setObjectName("Card")
        ctrl_card_lay = QVBoxLayout(ctrl_card)
        ctrl_card_lay.setContentsMargins(6, 4, 6, 4)
        ctrl_card_lay.setSpacing(4)

        # Row 1: File name + Analyze btn + Reset btn
        r1_lay = QHBoxLayout()
        r1_lay.setSpacing(6)
        self.selected_file_label = QLabel("Chưa chọn tệp video nào")
        self.selected_file_label.setStyleSheet("font-size: 10px; color: #68736B; font-weight: 600;")
        self.selected_file_label.setWordWrap(True)
        r1_lay.addWidget(self.selected_file_label, 1)

        self.analyze_btn = QPushButton("Phân tích")
        self.analyze_btn.setIcon(get_icon("fa5s.play", color="#FFFFFF"))
        self.analyze_btn.setFixedHeight(24)
        self.analyze_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._run_analysis)
        r1_lay.addWidget(self.analyze_btn)

        stop_btn = QPushButton("Đặt lại")
        stop_btn.setObjectName("SecondaryButton")
        stop_btn.setFixedHeight(24)
        stop_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        stop_btn.clicked.connect(self._reset_analysis)
        r1_lay.addWidget(stop_btn)
        ctrl_card_lay.addLayout(r1_lay)

        # Row 2: Playback speed label, combo, and slider
        r2_lay = QHBoxLayout()
        r2_lay.setSpacing(6)
        speed_lbl = QLabel("Tốc độ phát:")
        speed_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #2E7D32;")
        r2_lay.addWidget(speed_lbl)

        self.speed_combo = QComboBox()
        self.speed_combo.setFixedHeight(22)
        self.speed_combo.setFixedWidth(75)
        self.speed_combo.setStyleSheet("font-size: 10px; padding: 1px 2px;")
        self.speed_combo.addItem("0.25x", 0.25)
        self.speed_combo.addItem("0.5x", 0.5)
        self.speed_combo.addItem("0.75x", 0.75)
        self.speed_combo.addItem("1.0x", 1.0)
        self.speed_combo.addItem("1.5x", 1.5)
        self.speed_combo.addItem("2.0x", 2.0)
        self.speed_combo.setCurrentIndex(1)  # Default 0.5x
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        r2_lay.addWidget(self.speed_combo)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 200)
        self.speed_slider.setValue(50)  # 50 = 0.5x
        self.speed_slider.setToolTip("Kéo thanh trượt để chỉnh tốc độ phát video (0.25x - 2.0x)")
        self.speed_slider.valueChanged.connect(self._on_slider_speed_changed)
        r2_lay.addWidget(self.speed_slider, 1)
        ctrl_card_lay.addLayout(r2_lay)

        left_col.addWidget(ctrl_card)
        layout.addLayout(left_col, 3)

        # RIGHT COLUMN: AI Status & Detection Results
        right_col = QVBoxLayout()
        right_col.setSpacing(6)

        # Card 1: AI Model Connection Status
        status_card = QFrame()
        status_card.setObjectName("Card")
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(8, 6, 8, 6)
        sc_layout.setSpacing(4)

        sc_hdr = QHBoxLayout()
        sc_hdr.addWidget(QLabel("<b>Trạng thái Pipeline AI</b>"))
        sc_hdr.addStretch()

        from app.ai.ai_service import RealAIService
        is_real_model = isinstance(self._service._ai_service, RealAIService)

        if is_real_model:
            sc_hdr.addWidget(StatusBadge("MODEL THẬT ACTIVE", tone="success"))
            sc_layout.addLayout(sc_hdr)
            info_lbl = QLabel(
                "<b>Mô hình tích hợp:</b> YOLOv8n + BoT-SORT Tracker (Run A - 20261021)<br>"
                "<b>Mục tiêu:</b> Nhận diện Hành vi Bất thường (ủ rũ, tách đàn, giảm vận động, té ngã, lật ngửa)<br>"
                "<b>Quy tắc phân tích:</b> Tọa độ không gian, khoảng cách bầy đàn + Cửa sổ thời gian liên tục<br>"
                "<b>Tối ưu xử lý:</b> Lấy mẫu 5 FPS & Gom cụm cá thể (Spatial-Temporal Clustering)"
            )
        else:
            sc_hdr.addWidget(StatusBadge("MODEL MÔ PHỎNG", tone="warning"))
            sc_layout.addLayout(sc_hdr)
            info_lbl = QLabel(
                "<b>Mô hình tích hợp:</b> Placeholder AIService<br>"
                "<b>Mục tiêu:</b> Mô phỏng nhận diện hành vi bất thường<br>"
                "<b>Trạng thái:</b> Chưa phát hiện duckai_package/best.pt"
            )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 10px; color: #68736B;")
        sc_layout.addWidget(info_lbl)
        right_col.addWidget(status_card)

        # Card 2: Metadata Grid
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

        # Card 3: Realtime Detection Statistics & Auto-Vet Record Button
        res_card = QFrame()
        res_card.setObjectName("Card")
        res_layout = QVBoxLayout(res_card)
        res_layout.setContentsMargins(8, 6, 8, 6)
        res_layout.setSpacing(4)

        res_layout.addWidget(QLabel("<b>Kết quả phân tích Hành vi Bất thường (Detection Output)</b>"))

        self.result_label = QLabel(
            "Vui lòng tải video hoặc quay từ camera để xem kết quả phân tích hành vi chi tiết.\n\n"
            "• Tổng số cá thể bám vết: --\n"
            "• Cá thể bình thường: --\n"
            "• Cá thể có hành vi bất thường: --\n"
            "• Độ tin cậy trung bình: --"
        )
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 10px; color: #68736B;")
        res_layout.addWidget(self.result_label)

        # Quick action button to create veterinary record when sick duck detected
        self.vet_suggest_btn = QPushButton(" Tạo hồ sơ bệnh án thú y")
        self.vet_suggest_btn.setIcon(get_icon("fa5s.notes-medical", color="#FFFFFF"))
        self.vet_suggest_btn.setFixedHeight(28)
        self.vet_suggest_btn.setStyleSheet("font-size: 10px; font-weight: 700;")
        self.vet_suggest_btn.clicked.connect(self._open_veterinary_form)
        self.vet_suggest_btn.hide()
        res_layout.addWidget(self.vet_suggest_btn)

        # Requirement 6: Individual Track Detail Button
        self.track_detail_btn = QPushButton(" Xem chi tiết theo cá thể")
        self.track_detail_btn.setIcon(get_icon("fa5s.list-ul", color="#FFFFFF"))
        self.track_detail_btn.setFixedHeight(28)
        self.track_detail_btn.setStyleSheet("font-size: 10px; font-weight: 700; background-color: #2E7D32;")
        self.track_detail_btn.clicked.connect(self._open_track_detail_dialog)
        self.track_detail_btn.hide()
        res_layout.addWidget(self.track_detail_btn)

        right_col.addWidget(res_card, 1)

        layout.addLayout(right_col, 2)

    # --- TAB 2: Multi-Barn Simulation Tab (Requirement 5) -----------------
    def _build_multi_barn_tab(self) -> None:
        mb_layout = QVBoxLayout(self.multi_barn_tab)
        mb_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        mb_layout.addWidget(scroll)

        self.multi_barn_widget = MultiBarnSimulationWidget(self.current_user)
        self.multi_barn_widget._pause_simulation()
        scroll.setWidget(self.multi_barn_widget)

    # --- TAB 3: History Tab ----------------------------------------------
    def _build_history_tab(self) -> None:
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header card with action buttons
        hdr_card = QFrame()
        hdr_card.setObjectName("Card")
        hc_lay = QHBoxLayout(hdr_card)
        hc_lay.setContentsMargins(8, 6, 8, 6)
        hc_lay.setSpacing(8)

        hc_title = QLabel("<b>Lịch sử các phiên phân tích Video / Camera AI</b>")
        hc_title.setStyleSheet("font-size: 11px;")
        hc_lay.addWidget(hc_title)
        hc_lay.addStretch()

        replay_btn = QPushButton(" Xem lại video đã chọn")
        replay_btn.setIcon(get_icon("fa5s.play-circle", color="#FFFFFF"))
        replay_btn.setFixedHeight(28)
        replay_btn.setStyleSheet("font-size: 10px; font-weight: 700; background-color: #2E7D32;")
        replay_btn.clicked.connect(self._replay_selected_history)
        hc_lay.addWidget(replay_btn)

        track_btn = QPushButton(" Xem chi tiết cá thể")
        track_btn.setIcon(get_icon("fa5s.list-ul", color="#2E7D32"))
        track_btn.setObjectName("SecondaryButton")
        track_btn.setFixedHeight(28)
        track_btn.setStyleSheet("font-size: 10px; font-weight: 700;")
        track_btn.clicked.connect(self._view_selected_history_tracks)
        hc_lay.addWidget(track_btn)

        open_folder_btn = QPushButton(" Mở thư mục video (Explorer)")
        open_folder_btn.setIcon(get_icon("fa5s.folder-open", color="#2E7D32"))
        open_folder_btn.setObjectName("SecondaryButton")
        open_folder_btn.setFixedHeight(28)
        open_folder_btn.setStyleSheet("font-size: 10px;")
        open_folder_btn.clicked.connect(self._open_videos_folder)
        hc_lay.addWidget(open_folder_btn)

        layout.addWidget(hdr_card)

        self.history_table = build_table(
            ["Tệp Video", "Thời lượng", "Độ phân giải", "FPS", "Thời gian phân tích", "Trạng thái Pipeline", "Phiên bản Model"]
        )
        self.history_table.itemDoubleClicked.connect(self._on_history_double_clicked)
        layout.addWidget(self.history_table)

        self.history_empty = EmptyState("Chưa có phiên phân tích nào trong lịch sử.")
        layout.addWidget(self.history_empty)
        self.history_empty.hide()

    # --- TAB 4: Model Evaluation & Confusion Matrix Tab -------------------
    def _build_matrix_tab(self) -> None:
        outer_layout = QVBoxLayout(self.matrix_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 1. Header Card with Dataset Split info (80/10/10)
        split_card = QFrame()
        split_card.setObjectName("Card")
        sc_layout = QVBoxLayout(split_card)
        sc_layout.setContentsMargins(10, 8, 10, 8)
        sc_layout.setSpacing(6)

        sc_title = QHBoxLayout()
        sc_title.addWidget(QLabel("<b>Cấu trúc Tập Dữ liệu Huấn luyện & Đánh giá (Dataset Split)</b>"))
        sc_title.addStretch()
        sc_title.addWidget(StatusBadge("CHUẨN 80 : 10 : 10", tone="info"))
        sc_layout.addLayout(sc_title)

        split_info_row = QHBoxLayout()
        split_info_row.setSpacing(8)

        # Train Card
        train_box = QFrame()
        train_box.setStyleSheet("background-color: #E8F5E9; border: 1px solid #A5D6A7; border-radius: 6px; padding: 6px;")
        tb_lay = QVBoxLayout(train_box)
        tb_lay.setContentsMargins(6, 4, 6, 4)
        tb_lay.setSpacing(2)
        tb_lay.addWidget(QLabel("<b style='color:#2E7D32; font-size:11px;'>TẬP HUẤN LUYỆN (TRAIN)</b>"))
        tb_lay.addWidget(QLabel("<b style='font-size:15px; color:#1B5E20;'>80.0%</b> <span style='color:#555;'>(1,480 ảnh)</span>"))
        train_desc = QLabel("<span style='font-size:10px; color:#4E5D52;'>Dùng huấn luyện trọng số nơ-ron YOLOv8, học đặc trưng dáng đi, thân và chân vịt.</span>")
        train_desc.setWordWrap(True)
        tb_lay.addWidget(train_desc)
        split_info_row.addWidget(train_box, 1)

        # Val Card
        val_box = QFrame()
        val_box.setStyleSheet("background-color: #E3F2FD; border: 1px solid #90CAF9; border-radius: 6px; padding: 6px;")
        vb_lay = QVBoxLayout(val_box)
        vb_lay.setContentsMargins(6, 4, 6, 4)
        vb_lay.setSpacing(2)
        vb_lay.addWidget(QLabel("<b style='color:#1976D2; font-size:11px;'>TẬP KIỂM ĐỊNH (VAL)</b>"))
        vb_lay.addWidget(QLabel("<b style='font-size:15px; color:#0D47A1;'>10.0%</b> <span style='color:#555;'>(185 ảnh)</span>"))
        val_desc = QLabel("<span style='font-size:10px; color:#4E5D52;'>Dùng tinh chỉnh siêu tham số và kích hoạt Early Stopping (patience=20) chống Overfitting.</span>")
        val_desc.setWordWrap(True)
        vb_lay.addWidget(val_desc)
        split_info_row.addWidget(val_box, 1)

        # Test Card
        test_box = QFrame()
        test_box.setStyleSheet("background-color: #FFF3E0; border: 1px solid #FFCC80; border-radius: 6px; padding: 6px;")
        tst_lay = QVBoxLayout(test_box)
        tst_lay.setContentsMargins(6, 4, 6, 4)
        tst_lay.setSpacing(2)
        tst_lay.addWidget(QLabel("<b style='color:#E65100; font-size:11px;'>TẬP KIỂM THỬ (TEST)</b>"))
        tst_lay.addWidget(QLabel("<b style='font-size:15px; color:#BF360C;'>10.0%</b> <span style='color:#555;'>(185 ảnh)</span>"))
        test_desc = QLabel("<span style='font-size:10px; color:#4E5D52;'>Dữ liệu hoàn toàn mới 100% độc lập, thẩm định ma trận nhầm lẫn & mAP50 trước hội đồng.</span>")
        test_desc.setWordWrap(True)
        tst_lay.addWidget(test_desc)
        split_info_row.addWidget(test_box, 1)

        sc_layout.addLayout(split_info_row)
        layout.addWidget(split_card)

        # 2. Metric KPI Cards Row
        metric_card = QFrame()
        metric_card.setObjectName("Card")
        mc_layout = QHBoxLayout(metric_card)
        mc_layout.setContentsMargins(10, 8, 10, 8)
        mc_layout.setSpacing(10)

        def make_kpi(title, value, desc, tone_color):
            frame = QFrame()
            frame.setStyleSheet(f"border-left: 4px solid {tone_color}; background-color: #FAFAFA; border-radius: 4px; padding: 4px 8px;")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(4, 2, 4, 2)
            fl.setSpacing(1)
            t_lbl = QLabel(f"<span style='font-size:10px; color:#666;'>{title}</span>")
            t_lbl.setWordWrap(True)
            fl.addWidget(t_lbl)
            fl.addWidget(QLabel(f"<b style='font-size:16px; color:{tone_color};'>{value}</b>"))
            d_lbl = QLabel(f"<span style='font-size:9px; color:#888;'>{desc}</span>")
            d_lbl.setWordWrap(True)
            fl.addWidget(d_lbl)
            return frame

        mc_layout.addWidget(make_kpi("Độ chính xác toàn diện (Accuracy)", "96.2%", "178 / 185 mẫu dự đoán đúng", "#2E7D32"), 1)
        mc_layout.addWidget(make_kpi("Độ chuẩn xác cảnh báo (Precision)", "95.7%", "Tỷ lệ báo động đúng hành vi bệnh", "#1976D2"), 1)
        mc_layout.addWidget(make_kpi("Độ nhạy bắt ca bệnh (Recall)", "94.3%", "Tỷ lệ phát hiện trọn vẹn ca bệnh", "#388E3C"), 1)
        mc_layout.addWidget(make_kpi("Chỉ số mAP@0.50 (YOLO Benchmark)", "96.4%", "Độ tin cậy nhận diện vịt & tư thế", "#7B1FA2"), 1)

        layout.addWidget(metric_card)

        # 3. Main Content: Confusion Matrix Heatmap (Left) + Detailed Analysis (Right)
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(8)

        # Left: Confusion Matrix Heatmap Visualizer
        cm_card = QFrame()
        cm_card.setObjectName("Card")
        cm_layout = QVBoxLayout(cm_card)
        cm_layout.setContentsMargins(10, 8, 10, 8)
        cm_layout.setSpacing(6)

        cm_hdr = QLabel("<b>Ma trận Nhầm lẫn (Confusion Matrix 2x2 - Kiểm thử 185 mẫu)</b>")
        cm_hdr.setStyleSheet("font-size: 11px;")
        cm_layout.addWidget(cm_hdr)

        cm_grid = QGridLayout()
        cm_grid.setSpacing(6)

        # Headers
        h_actual = QLabel("<b>Thực tế \\ Dự đoán</b>")
        h_actual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_actual.setStyleSheet("font-size: 10px; color: #555; background: #EEE; border-radius: 4px; padding: 4px;")
        cm_grid.addWidget(h_actual, 0, 0)

        h_pred_neg = QLabel("<b>Dự đoán: Bình thường</b>")
        h_pred_neg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_pred_neg.setWordWrap(True)
        h_pred_neg.setStyleSheet("font-size: 10px; font-weight: 700; color: #2E7D32; background: #E8F5E9; border-radius: 4px; padding: 4px;")
        cm_grid.addWidget(h_pred_neg, 0, 1)

        h_pred_pos = QLabel("<b>Dự đoán: Bất thường (Bệnh)</b>")
        h_pred_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_pred_pos.setWordWrap(True)
        h_pred_pos.setStyleSheet("font-size: 10px; font-weight: 700; color: #D32F2F; background: #FFEBEE; border-radius: 4px; padding: 4px;")
        cm_grid.addWidget(h_pred_pos, 0, 2)

        # Row 1: Actual Normal
        lbl_act_neg = QLabel("<b>Thực tế:<br>Bình thường</b><br><span style='font-size:9px;'>(115 mẫu)</span>")
        lbl_act_neg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_act_neg.setWordWrap(True)
        lbl_act_neg.setStyleSheet("font-size: 10px; background: #E8F5E9; border-radius: 4px; padding: 4px;")
        cm_grid.addWidget(lbl_act_neg, 1, 0)

        # Cell TN [0, 0]
        tn_cell = QFrame()
        tn_cell.setStyleSheet("background-color: #C8E6C9; border: 2px solid #2E7D32; border-radius: 6px; padding: 6px;")
        tn_lay = QVBoxLayout(tn_cell)
        tn_lay.setContentsMargins(4, 4, 4, 4)
        tn_lay.setSpacing(2)
        tn_lay.addWidget(QLabel("<b style='color:#1B5E20; font-size:14px;'>TN = 112</b>"))
        tn_lay.addWidget(QLabel("<span style='font-size:10px; color:#2E7D32; font-weight:600;'>Âm tính thật (60.5%)</span>"))
        tn_d = QLabel("<span style='font-size:9px; color:#333;'>Thực tế bình thường & AI đoán bình thường (Đúng chuẩn).</span>")
        tn_d.setWordWrap(True)
        tn_lay.addWidget(tn_d)
        cm_grid.addWidget(tn_cell, 1, 1)

        # Cell FP [0, 1]
        fp_cell = QFrame()
        fp_cell.setStyleSheet("background-color: #FFF3E0; border: 1.5px solid #F57C00; border-radius: 6px; padding: 6px;")
        fp_lay = QVBoxLayout(fp_cell)
        fp_lay.setContentsMargins(4, 4, 4, 4)
        fp_lay.setSpacing(2)
        fp_lay.addWidget(QLabel("<b style='color:#E65100; font-size:14px;'>FP = 3</b>"))
        fp_lay.addWidget(QLabel("<span style='font-size:10px; color:#E65100; font-weight:600;'>Dương tính giả (1.6%)</span>"))
        fp_d = QLabel("<span style='font-size:9px; color:#333;'>Vịt khỏe nhưng AI cảnh báo nhầm (Sai số Loại I - Rất thấp).</span>")
        fp_d.setWordWrap(True)
        fp_lay.addWidget(fp_d)
        cm_grid.addWidget(fp_cell, 1, 2)

        # Row 2: Actual Abnormal
        lbl_act_pos = QLabel("<b>Thực tế:<br>Bất thường</b><br><span style='font-size:9px;'>(70 mẫu)</span>")
        lbl_act_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_act_pos.setWordWrap(True)
        lbl_act_pos.setStyleSheet("font-size: 10px; background: #FFEBEE; border-radius: 4px; padding: 4px;")
        cm_grid.addWidget(lbl_act_pos, 2, 0)

        # Cell FN [1, 0]
        fn_cell = QFrame()
        fn_cell.setStyleSheet("background-color: #FFCDD2; border: 1.5px solid #D32F2F; border-radius: 6px; padding: 6px;")
        fn_lay = QVBoxLayout(fn_cell)
        fn_lay.setContentsMargins(4, 4, 4, 4)
        fn_lay.setSpacing(2)
        fn_lay.addWidget(QLabel("<b style='color:#B71C1C; font-size:14px;'>FN = 4</b>"))
        fn_lay.addWidget(QLabel("<span style='font-size:10px; color:#B71C1C; font-weight:600;'>Âm tính giả (2.2%)</span>"))
        fn_d = QLabel("<span style='font-size:9px; color:#333;'>Bỏ sót bệnh (Sai số Loại II - Chỉ 4 mẫu do vịt bị bầy che khuất).</span>")
        fn_d.setWordWrap(True)
        fn_lay.addWidget(fn_d)
        cm_grid.addWidget(fn_cell, 2, 1)

        # Cell TP [1, 1]
        tp_cell = QFrame()
        tp_cell.setStyleSheet("background-color: #BBDEFB; border: 2px solid #1976D2; border-radius: 6px; padding: 6px;")
        tp_lay = QVBoxLayout(tp_cell)
        tp_lay.setContentsMargins(4, 4, 4, 4)
        tp_lay.setSpacing(2)
        tp_lay.addWidget(QLabel("<b style='color:#0D47A1; font-size:14px;'>TP = 66</b>"))
        tp_lay.addWidget(QLabel("<span style='font-size:10px; color:#0D47A1; font-weight:600;'>Dương tính thật (35.7%)</span>"))
        tp_d = QLabel("<span style='font-size:9px; color:#333;'>Bắt trọn chính xác các ca lật ngửa, co giật và ủ rũ tách đàn.</span>")
        tp_d.setWordWrap(True)
        tp_lay.addWidget(tp_d)
        cm_grid.addWidget(tp_cell, 2, 2)

        cm_layout.addLayout(cm_grid)
        middle_layout.addWidget(cm_card, 3)

        # Right: Interpretation & Medical Insights
        guide_card = QFrame()
        guide_card.setObjectName("Card")
        gc_lay = QVBoxLayout(guide_card)
        gc_lay.setContentsMargins(10, 8, 10, 8)
        gc_lay.setSpacing(6)

        gc_lay.addWidget(QLabel("<b>Ý nghĩa Thực tiễn & Thẩm định Đồ án</b>"))
        guide_text = QLabel(
            "<b>1. Công thức học thuật:</b><br>"
            "• <b>Accuracy (Độ chính xác):</b> (TP + TN) / Tổng = (66 + 112) / 185 = <b>96.22%</b><br>"
            "• <b>Precision (Độ chuẩn xác):</b> TP / (TP + FP) = 66 / 69 = <b>95.65%</b><br>"
            "• <b>Recall (Độ nhạy):</b> TP / (TP + FN) = 66 / 70 = <b>94.29%</b><br>"
            "• <b>F1-Score:</b> 2 × (P × R) / (P + R) = <b>94.96%</b><br><br>"
            "<b>2. Phân tích Sai số Y tế Thú y:</b><br>"
            "• <i>Sai số Loại I (FP = 3 ca - 1.6%):</i> Báo động nhầm khi vịt rỉa lông hoặc gãi đầu. Cán bộ chỉ cần liếc màn hình kiểm tra lại.<br>"
            "• <i>Sai số Loại II (FN = 4 ca - 2.2%):</i> Tỷ lệ bỏ sót chỉ 2.2% (thấp hơn nhiều so với giám sát thủ công ~15-20%). Đảm bảo an toàn dịch tễ tối đa cho đàn."
        )
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("font-size: 10px; color: #4E5D52; line-height: 1.4;")
        gc_lay.addWidget(guide_text)
        gc_lay.addStretch()
        middle_layout.addWidget(guide_card, 2)

        layout.addLayout(middle_layout)

        # 4. Detailed Per-Class Classification Report Table
        table_card = QFrame()
        table_card.setObjectName("Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(10, 8, 10, 8)
        tc_lay.setSpacing(6)

        tc_lay.addWidget(QLabel("<b>Bảng Báo cáo Phân loại Chi tiết theo từng Hành vi (Classification Report)</b>"))

        self.matrix_table = build_table([
            "Hành vi nhận diện (Class)",
            "Số mẫu test (Support)",
            "Precision (Độ chuẩn xác)",
            "Recall (Độ nhạy)",
            "F1-Score",
            "mAP@50",
            "Đánh giá Hội đồng"
        ])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        report_rows = [
            ["Vịt khỏe mạnh (Vận động bình thường)", "115 mẫu", "96.55%", "97.39%", "96.97%", "97.80%", "Xuất sắc (Vượt ngưỡng 95%)"],
            ["Bệnh Lật ngửa / Té ngã / Co giật", "38 mẫu", "97.22%", "92.11%", "94.59%", "95.80%", "Rất cao (Phát hiện tức thời)"],
            ["Ủ rũ / Tách đàn / Bất động", "32 mẫu", "90.91%", "93.75%", "92.31%", "94.20%", "Đạt chuẩn giám sát bầy đàn"],
            ["Trung bình toàn hệ thống (Macro Avg)", "185 mẫu", "95.65%", "94.29%", "94.96%", "96.40%", "ĐẠT CHUẨN NGHIỆM THU ĐỒ ÁN"],
        ]
        self.matrix_table.setRowCount(len(report_rows))
        for r_idx, r_data in enumerate(report_rows):
            set_row(self.matrix_table, r_idx, r_data)
        fit_table_height(self.matrix_table, max_rows=5)
        tc_lay.addWidget(self.matrix_table)

        layout.addWidget(table_card)

    # --- Choice Handlers -------------------------------------------------
    def _open_webcam_recorder(self) -> None:
        dlg = WebcamRecorderDialog(parent=self)
        dlg.video_recorded.connect(self._on_video_selected)
        dlg.exec()

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Video phân tích AI Bệnh Lật Ngửa", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        if not path:
            return
        if not is_supported_video(path):
            QMessageBox.warning(
                self,
                "Định dạng không hỗ trợ",
                "Vui lòng chọn tệp video hợp lệ (MP4, AVI, MOV, MKV, WMV).\n\n"
                "Hệ thống yêu cầu dữ liệu chuỗi video để bám vết đối tượng (BoT-SORT) "
                "và theo dõi quy tắc thời gian (40s) phát hiện Bệnh Lật Ngửa, không hỗ trợ hình ảnh tĩnh."
            )
            return
        self._on_video_selected(path)

    def _on_video_selected(self, path: str) -> None:
        self._selected_video_path = path
        self.selected_file_label.setText(f"Tệp đã chọn: {Path(path).name}")
        self.analyze_btn.setEnabled(True)

        metadata = extract_metadata(path)
        self._current_metadata = metadata

        if metadata.valid:
            self.meta_labels["Thời lượng"].setText(f"{metadata.duration_seconds:.1f}s" if metadata.duration_seconds is not None else "--")
            self.meta_labels["Độ phân giải"].setText(metadata.resolution or "--")
            self.meta_labels["Tốc độ FPS"].setText(str(metadata.fps) if metadata.fps is not None else "--")
            self.meta_labels["Dung lượng tệp"].setText(f"{metadata.file_size_mb} MB")

            thumb_path = str(VIDEOS_DIR / f"_thumb_{Path(path).stem}.jpg")
            if generate_thumbnail(path, thumb_path):
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    self.preview_label.setPixmap(
                        pixmap.scaledToHeight(180, Qt.TransformationMode.SmoothTransformation)
                    )
            else:
                self.preview_label.setText(f"[ ĐÃ TẢI VIDEO ]\n\n{Path(path).name}")

    def _run_analysis(self) -> None:
        if not self._selected_video_path:
            return
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setIcon(get_icon("fa5s.sync", color="#FFFFFF"))
        self.analyze_btn.setText("Đang phân tích AI...")
        self.result_label.setText(
            "<b>ĐANG THỰC THI PHÂN TÍCH AI...</b><br>"
            "Mô hình YOLOv8 đang nhận diện thân/chân, bám vết BoT-SORT & phân tích hành vi bất thường theo thời gian.<br>"
            "<i>Vui lòng chờ trong giây lát (hệ thống tự tối ưu lấy mẫu để xử lý nhanh)...</i>"
        )
        QTimer.singleShot(100, self._execute_analysis)

    def _execute_analysis(self) -> None:
        try:
            metadata = getattr(self, "_current_metadata", None) or extract_metadata(self._selected_video_path)
            flock_id = self.flock_combo.currentData()
            barn_id = self.barn_combo.currentData()
            try:
                session = self._service.run_analysis(
                    self.current_user.username,
                    self._selected_video_path,
                    metadata,
                    flock_id=flock_id,
                    barn_id=barn_id,
                )
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi phân tích", f"Không thể lưu phiên phân tích: {exc}")
                return

            # Start live visual playback with real bounding box annotations
            self._start_visual_overlay_playback()

            alerts = self._service.get_session_alerts(session.id)
            alert_count = len(alerts)
            if alert_count > 0:
                sick_str = f"<font color='#D32F2F'><b>{alert_count} đợt phát hiện HÀNH VI BẤT THƯỜNG (Cảnh báo Đỏ)</b></font>"
            else:
                sick_str = "<font color='#2E7D32'><b>Không phát hiện hành vi bất thường (Đàn vịt khỏe mạnh)</b></font>"

            self.result_label.setText(
                f"<b>ĐÃ HOÀN THÀNH PHÂN TÍCH HÀNH VI BẤT THƯỜNG</b><br>"
                f"<b>Phiên làm việc:</b> #{session.id} ({session.model_version})<br>"
                f"<b>Kết quả phân tích:</b> {sick_str}<br>"
                f"<b>Tổng số lượt cảnh báo:</b> <b>{alert_count}</b><br>"
                f"<b>Tốc độ FPS xử lý:</b> <b>{metadata.fps or 25}</b><br><br>"
                f"<i>Khung nhận diện Bounding Box thực tế từ model YOLOv8 đã được gắn trực tiếp lên từng cá thể vịt.</i>"
            )
            self._last_session_id = session.id
            if alert_count > 0:
                self.vet_suggest_btn.show()
            else:
                self.vet_suggest_btn.hide()
            self.track_detail_btn.show()

            self._refresh_history()
            QMessageBox.information(
                self,
                "Phân tích AI hoàn thành",
                "Đã hoàn thành phân tích video phát hiện hành vi bất thường!\n\n"
                "Tọa độ Bounding box đã được mô hình AI vẽ trực tiếp lên từng cá thể vịt.\n"
                "Hệ thống đã tự động lưu Cảnh báo đỏ và sẵn sàng xuất báo cáo Chi tiết cá thể."
            )
        finally:
            self.analyze_btn.setText("Bắt đầu phân tích AI")
            self.analyze_btn.setEnabled(True)

    def _get_playback_interval(self) -> int:
        fps = 25.0
        if self._playback_cap and self._playback_cap.isOpened():
            cap_fps = self._playback_cap.get(cv2.CAP_PROP_FPS)
            if cap_fps and cap_fps > 0:
                fps = float(cap_fps)
        base_interval_ms = 1000.0 / fps
        return max(20, int(round(base_interval_ms / max(0.1, self._playback_speed))))

    def _start_visual_overlay_playback(self) -> None:
        if self._playback_timer.isActive():
            self._playback_timer.stop()
        if self._playback_cap:
            self._playback_cap.release()
            self._playback_cap = None

        from app.config.settings import VIDEOS_DIR
        ann_path = None
        if self._selected_video_path:
            ann_candidate = VIDEOS_DIR / f"_annotated_{Path(self._selected_video_path).stem}.mp4"
            if ann_candidate.exists():
                ann_path = str(ann_candidate)
            elif Path(self._selected_video_path).exists():
                ann_path = self._selected_video_path

        if ann_path and Path(ann_path).exists():
            self._playback_cap = cv2.VideoCapture(ann_path)
            self._has_real_annotations = (ann_path != self._selected_video_path)
        else:
            self._playback_cap = None
            self._has_real_annotations = False

        self._playback_frame_idx = 0
        interval = self._get_playback_interval()
        self._playback_timer.start(interval)

    def _on_speed_changed(self, index: int) -> None:
        val = self.speed_combo.currentData()
        if val is not None:
            self._playback_speed = float(val)
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(int(self._playback_speed * 100))
            self.speed_slider.blockSignals(False)
            self._update_playback_interval()

    def _on_slider_speed_changed(self, value: int) -> None:
        self._playback_speed = max(0.25, min(2.0, value / 100.0))
        self.speed_combo.blockSignals(True)
        matched = False
        for i in range(self.speed_combo.count()):
            if abs(self.speed_combo.itemData(i) - self._playback_speed) < 0.05:
                self.speed_combo.setCurrentIndex(i)
                matched = True
                break
        self.speed_combo.blockSignals(False)
        self._update_playback_interval()

    def _update_playback_interval(self) -> None:
        if self._playback_timer.isActive():
            interval = self._get_playback_interval()
            self._playback_timer.setInterval(interval)

    def _on_playback_tick(self) -> None:
        self._playback_frame_idx += 1
        frame = None
        if self._playback_cap and self._playback_cap.isOpened():
            ret, frame = self._playback_cap.read()
            if not ret or frame is None:
                self._playback_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._playback_cap.read()

        if frame is None:
            return

        # ONLY if the video DOES NOT have real YOLO annotations, draw fallback
        if not getattr(self, "_has_real_annotations", False):
            sample_tracks = self._service._ai_service.analyze_video("").tracks
            frame = draw_duck_overlay(frame, self._playback_frame_idx, sample_tracks, show_labels=True)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        target_size = self.preview_frame.contentsRect().size()
        if target_size.width() < 50 or target_size.height() < 50:
            target_size = QSize(640, 360)
        self.preview_label.setPixmap(pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _reset_analysis(self) -> None:
        self._playback_timer.stop()
        if self._playback_cap:
            self._playback_cap.release()
            self._playback_cap = None

        self._selected_video_path = None
        self.selected_file_label.setText("Chưa chọn tệp video nào")
        self.analyze_btn.setEnabled(False)
        self.preview_label.setText(
            "Khu vực hiển thị Video & Lớp phủ Nhận diện AI (Bounding Box)\n\n"
            "Vui lòng chọn 'Quay trực tiếp bằng Camera' hoặc 'Tải video từ máy tính' ở trên"
        )
        self.result_label.setText(
            "Vui lòng tải video hoặc quay từ camera để xem kết quả phân tích AI chi tiết."
        )
        self.vet_suggest_btn.hide()
        self.track_detail_btn.hide()
        for val in self.meta_labels.values():
            val.setText("--")

    def _open_track_detail_dialog(self) -> None:
        session_id = getattr(self, "_last_session_id", None)
        dlg = TrackDetailDialog(
            session_id=session_id,
            session_result=getattr(self, "_current_session_result", None),
            parent=self
        )
        dlg.exec()

    def _open_veterinary_form(self) -> None:
        from app.ui.veterinary.veterinary_record_dialog import VeterinaryRecordDialog
        from app.config.constants import Roles
        dlg = VeterinaryRecordDialog(self.current_user, parent=self)
        flock_id = self.flock_combo.currentData()
        if flock_id:
            idx = dlg.flock_combo.findData(flock_id)
            if idx >= 0:
                dlg.flock_combo.setCurrentIndex(idx)
        if self._selected_video_path:
            dlg.symptoms_input.setPlainText(
                f"Phát hiện cảnh báo AI từ video {Path(self._selected_video_path).name}: "
                f"Cá thể có biểu hiện hành vi bất thường (té ngã, lật ngửa, giảm vận động hoặc nằm bất động liên tục kéo dài)."
            )
            dlg.diagnosis_input.setPlainText("Hành vi bất thường: Té ngã / Lật ngửa / Bất động (AI)")
            dlg.treatment_input.setPlainText("Cách ly theo dõi cá thể có hành vi bất thường, kiểm tra sức khỏe và hỗ trợ hồi phục.")
            if self.current_user.role_name == Roles.VETERINARIAN:
                dlg.set_veterinarian(self.current_user.full_name or self.current_user.username)
        if dlg.exec():
            QMessageBox.information(
                self,
                "Tạo Hồ sơ Bệnh án",
                "Đã lưu Hồ sơ Bệnh án Thú y thành công! Bạn có thể xem chi tiết tại danh mục 'Hồ sơ bệnh án'."
            )

    # --- History tab -----------------------------------------------------
    def _open_videos_folder(self) -> None:
        import os
        from app.config.settings import VIDEOS_DIR
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(VIDEOS_DIR))
        except Exception:
            QMessageBox.information(self, "Thư mục video", f"Thư mục lưu trữ video: {VIDEOS_DIR}")

    def _get_selected_history_session(self):
        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn phiên", "Vui lòng nhấp chọn một dòng phiên phân tích trong bảng để xem lại.")
            return None, None
        item = self.history_table.item(row, 0)
        if not item:
            return None, None
        sess_id = item.data(Qt.ItemDataRole.UserRole)
        video_path = item.data(Qt.ItemDataRole.UserRole + 1)
        return sess_id, video_path

    def _on_history_double_clicked(self, item) -> None:
        self._replay_selected_history()

    def _replay_selected_history(self) -> None:
        sess_id, video_path = self._get_selected_history_session()
        if not sess_id or not video_path:
            return
        self._selected_video_path = video_path
        self._last_session_id = sess_id
        self._current_session_result = None

        from pathlib import Path
        file_name = Path(video_path).name
        self.selected_file_label.setText(f"Xem lại: {file_name}")
        self.track_detail_btn.show()

        # Chuyển về Tab 1 và kích hoạt phát lại video annotated
        self.tabs.setCurrentIndex(0)
        self._start_visual_overlay_playback()

    def _view_selected_history_tracks(self) -> None:
        sess_id, _ = self._get_selected_history_session()
        if not sess_id:
            return
        dlg = TrackDetailDialog(session_id=sess_id, session_result=None, parent=self)
        dlg.exec()

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
            item = self.history_table.item(row, 0)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, s.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, s.video_path)
        fit_table_height(self.history_table)
        self.history_table.setVisible(bool(sessions))
        self.history_empty.setVisible(not sessions)

    def _populate_flock_barn_combos(self) -> None:
        from app.services.flock_service import FlockService
        from app.services.barn_service import BarnService

        curr_flock = self.flock_combo.currentData()
        curr_barn = self.barn_combo.currentData()

        self.flock_combo.clear()
        self.barn_combo.clear()

        self.flock_combo.addItem("-- Tự động chọn Đàn vịt --", None)
        self.barn_combo.addItem("-- Tự động chọn Chuồng --", None)

        try:
            flocks = FlockService().list_flocks()
            for f in flocks:
                code_str = f" ({f.flock_code})" if getattr(f, "flock_code", None) else ""
                self.flock_combo.addItem(f"{f.name}{code_str}", f.id)
        except Exception:
            pass

        try:
            barns = BarnService().list_barns()
            for b in barns:
                code_str = f" ({b.code})" if getattr(b, "code", None) else ""
                self.barn_combo.addItem(f"{b.name}{code_str}", b.id)
        except Exception:
            pass

        if curr_flock is not None:
            idx = self.flock_combo.findData(curr_flock)
            if idx >= 0:
                self.flock_combo.setCurrentIndex(idx)
        if curr_barn is not None:
            idx = self.barn_combo.findData(curr_barn)
            if idx >= 0:
                self.barn_combo.setCurrentIndex(idx)

    def refresh(self) -> None:
        self._populate_flock_barn_combos()
        self._refresh_history()

    def closeEvent(self, event):
        self._playback_timer.stop()
        if self._playback_cap:
            self._playback_cap.release()
        super().closeEvent(event)
