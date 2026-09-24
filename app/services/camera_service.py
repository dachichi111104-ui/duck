"""
Camera Surveillance Service & Live Frame Worker for Duck AI System.
Simulates high-performance RTSP camera video feeds with farm rendering and telemetry.
"""
from __future__ import annotations

import datetime as dt
import math
import random
import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QImage

from app.utils.logger import get_logger

logger = get_logger("camera_service")


@dataclass
class CameraInfo:
    code: str
    name: str
    location: str
    status: str = "ONLINE"  # ONLINE, CONNECTING, OFFLINE, STOPPED, AI_ANALYZING
    fps: int = 24
    resolution: str = "1920x1080"
    rtsp_url: str = ""
    ai_enabled: bool = True
    active_alerts: int = 0


DEFAULT_CAMERAS = [
    CameraInfo("CAM-01", "Khu Chuồng 01 - Khu A", "Chuồng 01", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.101/stream1", True, 1),
    CameraInfo("CAM-02", "Máng ăn & Uống 01", "Chuồng 01", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.102/stream1", True, 0),
    CameraInfo("CAM-03", "Aos Nước Bơi - Khu B", "Khu Nước", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.103/stream1", True, 1),
    CameraInfo("CAM-04", "Chuồng 02 - Khu A", "Chuồng 02", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.104/stream1", True, 0),
    CameraInfo("CAM-05", "Khu Ấp Trứng & Con", "Khu Ấp", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.105/stream1", True, 0),
    CameraInfo("CAM-06", "Sân Nắng Ngoại Trời", "Sân Chơi", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.106/stream1", True, 0),
    CameraInfo("CAM-07", "Chuồng 03 - Khu B", "Chuồng 03", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.107/stream1", True, 0),
    CameraInfo("CAM-08", "Khu Cách Ly Thú Y", "Cách Ly", "ONLINE", 24, "1920x1080", "rtsp://1920.168.1.108/stream1", True, 0),
]


class CameraWorker(QThread):
    """
    Background worker thread that renders live video frames for all cameras.
    Emits frame_ready(camera_code, QImage).
    """
    frame_ready = pyqtSignal(str, QImage)

    def __init__(self, cameras: list[CameraInfo], parent=None):
        super().__init__(parent)
        self.cameras = {c.code: c for c in cameras}
        self.running = True
        self.paused = False
        self.show_ai_overlay = True

        # Initialize simulated duck positions for animation
        self.duck_agents = {}
        for code in self.cameras:
            ducks = []
            for d_id in range(6):
                ducks.append({
                    "id": d_id + 1,
                    "x": random.randint(80, 560),
                    "y": random.randint(80, 320),
                    "vx": random.uniform(-1.2, 1.2),
                    "vy": random.uniform(-1.2, 1.2),
                    "status": "SUSPECTED" if (code == "CAM-01" and d_id == 0) or (code == "CAM-03" and d_id == 2) else "HEALTHY",
                    "conf": round(random.uniform(0.88, 0.98), 2),
                })
            self.duck_agents[code] = ducks

    def run(self):
        frame_width = 640
        frame_height = 360

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            start_time = time.time()
            now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for code, cam in list(self.cameras.items()):
                if cam.status == "OFFLINE" or cam.status == "STOPPED":
                    continue

                # Base image canvas (dark #101512)
                frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                frame[:] = (18, 21, 16)  # BGR equivalent of #101512

                # Draw subtle barn floor / pond water background pattern
                if "Aos" in cam.name or "Nước" in cam.location:
                    # Water theme
                    cv2.rectangle(frame, (40, 40), (600, 320), (35, 30, 20), -1)
                    cv2.putText(frame, "POND AREA", (50, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 75, 45), 1)
                else:
                    # Barn pen floor theme
                    cv2.rectangle(frame, (40, 40), (600, 320), (28, 32, 26), -1)
                    cv2.line(frame, (200, 40), (200, 320), (40, 45, 38), 1)
                    cv2.line(frame, (400, 40), (400, 320), (40, 45, 38), 1)
                    cv2.putText(frame, f"ZONE: {cam.location.upper()}", (50, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (70, 85, 70), 1)

                # Update duck movements
                ducks = self.duck_agents.get(code, [])
                for d in ducks:
                    d["x"] += d["vx"]
                    d["y"] += d["vy"]

                    if d["x"] < 60 or d["x"] > 580:
                        d["vx"] *= -1
                    if d["y"] < 60 or d["y"] > 300:
                        d["vy"] *= -1

                    ix, iy = int(d["x"]), int(d["y"])

                    # Draw duck representation
                    duck_color = (60, 180, 240) if d["status"] == "HEALTHY" else (50, 50, 220)
                    cv2.circle(frame, (ix, iy), 10, duck_color, -1)
                    cv2.circle(frame, (ix + 6, iy - 3), 4, (40, 210, 255), -1)  # duck beak/head

                    # Draw bounding box & AI label if AI overlay active
                    if self.show_ai_overlay and cam.ai_enabled:
                        box_color = (50, 180, 50) if d["status"] == "HEALTHY" else (40, 140, 240)
                        lbl = f"Duck #{d['id']} {d['conf']}"
                        if d["status"] == "SUSPECTED":
                            lbl = f"Abnormal #{d['id']} (Lật ngửa)"

                        cv2.rectangle(frame, (ix - 18, iy - 18), (ix + 18, iy + 18), box_color, 1)
                        cv2.putText(frame, lbl, (ix - 18, iy - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.35, box_color, 1)

                # Telemetry HUD header & footer
                cv2.putText(frame, f"● LIVE  {code} - {cam.name}", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 100), 1)
                cv2.putText(frame, now_str, (460, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 190, 180), 1)

                footer_text = f"FPS: {cam.fps}  RES: {cam.resolution}  STATUS: {cam.status}  AI: {'ON' if self.show_ai_overlay else 'OFF'}"
                cv2.putText(frame, footer_text, (12, frame_height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 150, 140), 1)

                # Convert OpenCV BGR to Qt QImage
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

                self.frame_ready.emit(code, qt_img)

            # Control loop frame rate (~24 FPS)
            elapsed = time.time() - start_time
            sleep_time = max(1.0 / 24.0 - elapsed, 0.005)
            time.sleep(sleep_time)

    def stop(self):
        self.running = False
        self.wait(1000)


class CameraService(QObject):
    """Singleton-style camera service for managing camera states and stream workers."""

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
        self.cameras: list[CameraInfo] = [c for c in DEFAULT_CAMERAS]
        self.worker: CameraWorker | None = None

    def start_worker(self):
        if not self.worker or not self.worker.isRunning():
            self.worker = CameraWorker(self.cameras)
            self.worker.start()

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

    def get_cameras(self) -> list[CameraInfo]:
        return self.cameras

    def get_camera(self, code: str) -> CameraInfo | None:
        return next((c for c in self.cameras if c.code == code), None)

    def count_total(self) -> int:
        return len(self.cameras)

    def count_online(self) -> int:
        return sum(1 for c in self.cameras if c.status == "ONLINE")

    def count_offline(self) -> int:
        return sum(1 for c in self.cameras if c.status == "OFFLINE")

    def count_alerts(self) -> int:
        return sum(c.active_alerts for c in self.cameras)
