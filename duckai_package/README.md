# Duck Lật Ngửa Detector — Module tích hợp (bản demo)

Module nhận diện nguy cơ vịt bị lật ngửa từ video, dùng YOLOv8 (nhận diện
thân/chân) + tracking + rule hình học + kiểm tra theo thời gian. Đây là bản
demo để kiểm tra tích hợp vào phần mềm quản lý — **chưa phải bản cuối cùng**.

## Cài đặt

```bash
pip install -r requirements.txt
```

Cần thêm file weight model `best.pt` — copy từ dự án gốc vào cùng thư mục
với `duck_detector.py` (hoặc chỉ đường dẫn tuỳ ý khi gọi hàm).

## Cách dùng cơ bản

```python
from duck_detector import analyze_video

result = analyze_video(
    video_path="video_can_kiem_tra.mp4",
    model_path="best.pt",
)

for alert in result["alerts"]:
    print(f"Vịt #{alert['track_id']} nghi lật ngửa từ giây "
          f"{alert['start_time_sec']} đến {alert['end_time_sec']}")
```

## Kết quả trả về

Hàm `analyze_video()` trả về 1 dict:

```python
{
    "video_path": str,
    "fps": float,
    "total_frames": int,
    "duration_sec": float,
    "alerts": [
        {
            "track_id": int,          # ID con vịt trong video (chỉ có ý
                                       # nghĩa trong phạm vi video này)
            "start_frame": int,
            "end_frame": int,
            "start_time_sec": float,
            "end_time_sec": float,
            "duration_sec": float,
        },
        ...
    ],
    "annotated_video_path": str | None,
}
```

`alerts` rỗng (`[]`) nghĩa là không phát hiện ca nghi ngờ nào trong video.

## Tích hợp hiển thị trực tiếp lên GUI (PyQt6)

Nếu muốn hiện preview/progress bar trong lúc xử lý (thay vì đợi xong mới có
kết quả), dùng tham số `on_frame`:

```python
def on_frame(frame_bgr, frame_idx, total_frames, risky_track_ids):
    # frame_bgr là numpy array (OpenCV BGR) - convert sang QImage để hiển
    # thị trên QLabel, ví dụ:
    #   rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    #   qimg = QImage(rgb.data, w, h, QImage.Format.Format_RGB888)
    # risky_track_ids: list ID đang bị cảnh báo ở frame này -> có thể
    # dùng để bật đèn cảnh báo / phát âm thanh ngay lập tức.
    ...

result = analyze_video(video_path=..., model_path=..., on_frame=on_frame)
```

## Xem lại video có chú thích (debug/demo)

Truyền `save_annotated_path="output.mp4"` để lưu video có vẽ bbox + nhãn
cảnh báo, tiện xem lại kết quả bằng mắt.

## Giới hạn cần biết (quan trọng khi đánh giá tích hợp)

- Đây là **rule-based heuristic**, không phải model phân loại end-to-end —
  có thể có sai số, đặc biệt ở điều kiện quay khác với dữ liệu train.
- Model hiện train trên dữ liệu **1 trại duy nhất**, số lượng ảnh còn hạn
  chế — độ chính xác ở trại/ánh sáng/góc quay khác chưa được kiểm chứng.
- `track_id` chỉ có ý nghĩa trong PHẠM VI 1 VIDEO — không dùng để nhận diện
  lại cùng 1 con vịt ở video khác hoặc ngày khác.
- Cần GPU (khuyến nghị) để xử lý real-time; chạy CPU vẫn được nhưng chậm
  hơn — cần benchmark cụ thể nếu tích hợp vào luồng xử lý real-time từ
  camera trực tiếp.
- Đây là bản demo kiểm tra tích hợp — các tham số ngưỡng (`conf`, `ratio`,
  `move_thresh`, `span_ratio`...) có thể cần tinh chỉnh thêm khi có thêm
  dữ liệu thực tế.

## File trong gói này

- `duck_detector.py` — module chính, chứa hàm `analyze_video()`.
- `demo.py` — script ví dụ minh hoạ cách gọi.
- `requirements.txt` — danh sách thư viện cần cài.
- `best.pt` — **cần tự copy vào** (không kèm sẵn trong gói code).
