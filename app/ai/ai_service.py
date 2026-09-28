"""
AI Service Standardized Seam & Contract.

Standardized interface connecting the PyQt6 Application with the AI Processing Pipeline
(YOLOv8 Detection + ByteTrack Tracking + Duck Behavior Classification).

Contract Output:
- Input: video file path (mp4, avi)
- Output per track: track_id, start_frame/end_frame, start_time/end_time,
  label ("Có bệnh" / "Khỏe mạnh"), confidence (0.0-1.0), bboxes dict per frame {frame_idx: (x1, y1, x2, y2)}.
"""
from __future__ import annotations

import abc
import datetime as dt
from dataclasses import dataclass, field
import random


@dataclass
class DuckTrack:
    """Standardized track summary for a single duck across video frames."""
    track_id: int
    start_frame: int = 0
    end_frame: int = 100
    start_time: float = 0.0
    end_time: float = 10.0
    label: str = "Khỏe mạnh"  # "Có bệnh" | "Khỏe mạnh"
    confidence: float = 0.90
    behavior_detail: str = "Di chuyển bình thường"
    # Map frame_idx -> (x1, y1, x2, y2) normalized/pixel bounding box
    bboxes: dict[int, tuple[float, float, float, float]] = field(default_factory=dict)


@dataclass
class AIDetection:
    """Frame-by-frame detection record (mirrors ai_detection_results DB table)."""
    track_id: int | None = None
    timestamp: float | None = None
    frame_idx: int | None = None
    bbox: tuple[float, float, float, float] | None = None  # x1, y1, x2, y2
    confidence: float | None = None
    behavior_label: str | None = None
    health_status: str | None = None  # "Có bệnh" | "Khỏe mạnh"
    notes: str | None = None


@dataclass
class AIAlertResult:
    """Alert triggered during AI analysis."""
    track_id: int | None
    alert_type: str
    severity: str  # RED | ORANGE | GREEN
    timestamp: float | None
    description: str


