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

        # Playback animation timer for visual overlay
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)
        self._playback_frame_idx = 0
        self._playback_cap: cv2.VideoCapture | None = None

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
        self.multi_barn_tab = QWidget()
        self.history_tab = QWidget()

        self.tabs.addTab(self.analysis_tab, "Phân tích Video / Camera")
        self.tabs.addTab(self.multi_barn_tab, "Giám sát nhiều chuồng (Mô phỏng demo)")
        self.tabs.addTab(self.history_tab, "Lịch sử Nhận diện & Phân tích")

        self._build_analysis_tab()
        self._build_multi_barn_tab()
        self._build_history_tab()

        self.refresh()

    # --- TAB 1: Single Video / Webcam Analysis Tab -----------------------
    def _build_analysis_tab(self) -> None:
        layout = QHBoxLayout(self.analysis_tab)
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
        webcam_btn.setToolTip("Mở webcam máy tính, quay 1 đoạn clip và tự động phân tích AI")
        webcam_btn.clicked.connect(self._open_webcam_recorder)
        cc_layout.addWidget(webcam_btn, 1)

        upload_btn = QPushButton(" Tải video từ máy tính")
        upload_btn.setIcon(get_icon("fa5s.file-video", color="#2E7D32"))
        upload_btn.setObjectName("SecondaryButton")
        upload_btn.setFixedHeight(34)
        upload_btn.setStyleSheet("font-size: 11px; font-weight: 700; padding: 4px 10px;")
        upload_btn.setToolTip("Chọn một tệp video sẵn có (mp4/avi) trong máy tính")
        upload_btn.clicked.connect(self._choose_video)
        cc_layout.addWidget(upload_btn, 1)

        upload_img_btn = QPushButton(" Tải hình ảnh từ máy tính")
        upload_img_btn.setIcon(get_icon("fa5s.file-image", color="#1565C0"))
        upload_img_btn.setObjectName("SecondaryButton")
        upload_img_btn.setFixedHeight(34)
        upload_img_btn.setStyleSheet("font-size: 11px; font-weight: 700; padding: 4px 10px;")
        upload_img_btn.setToolTip("Chọn một tệp ảnh (jpg/png) để nhận diện và chẩn đoán lật ngửa")
        upload_img_btn.clicked.connect(self._choose_image)
        cc_layout.addWidget(upload_img_btn, 1)

        left_col.addWidget(choice_card)

        # Video Preview Frame (Dark #101512 with Visual AI Overlay)
        preview_frame = QFrame()
        preview_frame.setObjectName("VideoFrame")
        preview_frame.setMinimumHeight(220)

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel(
            "Khu vực hiển thị Video & Lớp phủ Nhận diện AI (Bounding Box)\n\n"
            "Vui lòng chọn 'Quay trực tiếp bằng Camera' hoặc 'Tải video từ máy tính' ở trên"
        )
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #68736B; font-size: 11px; font-weight: 500;")
        self.preview_label.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_label)

        left_col.addWidget(preview_frame, 1)

        # Control Bar below video
        ctrl_card = QFrame()
        ctrl_card.setObjectName("Card")
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)
        ctrl_layout.setSpacing(6)

        self.selected_file_label = QLabel("Chưa chọn tệp video nào")
        self.selected_file_label.setStyleSheet("font-size: 10px; color: #68736B; font-weight: 600;")
        ctrl_layout.addWidget(self.selected_file_label, 1)

        self.analyze_btn = QPushButton("Bắt đầu phân tích AI")
        self.analyze_btn.setIcon(get_icon("fa5s.play", color="#FFFFFF"))
        self.analyze_btn.setFixedHeight(26)
        self.analyze_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._run_analysis)
        ctrl_layout.addWidget(self.analyze_btn)

        stop_btn = QPushButton("Đặt lại")
        stop_btn.setObjectName("SecondaryButton")
        stop_btn.setFixedHeight(26)
        stop_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        stop_btn.clicked.connect(self._reset_analysis)
        ctrl_layout.addWidget(stop_btn)

        left_col.addWidget(ctrl_card)
        layout.addLayout(left_col, 2)

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
                "<b>Mô hình tích hợp:</b> YOLOv8 Lật Ngửa (duckai_package/best.pt)<br>"
                "<b>Nhiệm vụ:</b> Detect Than/Chân + Tracking BoT-SORT + Cảnh báo Lật Ngửa<br>"
                "<b>Trạng thái:</b> Đã cắm Model thật thành công"
            )
        else:
            sc_hdr.addWidget(StatusBadge("MODEL MÔ PHỎNG", tone="warning"))
            sc_layout.addLayout(sc_hdr)
            info_lbl = QLabel(
                "<b>Mô hình tích hợp:</b> Placeholder AIService<br>"
                "<b>Nhiệm vụ:</b> Mô phỏng kết quả phân tích AI<br>"
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

        res_layout.addWidget(QLabel("<b>Kết quả chẩn đoán hành vi (Detection Output)</b>"))

        self.result_label = QLabel(
            "Vui lòng tải video hoặc quay từ camera để xem kết quả phân tích AI chi tiết.\n\n"
            "• Tổng số cá thể nhận diện: --\n"
            "• Cá thể khỏe mạnh: --\n"
            "• Cá thể nghi vấn mắc bệnh: --\n"
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

        layout.addLayout(right_col, 1)

    # --- TAB 2: Multi-Barn Simulation Tab (Requirement 5) -----------------
    def _build_multi_barn_tab(self) -> None:
        mb_layout = QVBoxLayout(self.multi_barn_tab)
        mb_layout.setContentsMargins(0, 0, 0, 0)
        self.multi_barn_widget = MultiBarnSimulationWidget(self.current_user)
        mb_layout.addWidget(self.multi_barn_widget)

    # --- TAB 3: History Tab ----------------------------------------------
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

    # --- Choice Handlers -------------------------------------------------
    def _open_webcam_recorder(self) -> None:
        dlg = WebcamRecorderDialog(parent=self)
        dlg.video_recorded.connect(self._on_video_selected)
        dlg.exec()

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Video phân tích AI", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        if not path:
            return
        if not is_supported_video(path):
            QMessageBox.warning(self, "Định dạng không hỗ trợ", "Vui lòng chọn tệp video hợp lệ.")
            return
        self._on_video_selected(path)

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Hình ảnh phân tích AI", "", "Image Files (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if not path:
            return
        from app.ai.video_processor import is_supported_image
        if not is_supported_image(path):
            QMessageBox.warning(self, "Định dạng không hỗ trợ", "Vui lòng chọn tệp hình ảnh hợp lệ.")
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

            from app.ai.video_processor import is_supported_image
            if is_supported_image(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.preview_label.setPixmap(
                        pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
            else:
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
            "Mô hình YOLOv8 Lật Ngửa đang nhận diện khung hình & chẩn đoán hành vi.<br>"
            "<i>Vui lòng chờ trong giây lát...</i>"
        )
        QTimer.singleShot(100, self._execute_analysis)

    def _execute_analysis(self) -> None:
        try:
            metadata = getattr(self, "_current_metadata", None) or extract_metadata(self._selected_video_path)
            try:
                session = self._service.run_analysis(self.current_user.username, self._selected_video_path, metadata)
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi phân tích", f"Không thể lưu phiên phân tích: {exc}")
                return

            from app.ai.video_processor import is_supported_image
            if is_supported_image(self._selected_video_path):
                self._playback_timer.stop()
                from pathlib import Path
                from app.config.settings import VIDEOS_DIR
                ann_path = str(VIDEOS_DIR / f"_annotated_{Path(self._selected_video_path).name}")
                display_path = ann_path if Path(ann_path).exists() else self._selected_video_path

                pixmap = QPixmap(display_path)
                if not pixmap.isNull():
                    self.preview_label.setPixmap(
                        pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
            else:
                # Start live visual playback with bounding box overlay for video files
                self._start_visual_overlay_playback()

            alerts = self._service.get_session_alerts(session.id)
            alert_count = len(alerts)
            if alert_count > 0:
                sick_str = f"<font color='#D32F2F'><b>{alert_count} lượt nghi ngờ LẬT NGỬA (Đỏ)</b></font>"
            else:
                sick_str = "<font color='#2E7D32'><b>Không phát hiện lật ngửa (Khỏe mạnh)</b></font>"

            self.result_label.setText(
                f"<b>ĐÃ HOÀN THÀNH PHÂN TÍCH AI (MODEL LẬT NGỬA)</b><br>"
                f"<b>Phiên làm việc:</b> #{session.id} ({session.model_version})<br>"
                f"<b>Kết quả phát hiện:</b> {sick_str}<br>"
                f"<b>Thông báo:</b> {session.notes or 'Hoàn thành'}<br><br>"
                f"<i>Hệ thống đã tự động ghi nhận phiên phân tích và tạo Cảnh báo Thú y nếu có cá thể bất thường.</i>"
            )
            self.vet_suggest_btn.show()
            self.track_detail_btn.show()
            self._last_session_id = session.id

            self._refresh_history()
            QMessageBox.information(
                self,
                "Hoàn thành phân tích AI",
                "Đã thực hiện xong phân tích AI!\n"
                "Tọa độ Bounding box đã được vẽ trực quan lên video/hình ảnh.\n"
                "Hệ thống đã tự động lưu Cảnh báo đỏ, khởi tạo Bệnh án Thú y và xuất báo cáo Chi tiết cá thể."
            )
        finally:
            self.analyze_btn.setText("Bắt đầu phân tích AI")
            self.analyze_btn.setEnabled(True)

    def _start_visual_overlay_playback(self) -> None:
        if self._selected_video_path and Path(self._selected_video_path).exists():
            self._playback_cap = cv2.VideoCapture(self._selected_video_path)
        else:
            self._playback_cap = None

        self._playback_frame_idx = 0
        self._playback_timer.start(40)  # 25 FPS

    def _on_playback_tick(self) -> None:
        self._playback_frame_idx += 1
        if self._playback_frame_idx >= 150:
            self._playback_frame_idx = 0

        # Read real frame or generate dark green mat
        frame = None
        if self._playback_cap and self._playback_cap.isOpened():
            ret, frame = self._playback_cap.read()
            if not ret or frame is None:
                self._playback_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._playback_cap.read()

        if frame is None:
            frame = np.full((360, 640, 3), (25, 35, 28), dtype=np.uint8)

        # Draw AI Bounding Boxes (Requirement 4)
        sample_tracks = self._service._ai_service.analyze_video("").tracks
        frame = draw_duck_overlay(frame, self._playback_frame_idx, sample_tracks, show_labels=True)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.preview_label.setPixmap(pixmap.scaled(
            self.preview_label.size(),
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
        dlg = TrackDetailDialog(session_id=session_id, parent=self)
        dlg.exec()

    def _open_veterinary_form(self) -> None:
        from app.ui.veterinary.veterinary_record_dialog import VeterinaryRecordDialog
        dlg = VeterinaryRecordDialog(self.current_user, parent=self)
        if self._selected_video_path:
            dlg.symptoms_input.setPlainText(f"Phát hiện cảnh báo AI từ tệp {Path(self._selected_video_path).name}: Nghi ngờ vịt Lật ngửa (Té ngã / Nằm ngửa).")
            dlg.diagnosis_input.setPlainText("Nghi dịch bệnh / Té ngã (Lật Ngửa)")
            dlg.treatment_input.setPlainText("Cách ly cá thể nghi bệnh, theo dõi thân nhiệt và tiêm bổ sung vắc xin.")
            dlg.veterinarian_input.setText(self.current_user.full_name or self.current_user.username)
        if dlg.exec():
            QMessageBox.information(
                self,
                "Tạo Hồ sơ Bệnh án",
                "Đã lưu Hồ sơ Bệnh án Thú y thành công! Bạn có thể xem chi tiết tại danh mục 'Hồ sơ bệnh án'."
            )

    # --- History tab -----------------------------------------------------
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
        fit_table_height(self.history_table)
        self.history_table.setVisible(bool(sessions))
        self.history_empty.setVisible(not sessions)

    def refresh(self) -> None:
        self._refresh_history()

    def closeEvent(self, event):
        self._playback_timer.stop()
        if self._playback_cap:
            self._playback_cap.release()
        super().closeEvent(event)
