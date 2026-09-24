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


def extract_metadata(file_path: str) -> VideoMetadata:
    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        return VideoMetadata(file_name, 0.0, None, None, None, False, "Không tìm thấy tệp video.")

    if not is_supported_video(file_path):
        return VideoMetadata(file_name, 0.0, None, None, None, False,
                              "Định dạng video không được hỗ trợ.")

    size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)

    if cv2 is None:
        return VideoMetadata(file_name, size_mb, None, None, None, False,
                              "Thư viện OpenCV chưa được cài đặt.")

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
