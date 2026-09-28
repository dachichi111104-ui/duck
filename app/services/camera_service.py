"""
Camera Surveillance Service & Live Frame Worker for Duck AI System.
Manages Camera records in SQLite database and streams live video frames using VideoLoopReader.
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QImage

from app.database.connection import session_scope
from app.database.models import Camera
from app.repositories.camera_repository import CameraRepository
from app.ai.video_processor import VideoLoopReader
from app.utils.logger import get_logger

logger = get_logger("camera_service")


@dataclass
class CameraInfo:
    code: str
    name: str
    location: str
    status: str = "ONLINE"
    fps: int = 24
    resolution: str = "1920x1080"
    rtsp_url: str = ""
    video_file_path: str | None = None
    ai_enabled: bool = True
    active_alerts: int = 0


# Initial seed cameras if table is empty
DEFAULT_CAM_DATA = [
    {"code": "CAM-01", "name": "Khu Chuồng 01 - Khu Ăn Uống", "location": "Chuồng 01", "status": "ONLINE", "rtsp_url": "rtsp://192.168.1.101/stream1", "ai_enabled": True},
    {"code": "CAM-02", "name": "Máng ăn & Uống 01", "location": "Chuồng 01", "status": "ONLINE", "rtsp_url": "rtsp://192.168.1.102/stream1", "ai_enabled": True},
    {"code": "CAM-03", "name": "Ao Nước Bơi - Khu B", "location": "Khu Nước", "status": "ONLINE", "rtsp_url": "rtsp://192.168.1.103/stream1", "ai_enabled": True},
    {"code": "CAM-04", "name": "Chuồng 02 - Khu Sân Chơi", "location": "Chuồng 02", "status": "ONLINE", "rtsp_url": "rtsp://192.168.1.104/stream1", "ai_enabled": True},
]


class CameraWorker(QThread):
    """
    Background worker thread that renders live video frames for all cameras.
    Uses VideoLoopReader if video_file_path is assigned, otherwise renders 'Chưa có nguồn video mô phỏng'.
    Emits frame_ready(camera_code, QImage).
    """
    frame_ready = pyqtSignal(str, QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused = False
        self._readers: dict[str, VideoLoopReader] = {}
        self._repo = CameraRepository()

    def run(self):
        frame_width = 640
        frame_height = 360

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            start_time = time.time()
            now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with session_scope() as session:
                cameras = self._repo.get_all(session)

            if not cameras:
                time.sleep(0.5)
                continue

            for cam in cameras:
                code = cam.code
                if cam.status in ("OFFLINE", "STOPPED"):
                    continue

                frame_bgr = None
                # Check video loop reader
                if cam.video_file_path:
                    reader = self._readers.get(code)
                    if not reader:
                        reader = VideoLoopReader(cam.video_file_path)
                        self._readers[code] = reader
                    else:
                        reader.set_file_path(cam.video_file_path)

                    ok, v_frame = reader.read_frame()
                    if ok and v_frame is not None:
                        frame_bgr = cv2.resize(v_frame, (frame_width, frame_height))

                if frame_bgr is None:
                    # No video file assigned or invalid video -> Display clean state canvas
                    frame_bgr = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                    frame_bgr[:] = (20, 24, 20)  # Dark farm green background

                    # Center message: "Chưa có nguồn video mô phỏng"
                    msg = "CHUA CO NGUON VIDEO MO PHONG"
                    sub_msg = f"Camera: {cam.name}"
                    sub_msg2 = "Gán tệp video mô phỏng trong cài đặt Camera"

                    cv2.putText(frame_bgr, msg, (120, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 160, 140), 2, cv2.LINE_AA)
                    cv2.putText(frame_bgr, sub_msg, (150, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 120, 100), 1, cv2.LINE_AA)
                    cv2.putText(frame_bgr, sub_msg2, (130, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 100, 80), 1, cv2.LINE_AA)

                # Telemetry HUD Header & Footer
                cv2.putText(frame_bgr, f"LIVE  {cam.code} - {cam.name}", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 100), 1)
                cv2.putText(frame_bgr, now_str, (460, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 190, 180), 1)

                footer_text = f"FPS: {cam.fps}  RES: {cam.resolution or '1920x1080'}  STATUS: {cam.status}  AI: {'ON' if cam.ai_enabled else 'OFF'}"
                cv2.putText(frame_bgr, footer_text, (12, frame_height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 150, 140), 1)

                # Convert BGR to QImage
                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

                self.frame_ready.emit(code, qt_img)

            elapsed = time.time() - start_time
            sleep_time = max(1.0 / 24.0 - elapsed, 0.005)
            time.sleep(sleep_time)

    def stop(self):
        self.running = False
        for r in self._readers.values():
            r.release()
        self._readers.clear()
        self.wait(1000)


class CameraService(QObject):
    """Camera service for DB operations and stream worker management."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._repo = CameraRepository()
        self.worker: CameraWorker | None = None
        self._ensure_seed_cameras()

    def _ensure_seed_cameras(self):
        with session_scope() as session:
            cams = self._repo.get_all(session)
            if not cams:
                for idx, item in enumerate(DEFAULT_CAM_DATA):
                    cam = Camera(
                        code=item["code"],
                        name=item["name"],
                        location=item["location"],
                        status=item["status"],
                        rtsp_url=item["rtsp_url"],
                        ai_enabled=item["ai_enabled"],
                        sync_status="PENDING",
                    )
                    session.add(cam)

    def start_worker(self):
        if not self.worker or not self.worker.isRunning():
            self.worker = CameraWorker()
            self.worker.start()

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

    def get_cameras(self) -> list[Camera]:
        with session_scope() as session:
            return self._repo.get_all(session)

    def get_camera_by_id(self, camera_id: int) -> Camera | None:
        with session_scope() as session:
            return session.get(Camera, camera_id)

    def get_camera(self, code: str) -> Camera | None:
        with session_scope() as session:
            return self._repo.get_by_code(session, code)

    def create_camera(self, code: str, name: str, location: str | None = None,
                      rtsp_url: str | None = None, video_file_path: str | None = None,
                      resolution: str = "1920x1080", fps: int = 30,
                      ai_enabled: bool = True, barn_id: int | None = None) -> Camera:
        with session_scope() as session:
            cam = Camera(
                code=code,
                name=name,
                location=location,
                status="ONLINE",
                rtsp_url=rtsp_url,
                video_file_path=video_file_path,
                resolution=resolution,
                fps=fps,
                ai_enabled=ai_enabled,
                barn_id=barn_id,
                sync_status="PENDING",
            )
            session.add(cam)
            session.flush()
            session.refresh(cam)
            return cam

    def update_camera(self, camera_id: int, **kwargs) -> Camera | None:
        with session_scope() as session:
            cam = session.get(Camera, camera_id)
            if not cam:
                return None
            for k, v in kwargs.items():
                if hasattr(cam, k):
                    setattr(cam, k, v)
            cam.sync_status = "PENDING"
            cam.last_modified_at = dt.datetime.utcnow()
            session.flush()
            return cam

    def delete_camera(self, camera_id: int) -> bool:
        with session_scope() as session:
            cam = session.get(Camera, camera_id)
            if not cam:
                return False
            session.delete(cam)
            return True

    def count_total(self) -> int:
        with session_scope() as session:
            return len(self._repo.get_all(session))

    def count_online(self) -> int:
        with session_scope() as session:
            return sum(1 for c in self._repo.get_all(session) if c.status == "ONLINE")

    def count_offline(self) -> int:
        with session_scope() as session:
            return sum(1 for c in self._repo.get_all(session) if c.status == "OFFLINE")

    def count_alerts(self) -> int:
        return 0
