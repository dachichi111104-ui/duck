"""
Demo cách gọi module duck_detector.py - dùng để bạn kiểm tra tích hợp.

Cách chạy:
    python demo.py --video test.mp4 --model best.pt

Kết quả in ra danh sách các đợt nghi ngờ lật ngửa (nếu có), và lưu video
có vẽ bbox/cảnh báo ra file demo_out.mp4 để xem lại.
"""

import argparse
from duck_detector import analyze_video


def progress_callback(frame, frame_idx, total_frames, risky_track_ids):
    """Ví dụ callback đơn giản: in tiến độ mỗi 30 frame.
    Trong app PyQt6 thật, thay đoạn print() này bằng code cập nhật
    progress bar / hiển thị frame lên QLabel (dùng frame trực tiếp,
    convert qua QImage)."""
    if frame_idx % 30 == 0:
        percent = frame_idx / total_frames * 100 if total_frames else 0
        flag = f" - CANH BAO: {risky_track_ids}" if risky_track_ids else ""
        print(f"  Đang xử lý: {percent:.0f}%{flag}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", default="demo_out.mp4")
    args = parser.parse_args()

    print(f"Đang phân tích {args.video} ...")
    result = analyze_video(
        video_path=args.video,
        model_path=args.model,
        save_annotated_path=args.out,
        on_frame=progress_callback,
    )

    print("\n--- KẾT QUẢ ---")
    print(f"Thời lượng video: {result['duration_sec']:.1f}s ({result['total_frames']} frame)")
    print(f"Số đợt nghi ngờ lật ngửa: {len(result['alerts'])}")
    for a in result["alerts"]:
        print(f"  - Track #{a['track_id']}: {a['start_time_sec']}s -> {a['end_time_sec']}s "
              f"(kéo dài {a['duration_sec']}s)")
    print(f"\nVideo có chú thích đã lưu tại: {result['annotated_video_path']}")


if __name__ == "__main__":
    main()
