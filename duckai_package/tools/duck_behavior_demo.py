"""Run current duck detector + BoT-SORT + experimental behavior rules offline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from duck_behavior_rules import (evaluate_rules, fixed_camera_records, load_config,
                                 load_metrics, stabilize_motion, summarize_events)
from duck_camera_motion import BackgroundMotion
from nestler_metrics import Config, Observation, calculate_metrics, read_video_info, summarize_tracks, write_csv


def collect_duck_tracks(video_path, model_path, tracker_path, conf, max_frames, camera_mode, cuts, progress=None):
    import cv2
    from ultralytics import YOLO

    if not model_path.is_file():
        raise ValueError(f"Model file not found: {model_path}")
    if not tracker_path.is_file():
        raise ValueError(f"Tracker configuration not found: {tracker_path}")
    info = read_video_info(video_path)
    model = YOLO(str(model_path))
    if "than" not in model.names.values():
        raise ValueError(f"Expected class 'than', got {model.names}")
    motion = BackgroundMotion(camera_mode)
    frames = []
    cameras = {}
    capture = cv2.VideoCapture(str(video_path))
    try:
        index = 0
        while max_frames is None or index < max_frames:
            success, frame = capture.read()
            if not success:
                break
            if index in cuts and index > 0:
                motion.reset()
                # A cut must reset tracker identity, not only the behavior timer.
                if model.predictor is not None:
                    for tracker in getattr(model.predictor, "trackers", []):
                        tracker.reset()
            result = model.track(frame, conf=conf, imgsz=640, persist=True,
                                 tracker=str(tracker_path), verbose=False, save=False)[0]
            body_boxes = []
            observations = []
            for box in result.boxes:
                if model.names[int(box.cls[0])] != "than":
                    continue
                raw = [float(v) for v in box.xyxy[0].tolist()]
                body_boxes.append(raw)
                if box.id is None:
                    continue
                x1, y1, x2, y2 = raw
                clipped = (max(x1, 0), max(y1, 0), min(x2, info["width"]), min(y2, info["height"]))
                if clipped[0] >= clipped[2] or clipped[1] >= clipped[3]:
                    continue
                observations.append(Observation(index, int(box.id[0]), None, *clipped,
                                                clipped != tuple(raw), None, float(box.conf[0]), "duck_yolo_botsort"))
            frames.append((index, observations))
            cameras[index] = motion.update(frame, body_boxes)
            index += 1
            if progress and index % 100 == 0:
                progress(index, info["frame_count"] if max_frames is None else min(max_frames, info["frame_count"]))
    finally:
        capture.release()
    if not frames:
        raise ValueError("No video frames decoded")
    for cut in cuts:
        if cut >= len(frames) or cut < 0:
            raise ValueError("Cut frame outside processed video")
    return frames, cameras, info, model.names


def render_behavior_preview(video_path, path, rows, fps, info, processed_frames):
    import cv2

    by_frame = defaultdict(list)
    for row in rows:
        by_frame[row["frame_index"]].append(row)
    capture = cv2.VideoCapture(str(video_path))
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (info["width"], info["height"]))
    try:
        if not writer.isOpened():
            raise ValueError("Cannot create behavior preview")
        for index in range(processed_frames):
            success, image = capture.read()
            if not success:
                raise ValueError("Preview input decoding ended early")
            rows_here = by_frame.get(index, [])
            for row in rows_here:
                status = row["isolated_low_mobility_status"]
                if status not in ("observing", "suspect", "alert"):
                    status = row["separation_status"]
                    prefix = "SEP"
                    seconds = row["separation_continuous_sec"]
                else:
                    prefix = "SEP+SLOW"
                    seconds = row["isolated_low_mobility_continuous_sec"]
                if status == "alert":
                    color = (0, 0, 255)
                elif status == "suspect":
                    color = (0, 100, 255)
                elif status == "observing":
                    color = (0, 220, 255)
                elif status == "unknown":
                    color = (180, 180, 180)
                else:
                    color = (40, 200, 40)
                label = f"#{row['track_id']}"
                if status in ("observing", "suspect", "alert"):
                    label += f" {prefix} {seconds:.1f}s {status}"
                elif status == "unknown":
                    label += " insufficient data"
                cv2.rectangle(image, (round(row["x1"]), round(row["y1"])),
                              (round(row["x2"]), round(row["y2"])), color, 2)
                cv2.putText(image, label, (round(row["x1"]), max(90, round(row["y1"]) - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)
            cv2.rectangle(image, (0, 0), (info["width"], 78), (0, 0, 0), -1)
            camera = rows_here[0]["camera_status"] if rows_here else "no tracks"
            labels = [f"DUCK BEHAVIOR PROTOTYPE | frame {index} | {index / fps:.2f}s | camera: {camera}",
                      "grey: unknown | green: clear | yellow: observing | orange: suspect | red: alert",
                      "Behavior evidence only. Not a fracture/paralysis/infection diagnosis."]
            for line, label in enumerate(labels):
                cv2.putText(image, label, (8, 20 + 23 * line), cv2.FONT_HERSHEY_SIMPLEX,
                            0.44, (255, 255, 255), 1, cv2.LINE_AA)
            writer.write(image)
    finally:
        capture.release()
        writer.release()
    check = read_video_info(path)
    if check["frame_count"] != processed_frames:
        raise ValueError("Encoded preview frame count mismatch")
    return check


def write_table(path, rows, fallback_fields):
    if rows:
        write_csv(path, rows)
    else:
        import csv
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerow(fallback_fields)


def analyze_duck_behaviors(video_path, model_path, out_dir, config_path=None, conf=0.3,
                           camera_mode="background", max_frames=None, segment_start_frames=(),
                           tracker_path=None, on_progress=None, save_preview=True):
    """New prototype API; the existing lat-ngua analyze_video API stays separate.

    Two video passes: infer and measure first; then render cached behavior rows.
    This is offline analysis, not a real-time GUI callback API.
    """
    video_path, model_path, out_dir = Path(video_path), Path(model_path), Path(out_dir)
    config = load_config(config_path)
    tracker_path = Path(tracker_path or Path(__file__).resolve().parents[1] / "configs" / "duck_botsort.yaml")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise ValueError("Use a new/empty output directory")
    started = time.perf_counter()
    frames, cameras, info, names = collect_duck_tracks(video_path, model_path, tracker_path, conf,
                                                    max_frames, camera_mode, set(segment_start_frames), on_progress)
    metrics = calculate_metrics(frames, info["fps"], Config(segment_start_frames=tuple(sorted(set(segment_start_frames)))))
    corrected = stabilize_motion(metrics, info["fps"], cameras)
    evaluated, intervals = evaluate_rules(corrected, info["fps"], config)
    inference_elapsed = time.perf_counter() - started
    out_dir.mkdir(parents=True, exist_ok=True)
    write_table(out_dir / "frame_metrics.csv", corrected, ["frame_index", "track_id", "timestamp_sec"])
    write_table(out_dir / "rule_frame_states.csv", evaluated, ["frame_index", "track_id", "separation_status"])
    write_table(out_dir / "candidate_intervals.csv", intervals, ["track_id", "behavior", "start_frame", "end_frame", "duration_sec", "severity"])
    write_table(out_dir / "track_summary.csv", summarize_tracks(metrics, info["fps"]), ["track_id", "observed_frames"])
    result = {
        "schema_version": 1, "status": "complete" if not save_preview else "metrics_complete_preview_pending",
        "calibration_status": "uncalibrated_prototype",
        "video_path": str(video_path.resolve()), "model_path": str(model_path.resolve()),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "class_names": names, "fps": info["fps"], "source_total_frames": info["frame_count"],
        "processed_frames": len(frames), "duration_sec": len(frames) / info["fps"],
        "config": asdict(config), "tracker_config": tracker_path.read_text(encoding="utf-8"),
        "camera_mode": camera_mode, "camera_status_counts": dict(Counter(c["status"] for c in cameras.values())),
        "track_count": len({r["track_id"] for r in metrics}),
        "tracked_body_observations": len(metrics),
        "frames_with_no_body_tracks": sum(not points for _, points in frames),
        "frames_with_enough_flock_tracks": sum(len(points) >= config.min_flock_size for _, points in frames),
        "processed_frame_rate_including_camera_and_rules": len(frames) / inference_elapsed,
        "dependency_versions": {p: importlib.metadata.version(p) for p in ("ultralytics", "torch", "opencv-python", "numpy", "lap")},
        "segment_start_frames": sorted(set(segment_start_frames)),
        "limitations": ["No fracture, paralysis or infection diagnosis", "No validated event labels or accuracy estimate",
                        "Background affine stabilization is approximate; failure suppresses evidence",
                        "Missing detections, occlusion and changed IDs reset behavior timers",
                        "No ground-plane calibration; body-height normalization is approximate",
                        "This prototype tests the new behavior branch; the lat-ngua module is unchanged"],
        **summarize_events(intervals),
    }
    path = out_dir / "result.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if save_preview:
        result["preview_info"] = render_behavior_preview(video_path, out_dir / "behavior_preview.mp4", evaluated,
                                                       info["fps"], info, len(frames))
        result["status"] = "complete"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path)
    source.add_argument("--metrics-csv", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--fps", type=float)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=root / "configs" / "duck_behavior_rules.json")
    parser.add_argument("--tracker", type=Path, default=root / "configs" / "duck_botsort.yaml")
    parser.add_argument("--conf", type=float, default=0.3)
    parser.add_argument("--camera-mode", choices=("background", "fixed"), default="background")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--segment-start-frame", type=int, action="append", default=[])
    parser.add_argument("--skip-preview", action="store_true")
    args = parser.parse_args()
    try:
        if args.max_frames is not None and args.max_frames < 1:
            raise ValueError("max-frames must be positive")
        if not 0 < args.conf < 1:
            raise ValueError("conf must be between 0 and 1")
        if args.video:
            if args.model is None:
                raise ValueError("--video requires --model")
            result = analyze_duck_behaviors(args.video, args.model, args.out_dir, args.config, args.conf,
                                           args.camera_mode, args.max_frames, args.segment_start_frame, args.tracker,
                                           lambda done, total: print(f"Inference: {done}/{total} frames", flush=True),
                                           not args.skip_preview)
        else:
            if args.fps is None or not 0 < args.fps < 1000:
                raise ValueError("--metrics-csv requires a positive --fps")
            config = load_config(args.config)
            rows = load_metrics(args.metrics_csv)
            if rows and "behavior_motion_status" not in rows[0]:
                if args.camera_mode != "fixed":
                    raise ValueError("Uncorrected CSV requires --camera-mode fixed for a verified fixed-camera clip")
                rows = stabilize_motion(rows, args.fps, fixed_camera_records(rows))
            evaluated, intervals = evaluate_rules(rows, args.fps, config)
            if args.out_dir.exists() and (not args.out_dir.is_dir() or any(args.out_dir.iterdir())):
                raise ValueError("Use a new/empty output directory")
            args.out_dir.mkdir(parents=True, exist_ok=True)
            write_table(args.out_dir / "frame_metrics.csv", rows, ["frame_index", "track_id"])
            write_table(args.out_dir / "rule_frame_states.csv", evaluated, ["frame_index", "track_id"])
            write_table(args.out_dir / "candidate_intervals.csv", intervals, ["track_id", "behavior", "duration_sec", "severity"])
            result = {"status": "complete", "calibration_status": "uncalibrated_prototype", "fps": args.fps,
                      "metrics_source": str(args.metrics_csv.resolve()), "config": asdict(config), **summarize_events(intervals)}
            (args.out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Alerts: {len(result['alerts'])}; suspects: {len(result['suspects'])}")
        print(f"Completed: {args.out_dir.resolve()}")
    except (ValueError, OSError, TypeError, KeyError, ImportError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
