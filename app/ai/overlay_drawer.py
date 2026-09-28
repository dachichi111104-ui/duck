"""
AI Bounding Box Overlay Drawing Utility.
Draws visual bounding boxes, track IDs, health status tags, and color-coded borders onto OpenCV BGR video frames.
Green (46, 125, 46) = Khỏe mạnh
Red (47, 47, 211) = Có bệnh / Nghi bệnh
"""
from __future__ import annotations

import cv2
import numpy as np

# BGR Colors matching Brand System
COLOR_HEALTHY_BGR = (46, 125, 46)     # Dark Green (#2E7D32)
COLOR_SICK_BGR = (47, 47, 211)        # Alert Red (#D32F2F)
COLOR_TEXT_WHITE = (255, 255, 255)


def draw_duck_overlay(
    frame: np.ndarray,
    frame_idx: int,
    tracks: list,
    show_labels: bool = True
) -> np.ndarray:
    """
    Draw bounding boxes and status labels on a single OpenCV video frame.

    Args:
        frame: BGR image numpy array.
        frame_idx: Current frame index in video stream.
        tracks: List of DuckTrack dataclass objects or detection dicts.
        show_labels: Whether to render label text tags.

    Returns:
        Frame with bounding box overlays rendered.
    """
    if frame is None:
        return frame

    h, w = frame.shape[:2]

    for track in tracks:
        # Get bounding box for current frame index
        bboxes = getattr(track, "bboxes", {})
        if not bboxes:
            continue

        # If frame_idx not exactly in bboxes, find closest frame_idx
        if frame_idx in bboxes:
            bbox = bboxes[frame_idx]
        else:
            available_frames = list(bboxes.keys())
            if not available_frames:
                continue
            closest_f = min(available_frames, key=lambda f: abs(f - frame_idx))
            bbox = bboxes[closest_f]

        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Clamp to frame boundaries
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(x1 + 10, min(w, x2))
        y2 = max(y1 + 10, min(h, y2))

        label = getattr(track, "label", "Khỏe mạnh")
        track_id = getattr(track, "track_id", 0)
        confidence = getattr(track, "confidence", 0.90)

        is_sick = (label == "Có bệnh" or "bệnh" in label.lower())
        box_color = COLOR_SICK_BGR if is_sick else COLOR_HEALTHY_BGR

        # Draw main bounding box rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        if show_labels:
            status_str = "CÓ BỆNH" if is_sick else "KHỎE MẠNH"
            text_str = f"ID:{track_id} | {status_str} ({confidence:.0%})"

            # Calculate text size for badge background
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.42
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(text_str, font, scale, thickness)

            # Draw top badge background
            badge_y1 = max(0, y1 - text_h - 8)
            badge_y2 = y1
            badge_x2 = min(w, x1 + text_w + 8)
            cv2.rectangle(frame, (x1, badge_y1), (badge_x2, badge_y2), box_color, -1)

            # Draw white text on badge background
            cv2.putText(
                frame,
                text_str,
                (x1 + 4, max(text_h + 2, y1 - 4)),
                font,
                scale,
                COLOR_TEXT_WHITE,
                thickness,
                lineType=cv2.LINE_AA
            )

    return frame
