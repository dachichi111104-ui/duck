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
):
    """
    Phân tích 1 video, trả về các đợt nghi ngờ lật ngửa.

    Tham số bắt buộc:
        video_path (str): đường dẫn video cần phân tích.
        model_path (str): đường dẫn file weight .pt (model YOLOv8 đã train).

    Tham số tuỳ chỉnh (đã có giá trị mặc định phù hợp, thường không cần đổi):
        conf (float): ngưỡng confidence detect (0.30 - đã kiểm chứng bằng sweep).
        margin (float): hệ số margin cho rule y-position.
        ratio (float): tỷ lệ frame dương tính trong window để xác nhận cảnh báo.
        window (int): số frame lịch sử giữ lại mỗi track (~1-1.5s).
        move_thresh (float): ngưỡng bất động TƯƠNG ĐỐI (theo chiều cao thân).
        span_ratio (float): ngưỡng tỷ lệ khoảng cách 2 chân / chiều rộng thân.
        tracker (str): "botsort.yaml" (mặc định, chịu rung/che khuất tốt hơn)
                       hoặc "bytetrack.yaml".

    Tham số tuỳ chọn cho tích hợp GUI:
        save_annotated_path (str | None): nếu truyền, lưu video có vẽ bbox +
            nhãn cảnh báo ra file này (dùng để xem lại/demo).
        on_frame (callable | None): callback gọi mỗi frame, chữ ký:
            on_frame(frame_bgr, frame_idx, total_frames, risky_track_ids)
            - frame_bgr: ảnh frame hiện tại (numpy array, BGR - dùng được trực
              tiếp với QImage/QPixmap trong PyQt6 để hiển thị preview)
            - frame_idx (int): chỉ số frame hiện tại (bắt đầu từ 0)
            - total_frames (int): tổng số frame trong video
            - risky_track_ids (list[int]): danh sách track_id đang bị cảnh báo
              NGHI NGỜ LẬT NGỬA ở frame này (rỗng nếu không có)
            Dùng callback này để cập nhật progress bar / preview trực tiếp
            trên giao diện, không cần đợi xử lý xong toàn bộ video.

    Trả về dict:
        {
            "video_path": str,
            "fps": float,
            "total_frames": int,
            "duration_sec": float,
            "alerts": [
                {
                    "track_id": int,
                    "start_frame": int,
                    "end_frame": int,
                    "start_time_sec": float,
                    "end_time_sec": float,
                    "duration_sec": float,
                },
                ...
            ],
            "annotated_video_path": str | None,  # None nếu không lưu
        }

        "alerts": mỗi phần tử là MỘT ĐỢT liên tục mà 1 track bị xác nhận nghi
        ngờ lật ngửa (từ frame bắt đầu đến frame kết thúc trạng thái đó).
        Danh sách rỗng nghĩa là không phát hiện ca nào trong video.

    Lưu ý quan trọng cho người tích hợp:
        - Đây là kết quả ở mức RULE-BASED HEURISTIC (không phải mô hình phân
          loại end-to-end), có thể có sai số. Khuyến nghị hiển thị cảnh báo
          kèm khả năng xác nhận thủ công, không tự động hành động one-way.
        - Model hiện train trên dữ liệu 1 trại, số lượng còn hạn chế - độ
          chính xác trên điều kiện quay khác (trại khác, ánh sáng khác) chưa
          được kiểm chứng đầy đủ.
    """
    model = YOLO(model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Không mở được video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = None
    if save_annotated_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(save_annotated_path, fourcc, fps, (w, h))

    flip_history = defaultdict(lambda: deque(maxlen=window))
    pos_history = defaultdict(lambda: deque(maxlen=window))
    size_history = defaultdict(lambda: deque(maxlen=window))

    # Theo dõi trạng thái cảnh báo để gộp thành các "đợt" liên tục
    open_alerts = {}  # track_id -> start_frame (đợt đang mở, chưa kết thúc)
    closed_alerts = []  # danh sách các đợt đã kết thúc

    MAX_DX_RATIO, MAX_DY_RATIO = 1.2, 1.0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(frame, conf=conf, persist=True,
                               tracker=tracker, verbose=False)[0]

        boxes = []
        if results.boxes.id is not None:
            for box, track_id in zip(results.boxes, results.boxes.id):
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((cls_name, x1, y1, x2, y2, int(track_id)))

        if writer or on_frame:
            for cls_name, x1, y1, x2, y2, tid in boxes:
                color = (0, 200, 0) if cls_name == "than" else (0, 165, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

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

        risky_track_ids = []

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

            enough_history = len(hist) >= max(5, int(window * 0.5))
            is_confirmed_risk = enough_history and flip_ratio >= ratio and is_still

            if is_confirmed_risk:
                risky_track_ids.append(tid)
                if tid not in open_alerts:
                    open_alerts[tid] = frame_idx  # bắt đầu 1 đợt cảnh báo mới
                if writer or on_frame:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(frame, f"NGHI LAT NGUA #{tid}", (x1, max(20, y1 - 20)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                if tid in open_alerts:
                    # đợt cảnh báo vừa kết thúc -> chốt lại
                    start_f = open_alerts.pop(tid)
                    closed_alerts.append(_make_alert(tid, start_f, frame_idx - 1, fps))

        # Đóng các đợt cảnh báo của track đã biến mất hoàn toàn khỏi frame (bị mất track hẳn)
        for tid in list(open_alerts.keys()):
            if tid not in active_ids_this_frame:
                start_f = open_alerts.pop(tid)
                closed_alerts.append(_make_alert(tid, start_f, frame_idx - 1, fps))

        if writer:
            writer.write(frame)
        if on_frame:
            on_frame(frame, frame_idx, total_frames, risky_track_ids)

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
