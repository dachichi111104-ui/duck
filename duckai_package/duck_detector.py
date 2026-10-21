"""
Module nhận diện nguy cơ "lật ngửa" ở vịt từ video.
Đóng gói pipeline: YOLOv8 detect (than/chan) -> tracking (BoT-SORT) ->
rule kết hợp (y-position + leg-span) -> temporal threshold + immobility check.

CÁCH DÙNG (tích hợp vào app khác):

    from duck_detector import analyze_video

    result = analyze_video(
        video_path="duong_dan_video.mp4",
        model_path="best.pt",
    )
    print(result["alerts"])  # danh sách các đợt nghi ngờ lật ngửa

Nếu muốn xem trực tiếp trên GUI (preview từng frame + progress bar), truyền
thêm on_frame callback - xem docstring hàm analyze_video() bên dưới.

YÊU CẦU: pip install ultralytics opencv-python numpy lap
(xem requirements.txt đi kèm)
"""

from collections import deque, defaultdict

import cv2
import numpy as np
from ultralytics import YOLO


def analyze_video(
    video_path,
    model_path,
    conf=0.30,
    margin=0.3,
    ratio=0.8,
    window=30,
    move_thresh=0.35,
    span_ratio=1.2,
    tracker="botsort.yaml",
    save_annotated_path=None,
    on_frame=None,
    sample_fps=5.0,
):
    """
    Phân tích 1 video, trả về các đợt phát hiện hành vi bất thường (lật ngửa / té ngã / bất động).
    Sử dụng sample_fps để tăng tốc xử lý x5-x10 lần mà vẫn đảm bảo độ chính xác theo chuỗi thời gian.
    """
    model = YOLO(model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Không mở được video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    stride = max(1, int(round(fps / sample_fps))) if sample_fps and sample_fps > 0 else 1
    effective_fps = fps / stride

    writer = None
    if save_annotated_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(save_annotated_path, fourcc, effective_fps, (w, h))

    effective_window = max(5, int(round(effective_fps * 1.5)))
    flip_history = defaultdict(lambda: deque(maxlen=effective_window))
    pos_history = defaultdict(lambda: deque(maxlen=effective_window))
    size_history = defaultdict(lambda: deque(maxlen=effective_window))

    # Theo dõi trạng thái cảnh báo để gộp thành các "đợt" liên tục
    open_alerts = {}  # track_id -> start_frame
    closed_alerts = []  # danh sách các đợt đã kết thúc

    MAX_DX_RATIO, MAX_DY_RATIO = 1.2, 1.0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % stride != 0:
            frame_idx += 1
            continue

        results = model.track(
            frame, conf=conf, persist=True, tracker=tracker, verbose=False, imgsz=640
        )[0]

        boxes = []
        if results.boxes.id is not None:
            for box, track_id in zip(results.boxes, results.boxes.id):
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((cls_name, x1, y1, x2, y2, int(track_id)))

        than_boxes = [b for b in boxes if b[0] == "than"]
        chan_boxes = [b for b in boxes if b[0] == "chan"]

        than_info = []
        for than in than_boxes:
            _, x1, y1, x2, y2, tid = than
            than_info.append({
                "box": than, "cx": (x1 + x2) / 2, "cy": (y1 + y2) / 2,
                "w": x2 - x1, "h": y2 - y1, "chans": [],
            })

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

        risky_track_ids = set()
        active_ids_this_frame = set()

        for t in than_info:
            than = t["box"]
            _, x1, y1, x2, y2, tid = than
            active_ids_this_frame.add(tid)
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

            flipped_this_frame = flipped_by_yrule or flipped_by_span

            flip_history[tid].append(flipped_this_frame)
            pos_history[tid].append((than_cx, than_cy))
            size_history[tid].append(than_h)

            hist = flip_history[tid]
            flip_ratio = sum(hist) / len(hist) if hist else 0.0

            positions = np.array(pos_history[tid])
            sizes = np.array(size_history[tid])
            is_still = True
            if len(positions) >= 5:
                std_x, std_y = positions[:, 0].std(), positions[:, 1].std()
                avg_h = sizes.mean() if len(sizes) else than_h
                move_ratio = (std_x + std_y) / 2 / max(avg_h, 1e-6)
                is_still = move_ratio < move_thresh

            enough_history = len(hist) >= max(3, int(effective_window * 0.4))
            is_confirmed_risk = enough_history and flip_ratio >= ratio and is_still

            if is_confirmed_risk:
                risky_track_ids.add(tid)
                if tid not in open_alerts:
                    open_alerts[tid] = frame_idx  # bắt đầu 1 đợt cảnh báo mới
            else:
                if tid in open_alerts:
                    # đợt cảnh báo vừa kết thúc -> chốt lại
                    start_f = open_alerts.pop(tid)
                    closed_alerts.append(_make_alert(tid, start_f, frame_idx - stride, fps))

        # Đóng các đợt cảnh báo của track đã biến mất hoàn toàn khỏi frame (bị mất track hẳn)
        for tid in list(open_alerts.keys()):
            if tid not in active_ids_this_frame:
                start_f = open_alerts.pop(tid)
                closed_alerts.append(_make_alert(tid, start_f, frame_idx - stride, fps))

        # Vẽ bounding box và nhãn trực quan, chính xác lên frame
        if writer or on_frame:
            for chan in chan_boxes:
                _, cx1, cy1, cx2, cy2, _ = chan
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 140, 255), 1)

            for t in than_info:
                _, x1, y1, x2, y2, tid = t["box"]
                is_abnormal = tid in risky_track_ids
                color = (0, 0, 255) if is_abnormal else (46, 125, 50)
                tag = f"BAT THUONG #{tid}" if is_abnormal else f"Vit #{tid}"
                thickness = 3 if is_abnormal else 2
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                badge_w = len(tag) * 11 + 6
                badge_h = 22
                cv2.rectangle(frame, (x1, max(0, y1 - badge_h)), (x1 + badge_w, y1), color, -1)
                cv2.putText(frame, tag, (x1 + 3, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        if writer:
            writer.write(frame)
        if on_frame:
            on_frame(frame, frame_idx, total_frames, list(risky_track_ids))

        frame_idx += 1

    # Chốt các đợt cảnh báo vẫn còn mở khi video kết thúc
    for tid, start_f in open_alerts.items():
        closed_alerts.append(_make_alert(tid, start_f, frame_idx - 1, fps))

    cap.release()
    if writer:
        writer.release()

    closed_alerts.sort(key=lambda a: a["start_frame"])

    return {
        "video_path": video_path,
        "fps": fps,
        "total_frames": total_frames,
        "duration_sec": total_frames / fps if fps else 0.0,
        "alerts": closed_alerts,
        "annotated_video_path": save_annotated_path,
    }


def _make_alert(track_id, start_frame, end_frame, fps):
    return {
        "track_id": track_id,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_time_sec": round(start_frame / fps, 2) if fps else 0.0,
        "end_time_sec": round(end_frame / fps, 2) if fps else 0.0,
        "duration_sec": round((end_frame - start_frame) / fps, 2) if fps else 0.0,
    }
