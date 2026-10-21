"""Portable launcher for the current duck behavior demo and separate legacy mode."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("behavior", "lat-ngua"), default="behavior")
    parser.add_argument("--video", type=Path, help="Omit to select a video in a file dialog")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--max-frames", type=int, help="Behavior smoke test only, not a full evaluation")
    return parser.parse_args()


def select_video():
    import tkinter as tk
    from tkinter import filedialog
    window = tk.Tk()
    window.withdraw()
    try:
        selected = filedialog.askopenfilename(title="Chon video vit de chay demo",
                    filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")])
    finally:
        window.destroy()
    return Path(selected) if selected else None


def main():
    args = parse_args()
    if args.max_frames is not None and (args.max_frames < 1 or args.mode != "behavior"):
        raise ValueError("--max-frames must be positive and is supported only in behavior mode")
    video = args.video or select_video()
    if video is None:
        print("Cancelled: no video selected.")
        return
    video = video.resolve()
    if not video.is_file():
        raise FileNotFoundError(video)
    output = (args.out_dir or ROOT / "outputs" /
              (datetime.now().strftime("%Y%m%d_%H%M%S_") + args.mode + "_" + uuid4().hex[:6])).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output must be a new or empty directory; previous runs are not overwritten")
    tracker = ROOT / "configs" / "duck_botsort.yaml"
    if args.mode == "behavior":
        from duck_behavior_demo import analyze_duck_behaviors
        model = ROOT / "models" / "behavior_runA.pt"
        print("BEHAVIOR DEMO: suspect 30s / alert 40 continuous seconds. Not a diagnosis.", flush=True)
        result = analyze_duck_behaviors(video, model, output,
                  config_path=ROOT / "configs" / "duck_behavior_rules.json",
                  tracker_path=tracker, camera_mode="background", max_frames=args.max_frames,
                  on_progress=lambda done,total: print(f"Inference: {done}/{total}", flush=True))
    else:
        sys.path.insert(0, str(ROOT / "legacy"))
        from duck_detector import analyze_video
        model = ROOT / "models" / "lat_ngua_v1_5.pt"
        output.mkdir(parents=True, exist_ok=True)
        print("LEGACY LAT NGUA: original v1-5 weights and original rule. Separate from 40s behavior mode.", flush=True)
        result = analyze_video(str(video), str(model), tracker=str(tracker),
                               save_annotated_path=str(output / "lat_ngua_preview.mp4"))
        result.update({"mode": "lat-ngua", "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                       "notice": "Original legacy heuristic; not the 40-second behavior rule or a clinical diagnosis."})
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Finished. Alerts: {len(result['alerts'])}")
    print(f"Output: {output}")
    print("Open the preview MP4 after processing completes. No live camera or real-time GUI is provided.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
