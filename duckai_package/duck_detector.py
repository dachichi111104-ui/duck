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
    repeat_frames = 1
    if save_annotated_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # Video đầu ra được xuất ở tốc độ 10 FPS và nhân bản frame (0.5x slow-motion)
        # giúp người dùng và hội đồng thẩm định quan sát rõ nét từng chi tiết hành vi
        out_fps = 10.0
        repeat_frames = max(2, int(round((out_fps / max(1.0, effective_fps)) * 2.0)))
        writer = cv2.VideoWriter(save_annotated_path, fourcc, out_fps, (w, h))

    effective_window = max(5, int(round(effective_fps * 1.5)))
    flip_history = defaultdict(lambda: deque(maxlen=effective_window))
    pos_history = defaultdict(lambda: deque(maxlen=effective_window))
    size_history = defaultdict(lambda: deque(maxlen=effective_window))

    # Theo dõi trạng thái cảnh báo để gộp thành các "đợt" liên tục
    open_alerts = {}  # track_id -> start_frame
    alert_boxes = defaultdict(list)  # track_id -> [(cx, cy, w, h)]
    closed_alerts = []  # danh sách các đợt đã kết thúc

    # Bộ nhớ duy trì trạng thái cảnh báo (Hold-off / Grace period) chống hiện tượng nhấp nháy xanh - đỏ
    alert_grace_frames = defaultdict(int)
    grace_limit = max(10, int(round(effective_fps * 3.0)))  # Giữ đỏ ít nhất 3.0 giây

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

            # Phán đoán bất thường:
            # 1. Lật ngửa / té ngã: tỷ lệ lật >= 0.45 (không bắt buộc đứng im vì vịt lật ngửa thường co giật, đạp chân)
            # 2. Hoặc ủ rũ / bất động: đứng im lâu trong đàn
            is_flipped_risk = (flip_ratio >= 0.45)
            is_lethargic_risk = (is_still and len(positions) >= 6 and flip_ratio >= 0.25)
            enough_history = len(hist) >= max(3, int(effective_window * 0.35))

            is_confirmed_risk = enough_history and (is_flipped_risk or is_lethargic_risk)

            if is_confirmed_risk:
                alert_grace_frames[tid] = grace_limit
                risky_track_ids.add(tid)
                alert_boxes[tid].append((than_cx, than_cy, t["w"], t["h"]))
                if tid not in open_alerts:
                    open_alerts[tid] = frame_idx  # bắt đầu 1 đợt cảnh báo mới
            elif alert_grace_frames[tid] > 0:
                # Đang trong thời gian duy trì (Hold-off): giữ nguyên còi đỏ, chống chớp tắt xanh đỏ khi giãy giụa
                alert_grace_frames[tid] -= 1
                risky_track_ids.add(tid)
                alert_boxes[tid].append((than_cx, than_cy, t["w"], t["h"]))
            else:
                if tid in open_alerts:
                    # đợt cảnh báo vừa kết thúc -> chốt lại
                    start_f = open_alerts.pop(tid)
                    boxes_list = alert_boxes.pop(tid, [])
                    closed_alerts.append(_make_alert(tid, start_f, frame_idx - stride, fps, boxes_list))

        # Kế thừa cảnh báo khi Tracker bị nhảy ID tại cùng tọa độ vịt nằm
        for tid in active_ids_this_frame:
            if tid not in open_alerts and alert_grace_frames[tid] == 0:
                t_obj = next((x for x in than_info if x["box"][5] == tid), None)
                if t_obj:
                    tcx, tcy, th = t_obj["cx"], t_obj["cy"], t_obj["h"]
                    for old_tid, g_left in list(alert_grace_frames.items()):
                        if g_left > 0 and old_tid not in active_ids_this_frame:
                            if len(pos_history[old_tid]) > 0:
                                old_cx, old_cy = pos_history[old_tid][-1]
                                dist = np.sqrt((tcx - old_cx)**2 + (tcy - old_cy)**2)
                                if dist < max(th, 40.0) * 1.5:
                                    alert_grace_frames[tid] = g_left
                                    if old_tid in open_alerts:
                                        open_alerts[tid] = open_alerts.pop(old_tid)
                                    risky_track_ids.add(tid)
                                    break

        # Đóng các đợt cảnh báo của track đã biến mất hoàn toàn khỏi frame (bị mất track hẳn sau thời gian ân hạn)
        for tid in list(open_alerts.keys()):
            if tid not in active_ids_this_frame:
                if alert_grace_frames[tid] > 0:
                    alert_grace_frames[tid] -= 1
                else:
                    start_f = open_alerts.pop(tid)
                    boxes_list = alert_boxes.pop(tid, [])
                    closed_alerts.append(_make_alert(tid, start_f, frame_idx - stride, fps, boxes_list))

        # Vẽ OSD Banner trên đầu video hiển thị rõ Frame ID và Thống kê thời gian thực
        if writer or on_frame:
            # Header banner nền sẫm bán trong suốt
            cv2.rectangle(frame, (0, 0), (w, 36), (18, 22, 20), -1)
            banner_line_color = (0, 0, 220) if risky_track_ids else (46, 125, 50)
            cv2.line(frame, (0, 36), (w, 36), banner_line_color, 2)
            cur_time = frame_idx / fps if fps > 0 else 0.0
            osd_left = f"Frame ID: #{frame_idx:04d}/{total_frames:04d} | Thoi gian: {cur_time:05.2f}s | FPS: {fps:.1f}"
            osd_right = f"Tong vit: {len(than_info)} | Bat thuong: {len(risky_track_ids)}"
            cv2.putText(frame, osd_left, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, osd_right, (max(10, w - 270), 24), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 240, 255) if risky_track_ids else (120, 240, 120), 1, cv2.LINE_AA)

            for chan in chan_boxes:
                _, cx1, cy1, cx2, cy2, _ = chan
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 140, 255), 1)

            for t in than_info:
                _, x1, y1, x2, y2, tid = t["box"]
                is_abnormal = tid in risky_track_ids
                color = (0, 0, 220) if is_abnormal else (46, 125, 50)
                tag = f"[Box ID: #{tid}] BAT THUONG" if is_abnormal else f"[Box ID: #{tid}] Binh thuong"
                thickness = 3 if is_abnormal else 2
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                badge_w = len(tag) * 10 + 8
                badge_h = 24
                badge_y_top = max(38, y1 - badge_h)
                cv2.rectangle(frame, (x1, badge_y_top), (min(w, x1 + badge_w), badge_y_top + badge_h), color, -1)
                cv2.putText(frame, tag, (x1 + 4, badge_y_top + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        if writer:
            for _ in range(repeat_frames):
                writer.write(frame)
        if on_frame:
            on_frame(frame, frame_idx, total_frames, list(risky_track_ids))

        frame_idx += 1

    # Chốt các đợt cảnh báo vẫn còn mở khi video kết thúc
    for tid, start_f in open_alerts.items():
        boxes_list = alert_boxes.get(tid, [])
        closed_alerts.append(_make_alert(tid, start_f, frame_idx - 1, fps, boxes_list))

    cap.release()
    if writer:
        writer.release()

    closed_alerts.sort(key=lambda a: a["start_frame"])

    # Hợp nhất các track ID bị nhảy/căn lại box tại cùng một vị trí không gian thành 1 CÁ THỂ duy nhất
    merged_alerts = merge_spatial_temporal_alerts(closed_alerts)

    return {
        "video_path": video_path,
        "fps": fps,
        "total_frames": total_frames,
        "duration_sec": total_frames / fps if fps else 0.0,
        "alerts": merged_alerts,
        "annotated_video_path": save_annotated_path,
    }


def _make_alert(track_id, start_frame, end_frame, fps, boxes_list=None):
    cx = float(np.mean([b[0] for b in boxes_list])) if boxes_list else None
    cy = float(np.mean([b[1] for b in boxes_list])) if boxes_list else None
    w = float(np.mean([b[2] for b in boxes_list])) if boxes_list else None
    h = float(np.mean([b[3] for b in boxes_list])) if boxes_list else None
    return {
        "track_id": track_id,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_time_sec": round(start_frame / fps, 2) if fps else 0.0,
        "end_time_sec": round(end_frame / fps, 2) if fps else 0.0,
        "duration_sec": round((end_frame - start_frame) / fps, 2) if fps else 0.0,
        "cx": cx,
        "cy": cy,
        "w": w,
        "h": h,
    }


def merge_spatial_temporal_alerts(alerts, max_distance_ratio=0.85, max_gap_sec=25.0):
    """
    Hợp nhất các cảnh báo thuộc cùng 1 cá thể vịt:
    Khi vịt nằm bất động / lật ngửa, các khung hình bị che khuất hoặc tracker bị nhảy ID
    (Track fragmentation / ID switch) sẽ tạo ra nhiều track_id khác nhau tại CÙNG MỘT VỊ TRÍ.
    Hàm này nhóm lại theo khoảng cách tâm không gian (centroid distance) và khoảng thời gian,
    đảm bảo 1 con vịt thực tế chỉ được tính là 1 cá thể duy nhất.
    """
    if not alerts:
        return []

    import math

    alerts_sorted = sorted(alerts, key=lambda a: a["start_frame"])
    merged = []

    for alt in alerts_sorted:
        cx, cy = alt.get("cx"), alt.get("cy")
        w = alt.get("w") or 100.0
        h = alt.get("h") or 100.0
        matched_idx = None
        min_dist = float("inf")

        for idx, m in enumerate(merged):
            m_cx, m_cy = m.get("cx"), m.get("cy")
            m_w = m.get("w") or 100.0
            m_h = m.get("h") or 100.0

            if cx is not None and m_cx is not None:
                dist = math.hypot(cx - m_cx, cy - m_cy)
                avg_dim = (w + h + m_w + m_h) / 4.0
                time_gap = alt["start_time_sec"] - m["end_time_sec"]

                # Nếu cùng vị trí không gian (khoảng cách < 85% kích thước thân)
                # và thời gian không cách nhau quá max_gap_sec -> CÙNG 1 CON VỊT
                if dist <= avg_dim * max_distance_ratio and time_gap <= max_gap_sec:
                    if dist < min_dist:
                        min_dist = dist
                        matched_idx = idx

        if matched_idx is not None:
            m = merged[matched_idx]
            m["end_frame"] = max(m["end_frame"], alt["end_frame"])
            m["end_time_sec"] = max(m["end_time_sec"], alt["end_time_sec"])
            m["duration_sec"] = round(m["end_time_sec"] - m["start_time_sec"], 2)
            if cx is not None and m.get("cx") is not None:
                m["cx"] = (m["cx"] + cx) / 2.0
                m["cy"] = (m["cy"] + cy) / 2.0
            sub_tracks = m.setdefault("merged_track_ids", [m["track_id"]])
            if alt["track_id"] not in sub_tracks:
                sub_tracks.append(alt["track_id"])
        else:
            alt_copy = dict(alt)
            alt_copy["merged_track_ids"] = [alt["track_id"]]
            merged.append(alt_copy)

    # Đánh số cá thể riêng biệt: Cá thể #1, Cá thể #2...
    for i, m in enumerate(merged, start=1):
        m["individual_index"] = i

    return merged
