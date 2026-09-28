"""
Video metadata extraction (duration, resolution, fps, file size).

This runs today (real, not a placeholder) since it only reads container
metadata via OpenCV — it does not perform any detection or analysis.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import cv2
except ImportError:  # pragma: no cover - OpenCV should be installed via requirements.txt
    cv2 = None

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS


@dataclass
class VideoMetadata:
    file_name: str
    file_size_mb: float
    duration_seconds: float | None
    resolution: str | None
    fps: float | None
    valid: bool
    error: str | None = None


def is_supported_video(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_VIDEO_EXTENSIONS


def is_supported_image(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_IMAGE_EXTENSIONS


def is_supported_media(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_MEDIA_EXTENSIONS


def extract_metadata(file_path: str) -> VideoMetadata:
    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        return VideoMetadata(file_name, 0.0, None, None, None, False, "Không tìm thấy tệp phương tiện.")

    if not is_supported_media(file_path):
        return VideoMetadata(file_name, 0.0, None, None, None, False,
                              "Định dạng video/hình ảnh không được hỗ trợ.")

    size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)

    if cv2 is None:
        return VideoMetadata(file_name, size_mb, None, None, None, False,
                              "Thư viện OpenCV chưa được cài đặt.")

    if is_supported_image(file_path):
        img = cv2.imread(file_path)
        if img is None:
            return VideoMetadata(file_name, size_mb, None, None, None, False, "Không thể đọc tệp hình ảnh.")
        h, w = img.shape[:2]
        return VideoMetadata(
            file_name=file_name, file_size_mb=size_mb, duration_seconds=0.0,
            resolution=f"{w}x{h}", fps=1.0, valid=True,
        )

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return VideoMetadata(file_name, size_mb, None, None, None, False,
                              "Không thể đọc tệp video (tệp có thể bị hỏng).")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = (frame_count / fps) if fps else None
        resolution = f"{width}x{height}" if width and height else None
    finally:
        cap.release()

    return VideoMetadata(
        file_name=file_name, file_size_mb=size_mb, duration_seconds=duration,
        resolution=resolution, fps=round(fps, 2) if fps else None, valid=True,
    )


def generate_thumbnail(file_path: str, output_path: str, frame_position: float = 0.1) -> bool:
    """Extract a single frame near the start of the video as a JPEG thumbnail."""
    if cv2 is None or not os.path.exists(file_path):
        return False
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return False
    try:
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        target_frame = int(frame_count * frame_position) if frame_count else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = cap.read()
        if not ok:
            return False
        cv2.imwrite(output_path, frame)
        return True
    finally:
        cap.release()


class VideoLoopReader:
    """
    Continuous frame-by-frame video loop reader for simulation & camera monitoring.
    Re-uses OpenCV VideoCapture and rewinds to frame 0 upon reaching end of stream.
    """

    def __init__(self, file_path: str | None = None):
        self.file_path = file_path
        self.cap: cv2.VideoCapture | None = None
        if file_path:
            self._open()

    def set_file_path(self, file_path: str | None):
        if self.file_path != file_path:
            self.release()
            self.file_path = file_path
            if file_path:
                self._open()

    def _open(self) -> bool:
        if cv2 is not None and self.file_path and os.path.exists(self.file_path):
            self.cap = cv2.VideoCapture(self.file_path)
            return self.cap.isOpened()
        self.cap = None
        return False

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Returns (success, frame_bgr). Automatically rewinds to start on EOF."""
        if cv2 is None:
            return False, None

        if not self.cap or not self.cap.isOpened():
            if not self._open():
                return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            # Loop back to start
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None

        return True, frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