@dataclass
class AIAnalysisResult:
    """Return value of AIService.analyze_video()."""
    model_version: str
    status: str  # e.g. "DONE" or "PLACEHOLDER_DONE"
    tracks: list[DuckTrack] = field(default_factory=list)
    detections: list[AIDetection] = field(default_factory=list)
    alerts: list[AIAlertResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    message: str = ""


class AIServiceBase(abc.ABC):
    """Abstract Base Class defining the AI Pipeline Contract."""

    @abc.abstractmethod
    def analyze_video(self, video_path: str) -> AIAnalysisResult:
        """Run detection + ByteTrack + behavior classification on a video file."""
        raise NotImplementedError


class PlaceholderAIService(AIServiceBase):
    """
    Placeholder AI Service providing realistic synthetic duck trajectories
    and bounding boxes for UI demonstration before weights are plugged in.
    """

    MODEL_VERSION = "YOLOv8-ByteTrack-SIMULATED-1.0"

    def analyze_video(self, video_path: str) -> AIAnalysisResult:
        from app.config.constants import AISessionStatus, AlertSeverity, AlertType

        # Generate 4 realistic duck tracks with smooth bounding box motion
        tracks = []
        detections = []
        alerts = []

        # Duck 1: Healthy
        bbox1 = {}
        for f in range(0, 150):
            x1 = 120 + int(f * 0.8)
            y1 = 140 + int(sin_step(f, 10))
            bbox1[f] = (x1, y1, x1 + 75, y1 + 60)
        t1 = DuckTrack(
            track_id=101, start_frame=0, end_frame=150, start_time=0.0, end_time=6.0,
            label="Khỏe mạnh", confidence=0.94, behavior_detail="Di chuyển bình thường",
            bboxes=bbox1
        )
        tracks.append(t1)

        # Duck 2: Sick / Abnormal (Té ngã / Lật ngửa)
        bbox2 = {}
        for f in range(0, 150):
            x1 = 340 + int(sin_step(f, 3))
            y1 = 210 + int(sin_step(f, 2))
            bbox2[f] = (x1, y1, x1 + 80, y1 + 65)
        t2 = DuckTrack(
            track_id=102, start_frame=0, end_frame=150, start_time=0.0, end_time=6.0,
            label="Có bệnh", confidence=0.89, behavior_detail="Nghi bệnh: Té ngã / lật ngửa, giảm vận động",
            bboxes=bbox2
        )
        tracks.append(t2)

        # Duck 3: Healthy
        bbox3 = {}
        for f in range(0, 150):
            x1 = 520 - int(f * 0.5)
            y1 = 160 + int(sin_step(f, 8))
            bbox3[f] = (x1, y1, x1 + 70, y1 + 55)
        t3 = DuckTrack(
            track_id=103, start_frame=0, end_frame=150, start_time=0.0, end_time=6.0,
            label="Khỏe mạnh", confidence=0.92, behavior_detail="Di chuyển bình thường",
            bboxes=bbox3
        )
        tracks.append(t3)

        # Populate detections list for database persistence
        for t in tracks:
            for f_idx, (x1, y1, x2, y2) in t.bboxes.items():
                if f_idx % 15 == 0:  # Sample every 15 frames for DB storage
                    detections.append(AIDetection(
                        track_id=t.track_id,
                        timestamp=round(f_idx / 25.0, 2),
                        frame_idx=f_idx,
                        bbox=(x1, y1, x2 - x1, y2 - y1),
                        confidence=t.confidence,
                        behavior_label=t.behavior_detail,
                        health_status=t.label,
                        notes=f"Phát hiện cá thể {t.track_id}: {t.label}"
                    ))

        # Alert for sick duck
        alerts.append(AIAlertResult(
            track_id=102,
            alert_type=AlertType.AI_ABNORMAL_BEHAVIOR,
            severity=AlertSeverity.RED,
            timestamp=2.5,
            description="Phát hiện cá thể ID:102 nghi bị bệnh (Té ngã / Lật ngửa liên tục trong 5+ khung hình)."
        ))

        return AIAnalysisResult(
            model_version=self.MODEL_VERSION,
            status=AISessionStatus.PLACEHOLDER_DONE,
            tracks=tracks,
            detections=detections,
            alerts=alerts,
            summary={
                "total_individuals": len(tracks),
                "normal_individuals": 2,
                "suspected_individuals": 1,
                "detection": "YOLOv8-Simulated",
                "tracking": "ByteTrack-Simulated",
                "behavior_classifier": "Behavior-Rules-Simulated",
            },
            message="Đã hoàn thành phân tích AI (Khung hình & Tọa độ Bounding Box mô phỏng sẵn sàng)."
        )


class RealAIService(AIServiceBase):
    """
    Real AI Service integration for Ultralytics YOLOv8 + Duck Inverted (Lật Ngửa) Behavior Detection.
    Uses duckai_package/best.pt and duckai_package/duck_detector.py pipeline.
    """

    MODEL_VERSION = "YOLOv8-DuckLatNgua-v1.0"

    def __init__(self, weights_path: str | None = None) -> None:
        from pathlib import Path
        if weights_path is None:
            base = Path(__file__).resolve().parents[2]
            weights_path = str(base / "duckai_package" / "best.pt")
        self.weights_path = weights_path
        self.load_model(weights_path)

    def load_model(self, weights_path: str) -> None:
        from pathlib import Path
        p = Path(weights_path)
        if not p.exists():
            raise FileNotFoundError(f"Không tìm thấy file trọng số model AI lật ngửa tại: '{weights_path}'")
        self.weights_path = str(p)

    def analyze_video(self, video_path: str) -> AIAnalysisResult:
        from pathlib import Path
        from app.config.constants import AISessionStatus, AlertSeverity, AlertType
        from app.ai.video_processor import is_supported_image

        # If video_path is empty or non-existent (e.g. preview overlay tick), return sample tracks
        if not video_path or not Path(video_path).exists():
            placeholder = PlaceholderAIService()
            return placeholder.analyze_video(video_path)

        if is_supported_image(video_path):
            return self._analyze_image(video_path)

        try:
            from duckai_package.duck_detector import analyze_video as run_duck_detector
            raw_res = run_duck_detector(
                video_path=video_path,
                model_path=self.weights_path,
            )
        except Exception as exc:
            import logging
            logging.getLogger("wdf.ai").error("Error in duck_detector analyze_video: %s", exc, exc_info=True)
            # Fallback to placeholder if inference fails
            placeholder = PlaceholderAIService()
            res = placeholder.analyze_video(video_path)
            res.message = f"Phát hiện qua model thật thất bại, sử dụng mô phỏng: {exc}"
            return res

        tracks: list[DuckTrack] = []
        detections: list[AIDetection] = []
        alerts: list[AIAlertResult] = []

        raw_alerts = raw_res.get("alerts", [])
        total_frames = raw_res.get("total_frames", 100)
        duration_sec = raw_res.get("duration_sec", 10.0)

        alerted_track_ids = set()
        for idx, alt in enumerate(raw_alerts):
            t_id = alt.get("track_id", idx + 1)
            alerted_track_ids.add(t_id)

            s_sec = alt.get("start_time_sec", 0.0)
            e_sec = alt.get("end_time_sec", 0.0)
            dur = alt.get("duration_sec", 0.0)
            s_frame = alt.get("start_frame", 0)
            e_frame = alt.get("end_frame", 0)

            tracks.append(DuckTrack(
                track_id=t_id,
                start_frame=s_frame,
                end_frame=e_frame,
                start_time=s_sec,
                end_time=e_sec,
                label="Có bệnh",
                confidence=0.92,
                behavior_detail=f"Phát hiện nguy cơ LẬT NGỬA (kéo dài {dur}s từ {s_sec}s đến {e_sec}s)",
            ))

            detections.append(AIDetection(
                track_id=t_id,
                timestamp=s_sec,
                frame_idx=s_frame,
                confidence=0.92,
                behavior_label="Nghi ngờ Lật Ngửa",
                health_status="Có bệnh",
                notes=f"Cá thể ID:{t_id} lật ngửa từ {s_sec}s đến {e_sec}s (Thời lượng: {dur}s)",
            ))

            alerts.append(AIAlertResult(
                track_id=t_id,
                alert_type=AlertType.AI_ABNORMAL_BEHAVIOR,
                severity=AlertSeverity.RED,
                timestamp=s_sec,
                description=f"CẢNH BÁO AI: Cá thể ID:{t_id} phát hiện nghi ngờ LẬT NGỬA liên tục trong {dur}s (khung hình {s_frame}-{e_frame}).",
            ))

        # If no alerts found, create representative normal track
        if not tracks:
            tracks.append(DuckTrack(
                track_id=1,
                start_frame=0,
                end_frame=total_frames,
                start_time=0.0,
                end_time=duration_sec,
                label="Khỏe mạnh",
                confidence=0.95,
                behavior_detail="Di chuyển bình thường, không phát hiện lật ngửa",
            ))

        sick_count = len(alerted_track_ids)
        total_count = max(len(tracks), 1)
        normal_count = max(0, total_count - sick_count)

        return AIAnalysisResult(
            model_version=self.MODEL_VERSION,
            status=AISessionStatus.DONE,
            tracks=tracks,
            detections=detections,
            alerts=alerts,
            summary={
                "total_individuals": total_count,
                "normal_individuals": normal_count,
                "suspected_individuals": sick_count,
                "detection": "YOLOv8-DuckLatNgua",
                "tracking": "BoT-SORT",
                "behavior_classifier": "Temporal Rule + Immobility Check",
            },
            message=f"Hoàn tất phân tích video bằng model Lật ngửa: phát hiện {sick_count} cá thể nghi ngờ lật ngửa."
        )

    def _analyze_image(self, image_path: str) -> AIAnalysisResult:
        import cv2
        from ultralytics import YOLO
        from app.config.constants import AISessionStatus, AlertSeverity, AlertType

        model = YOLO(self.weights_path)
        results = model(image_path, conf=0.30, verbose=False)[0]

        img = cv2.imread(image_path)
        h, w = img.shape[:2] if img is not None else (480, 640)

        boxes = []
        if results.boxes is not None:
            for box in results.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((cls_name, x1, y1, x2, y2, conf))

        than_boxes = [b for b in boxes if b[0] == "than"]
        chan_boxes = [b for b in boxes if b[0] == "chan"]

        than_info = []
        for i, than in enumerate(than_boxes):
            _, x1, y1, x2, y2, conf = than
            than_info.append({
                "box": than, "cx": (x1 + x2) / 2, "cy": (y1 + y2) / 2,
                "w": x2 - x1, "h": y2 - y1, "chans": [], "id": i + 1, "conf": conf
            })

        MAX_DX_RATIO, MAX_DY_RATIO = 1.2, 1.0
        for chan in chan_boxes:
            ccx = (chan[1] + chan[3]) / 2
            ccy = (chan[2] + chan[4]) / 2
            best_i, best_dist = None, float("inf")
            for i, t in enumerate(than_info):
                dx = abs(ccx - t["cx"]) / max(t["w"], 1e-6)
                dy = abs(ccy - t["cy"]) / max(t["h"], 1e-6)
                if dx > MAX_DX_RATIO or dy > MAX_DY_RATIO:
                    continue
                dist = dx + dy
                if dist < best_dist:
                    best_dist = dist
                    best_i = i
            if best_i is not None:
                than_info[best_i]["chans"].append(chan)

        tracks = []
        detections = []
        alerts = []

        margin = 0.3
        span_ratio = 1.2

        for t in than_info:
            _, x1, y1, x2, y2, conf = t["box"]
            tid = t["id"]
            than_cx, than_cy, than_h = t["cx"], t["cy"], t["h"]
            my_chans = t["chans"]

            flipped_by_yrule = False
            if my_chans:
                closest_chan = min(my_chans, key=lambda c: abs(((c[1] + c[3]) / 2) - than_cx))
                chan_cy = (closest_chan[2] + closest_chan[4]) / 2
                flipped_by_yrule = chan_cy < than_cy - margin * than_h

            flipped_by_span = False
            if len(my_chans) >= 2:
                centers_x = [(c[1] + c[3]) / 2 for c in my_chans]
                span = max(centers_x) - min(centers_x)
                flipped_by_span = (span / max(t["w"], 1e-6)) >= span_ratio

            is_flipped = flipped_by_yrule or flipped_by_span

            label = "Có bệnh" if is_flipped else "Khỏe mạnh"
            behavior = "Phát hiện nguy cơ LẬT NGỬA (Té ngã / Nằm ngửa)" if is_flipped else "Bình thường"

            tracks.append(DuckTrack(
                track_id=tid,
                start_frame=0,
                end_frame=0,
                start_time=0.0,
                end_time=0.0,
                label=label,
                confidence=round(conf, 2),
                behavior_detail=behavior,
                bboxes={0: (x1, y1, x2, y2)}
            ))

            detections.append(AIDetection(
                track_id=tid,
                timestamp=0.0,
                frame_idx=0,
                bbox=(x1, y1, x2 - x1, y2 - y1),
                confidence=round(conf, 2),
                behavior_label=behavior,
                health_status=label,
                notes=f"Phân tích ảnh: Cá thể ID:{tid} - {label}"
            ))

            if is_flipped:
                alerts.append(AIAlertResult(
                    track_id=tid,
                    alert_type=AlertType.AI_ABNORMAL_BEHAVIOR,
                    severity=AlertSeverity.RED,
                    timestamp=0.0,
                    description=f"CẢNH BÁO AI (HÌNH ẢNH): Cá thể ID:{tid} phát hiện dấu hiệu LẬT NGỬA."
                ))

        if not tracks:
            tracks.append(DuckTrack(
                track_id=1,
                start_frame=0,
                end_frame=0,
                start_time=0.0,
                end_time=0.0,
                label="Khỏe mạnh",
                confidence=0.90,
                behavior_detail="Không phát hiện cá thể bất thường trên ảnh"
            ))

        annotated_path = image_path
        if img is not None:
            from pathlib import Path
            from app.config.settings import VIDEOS_DIR
            for t in than_info:
                _, x1, y1, x2, y2, conf = t["box"]
                tid = t["id"]
                my_chans = t["chans"]
                than_cx, than_cy, than_h = t["cx"], t["cy"], t["h"]

                flipped_by_yrule = False
                if my_chans:
                    closest_chan = min(my_chans, key=lambda c: abs(((c[1] + c[3]) / 2) - than_cx))
                    chan_cy = (closest_chan[2] + closest_chan[4]) / 2
                    flipped_by_yrule = chan_cy < than_cy - margin * than_h

                flipped_by_span = False
                if len(my_chans) >= 2:
                    centers_x = [(c[1] + c[3]) / 2 for c in my_chans]
                    span = max(centers_x) - min(centers_x)
                    flipped_by_span = (span / max(t["w"], 1e-6)) >= span_ratio

                is_flipped = flipped_by_yrule or flipped_by_span

                color = (0, 0, 255) if is_flipped else (0, 200, 0)
                lbl_text = f"ID:{tid} | NGHI LAT NGUA ({int(conf*100)}%)" if is_flipped else f"ID:{tid} | KHOE MANH ({int(conf*100)}%)"

                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3 if is_flipped else 2)
                cv2.putText(img, lbl_text, (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            for chan in chan_boxes:
                _, x1, y1, x2, y2, conf = chan
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 165, 255), 2)
                cv2.putText(img, "chan", (x1, max(15, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

            annotated_path = str(VIDEOS_DIR / f"_annotated_{Path(image_path).name}")
            cv2.imwrite(annotated_path, img)

        sick_count = len(alerts)
        total_count = len(tracks)
        normal_count = max(0, total_count - sick_count)

        return AIAnalysisResult(
            model_version=self.MODEL_VERSION,
            status=AISessionStatus.DONE,
            tracks=tracks,
            detections=detections,
            alerts=alerts,
            summary={
                "total_individuals": total_count,
                "normal_individuals": normal_count,
                "suspected_individuals": sick_count,
                "detection": "YOLOv8-DuckLatNgua-Image",
                "behavior_classifier": "Relative Y-position + Leg-span",
                "annotated_image_path": annotated_path,
            },
            message=f"Hoàn tất phân tích hình ảnh bằng model Lật ngửa: {sick_count} vịt nghi ngờ lật ngửa."
        )


def sin_step(idx: int, amp: int) -> float:
    import math
    return amp * math.sin(idx * 0.1)


def get_ai_service() -> AIServiceBase:
    """
    Factory function used everywhere in the application.
    Automatically initializes RealAIService with duckai_package/best.pt if present,
    otherwise falls back gracefully to PlaceholderAIService.
    """
    try:
        from pathlib import Path
        weights_file = Path(__file__).resolve().parents[2] / "duckai_package" / "best.pt"
        if weights_file.exists():
            return RealAIService(str(weights_file))
    except Exception as exc:
        import logging
        logging.getLogger("wdf.ai").warning("Không thể khởi tạo RealAIService, dùng PlaceholderAIService: %s", exc)
    return PlaceholderAIService()
