"""Offline geometry audit of a NESTLER tracker export. No disease classification.

Run with Python 3.11 and opencv-python. All calculations except video I/O use
the standard library. The input JSON/video are never changed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Observation:
    frame_index: int
    track_id: int
    assembly_id: int | None
    x1: float
    y1: float
    x2: float
    y2: float
    clipped: bool
    action: str | None
    confidence: float | None = None
    source: str = "nestler_tracker_export"

    @property
    def cx(self):
        return (self.x1 + self.x2) / 2

    @property
    def cy(self):
        return (self.y1 + self.y2) / 2

    @property
    def height(self):
        return self.y2 - self.y1


@dataclass(frozen=True)
class Config:
    speed_window_sec: float = 1.0
    jump_threshold_body: float = 3.0
    min_flock_size: int = 3
    min_speed_peers: int = 3
    flock_speed_floor_body_sec: float = 0.05
    segment_start_frames: tuple[int, ...] = ()


def positive_number(value, name):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def integer_id(value):
    if value is None or isinstance(value, bool):
        raise ValueError("Missing/boolean identifier")
    number = float(value)
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        raise ValueError("Identifier must be a non-negative integer")
    return int(number)


def parse_annotation(data):
    """Column 4 indexes actions/tracks; column 5 is a frame assembly index.

    Counts of distinct values alone cannot establish these meanings. This
    mapping follows the inspected export: actions keys use column 4, and
    column 5 repeatedly moves to a different spatial object on adjacent frames.
    """
    width = positive_number(data.get("frame_width"), "frame_width")
    height = positive_number(data.get("frame_height"), "frame_height")
    frames = data.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("JSON must contain a non-empty frames list")
    declared_count = data.get("frames_count")
    if declared_count is not None and integer_id(declared_count) != len(frames):
        raise ValueError("JSON frames_count does not match frames list length")

    audit = Counter()
    rejected = []
    parsed = []
    previous_index = -1
    for frame in frames:
        index = integer_id(frame.get("frame_index"))
        if index <= previous_index:
            raise ValueError("frame_index must be unique and strictly increasing")
        previous_index = index
        raw_rows = frame.get("tracks_bbox", [])
        if not isinstance(raw_rows, list):
            raise ValueError(f"tracks_bbox at frame {index} must be a list")
        actions = frame.get("actions") or {}
        if not isinstance(actions, dict):
            raise ValueError(f"actions at frame {index} must be an object")
        observations = []
        for row in raw_rows:
            audit["raw_rows"] += 1
            try:
                if not isinstance(row, list) or len(row) != 6:
                    raise ValueError("Expected six values: x1,y1,x2,y2,track_id,assembly_id")
                if any(v is None or isinstance(v, bool) for v in row[:4]):
                    raise ValueError("Missing/boolean box coordinate")
                x1, y1, x2, y2 = (float(v) for v in row[:4])
                if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
                    raise ValueError("Non-finite box coordinate")
                if x1 >= x2 or y1 >= y2:
                    raise ValueError("Box has non-positive area")
                tid = integer_id(row[4])
                assembly_id = integer_id(row[5])
                clipped_coords = (
                    min(max(x1, 0), width), min(max(y1, 0), height),
                    min(max(x2, 0), width), min(max(y2, 0), height),
                )
                if clipped_coords[0] >= clipped_coords[2] or clipped_coords[1] >= clipped_coords[3]:
                    raise ValueError("Box lies outside image")
                clipped = clipped_coords != (x1, y1, x2, y2)
                action = actions.get(str(tid))
                if action is not None and not isinstance(action, str):
                    audit["unsupported_action_values"] += 1
                    action = None
                observations.append(Observation(index, tid, assembly_id, *clipped_coords, clipped, action))
            except (ValueError, TypeError, OverflowError) as error:
                audit["invalid_rows"] += 1
                rejected.append({"frame_index": index, "reason": str(error), "row": row})
        # Ambiguous duplicate IDs must not contribute twice to the flock center.
        duplicates = {tid for tid, count in Counter(o.track_id for o in observations).items() if count > 1}
        if duplicates:
            audit["frames_with_duplicate_ids"] += 1
        valid = []
        for observation in observations:
            if observation.track_id in duplicates:
                audit["duplicate_rows_removed"] += 1
                rejected.append({"frame_index": index, "reason": "Duplicate track_id in frame", "row": observation.track_id})
            else:
                valid.append(observation)
                audit["usable_rows"] += 1
                audit["clipped_rows"] += int(observation.clipped)
        parsed.append((index, valid))
    return parsed, dict(audit), rejected


def read_video_info(path):
    import cv2

    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open video: {path}")
        return {
            "fps": positive_number(capture.get(cv2.CAP_PROP_FPS), "video FPS"),
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
    finally:
        capture.release()


def resolve_timing(data, video_info, timebase):
    annotation_fps = positive_number(data.get("fps"), "annotation FPS")
    video_fps = positive_number(video_info["fps"], "video FPS")
    width = positive_number(data.get("frame_width"), "frame_width")
    height = positive_number(data.get("frame_height"), "frame_height")
    if (width, height) != (video_info["width"], video_info["height"]):
        raise ValueError("Annotation and video dimensions differ; no implicit rescaling")
    indices = [integer_id(f["frame_index"]) for f in data["frames"]]
    if max(indices) >= video_info["frame_count"]:
        raise ValueError("Annotation frame_index exceeds video length")
    chosen = video_fps if timebase == "video" else annotation_fps
    return {
        "timebase": timebase,
        "selected_fps": chosen,
        "video_fps": video_fps,
        "annotation_fps": annotation_fps,
        "fps_difference_percent_of_video": abs(video_fps - annotation_fps) / video_fps * 100,
        "annotation_frame_count": len(indices),
        "annotated_coverage_sec": len(indices) / chosen,
        "first_timestamp_sec": min(indices) / chosen,
        "last_timestamp_sec": max(indices) / chosen,
        "video_duration_sec": video_info["frame_count"] / video_fps,
        "alignment_assumption": "frame_index is the corresponding zero-based video frame, without sampling or offset",
    }


def calculate_metrics(frames, fps, config):
    """Raw image displacement only: never treated as disease or physical speed.

    Speed uses a contiguous one-second endpoint window rather than per-frame
    differences. Gaps and implausible position steps restart the window.
    Camera motion remains a confounder and is explicitly recorded in output.
    """
    fps = positive_number(fps, "selected FPS")
    positive_number(config.speed_window_sec, "speed_window_sec")
    positive_number(config.jump_threshold_body, "jump_threshold_body")
    positive_number(config.flock_speed_floor_body_sec, "flock_speed_floor_body_sec")
    if config.min_flock_size < 2 or config.min_speed_peers < 1:
        raise ValueError("min_flock_size >= 2 and min_speed_peers >= 1 required")
    histories = defaultdict(deque)
    segment_ids = defaultdict(int)
    previous_clip_ids = {}
    known_frames = {index for index, _ in frames}
    cut_frames = set(config.segment_start_frames)
    if any(integer_id(cut) not in known_frames for cut in cut_frames):
        raise ValueError("Each segment-start-frame must exist in annotation")
    clip_segment_id = 0
    clip_start_frame = frames[0][0]
    output = []

    for frame_index, observations in frames:
        if frame_index in cut_frames and frame_index != frames[0][0]:
            clip_segment_id += 1
            clip_start_frame = frame_index
        if not observations:
            continue
        time_sec = frame_index / fps
        enough_flock = len(observations) >= config.min_flock_size
        mean_cx = statistics.mean(o.cx for o in observations)
        mean_cy = statistics.mean(o.cy for o in observations)
        median_cx = statistics.median(o.cx for o in observations)
        median_cy = statistics.median(o.cy for o in observations)
        neighbor_info = {}
        if len(observations) >= 2:
            for obs in observations:
                other = min((o for o in observations if o.track_id != obs.track_id),
                            key=lambda o: math.hypot(o.cx - obs.cx, o.cy - obs.cy))
                neighbor_info[obs.track_id] = (other.track_id, math.hypot(other.cx - obs.cx, other.cy - obs.cy))
        nn_scale = statistics.median(d for _, d in neighbor_info.values()) if neighbor_info else None
        usable_scale = enough_flock and nn_scale is not None and nn_scale > 1e-9
        frame_rows = []
        for obs in observations:
            hist = histories[obs.track_id]
            segment_reason = "new_track"
            step_body = None
            status = "warming_up"
            if obs.track_id in previous_clip_ids and previous_clip_ids[obs.track_id] != clip_segment_id:
                hist.clear()
                segment_ids[obs.track_id] += 1
                segment_reason = "clip_boundary"
            if hist:
                prior_index, _, prior_x, prior_y, prior_height = hist[-1]
                if frame_index != prior_index + 1:
                    hist.clear()
                    segment_ids[obs.track_id] += 1
                    segment_reason = "observation_gap"
                else:
                    step_body = math.hypot(obs.cx - prior_x, obs.cy - prior_y) / statistics.mean((obs.height, prior_height))
                    if step_body > config.jump_threshold_body:
                        hist.clear()
                        segment_ids[obs.track_id] += 1
                        segment_reason = "position_jump"
                        status = "position_jump"
                    else:
                        segment_reason = "continuous"
            hist.append((frame_index, time_sec, obs.cx, obs.cy, obs.height))
            previous_clip_ids[obs.track_id] = clip_segment_id
            while hist and hist[0][1] < time_sec - config.speed_window_sec - 1e-9:
                hist.popleft()
            span = time_sec - hist[0][1]
            speed_px = speed_body = None
            # Permit fractional FPS to select the closest shorter full window.
            required_span = max(config.speed_window_sec - 1 / fps, 1 / fps)
            if len(hist) >= 2 and span + 1e-9 >= required_span:
                start = hist[0]
                speed_px = math.hypot(obs.cx - start[2], obs.cy - start[3]) / span
                speed_body = speed_px / statistics.mean(p[4] for p in hist)
                status = "ok"
            nearest_id, nearest_distance = neighbor_info.get(obs.track_id, (None, None))
            distance_mean = math.hypot(obs.cx - mean_cx, obs.cy - mean_cy)
            distance_median = math.hypot(obs.cx - median_cx, obs.cy - median_cy)
            frame_rows.append({
                "frame_index": frame_index,
                "timestamp_sec": time_sec,
                "clip_segment_id": clip_segment_id,
                "clip_segment_start_frame": clip_start_frame,
                "segment_timestamp_sec": (frame_index - clip_start_frame) / fps,
                "track_id": obs.track_id,
                "assembly_id": obs.assembly_id,
                "source": obs.source,
                "confidence": obs.confidence,
                "action_from_export": obs.action,
                "x1": obs.x1, "y1": obs.y1, "x2": obs.x2, "y2": obs.y2,
                "cx": obs.cx, "cy": obs.cy,
                "body_width_px": obs.x2 - obs.x1,
                "body_height_px": obs.height,
                "bbox_clipped": obs.clipped,
                "visible_track_count": len(observations),
                "flock_mean_cx": mean_cx, "flock_mean_cy": mean_cy,
                "flock_median_cx": median_cx, "flock_median_cy": median_cy,
                "distance_to_mean_center_px": distance_mean,
                "distance_to_median_center_px": distance_median,
                "nearest_track_id": nearest_id,
                "nearest_neighbor_distance_px": nearest_distance,
                "median_nearest_neighbor_px": nn_scale,
                "normalized_distance_mean": distance_mean / nn_scale if usable_scale else None,
                "normalized_distance_median": distance_median / nn_scale if usable_scale else None,
                "normalized_neighbor_distance": nearest_distance / nn_scale if usable_scale else None,
                "geometry_status": "ok" if usable_scale else "insufficient_flock_or_zero_scale",
                "segment_id": segment_ids[obs.track_id],
                "segment_reason": segment_reason,
                "step_distance_body": step_body,
                "speed_window_span_sec": span,
                "speed_px_sec": speed_px,
                "speed_body_sec": speed_body,
                "motion_status": status,
                "camera_motion_compensated": False,
            })
        for row in frame_rows:
            peers = [r["speed_body_sec"] for r in frame_rows
                     if r["track_id"] != row["track_id"] and r["motion_status"] == "ok"]
            baseline = statistics.median(peers) if len(peers) >= config.min_speed_peers else None
            if row["speed_body_sec"] is None:
                relative_status = "own_speed_unavailable"
            elif baseline is None:
                relative_status = "insufficient_speed_peers"
            elif baseline <= config.flock_speed_floor_body_sec:
                relative_status = "low_activity_baseline"
            else:
                relative_status = "ok"
            row["speed_peer_count"] = len(peers)
            row["peer_median_speed_body_sec"] = baseline
            row["relative_speed"] = row["speed_body_sec"] / baseline if relative_status == "ok" else None
            row["relative_speed_status"] = relative_status
        output.extend(frame_rows)
    return output


def summarize_tracks(rows, fps):
    groups = defaultdict(list)
    for row in rows:
        groups[row["track_id"]].append(row)
    result = []
    for tid, track_rows in sorted(groups.items()):
        runs = Counter(row["segment_id"] for row in track_rows)
        result.append({
            "track_id": tid,
            "observed_frames": len(track_rows),
            "first_frame": track_rows[0]["frame_index"],
            "last_frame": track_rows[-1]["frame_index"],
            "observed_time_sec": len(track_rows) / fps,
            "continuous_segments": len(runs),
            "clip_segments_seen": len({r["clip_segment_id"] for r in track_rows}),
            "longest_usable_contiguous_sec": max(runs.values()) / fps,
            "observation_gap_resets": sum(r["segment_reason"] == "observation_gap" for r in track_rows),
            "position_jump_resets": sum(r["segment_reason"] == "position_jump" for r in track_rows),
            "clip_boundary_resets": sum(r["segment_reason"] == "clip_boundary" for r in track_rows),
            "valid_speed_frames": sum(r["motion_status"] == "ok" for r in track_rows),
            "valid_relative_speed_frames": sum(r["relative_speed_status"] == "ok" for r in track_rows),
        })
    return result


def write_csv(path, rows):
    if not rows:
        raise ValueError("Cannot export empty metrics")
    # BOM allows Windows Excel to recognize UTF-8; values are not rounded in RAM.
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: round(v, 6) if isinstance(v, float) else v for k, v in row.items()})


def render_preview(video_path, output_path, rows, fps, video_info, on_progress=None):
    import cv2

    by_frame = defaultdict(list)
    for row in rows:
        by_frame[row["frame_index"]].append(row)
    final_frame = max(by_frame)
    capture = cv2.VideoCapture(str(video_path))
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (video_info["width"], video_info["height"]))
    decoded = 0
    try:
        if not capture.isOpened() or not writer.isOpened():
            raise ValueError("Cannot open preview input or output video")
        while decoded <= final_frame:
            success, image = capture.read()
            if not success:
                raise ValueError(f"Video decoding stopped early at frame {decoded}")
            frame_rows = by_frame.get(decoded, [])
            for row in frame_rows:
                color = (40, 210, 40) if row["motion_status"] == "ok" else (0, 180, 255)
                cv2.rectangle(image, (round(row["x1"]), round(row["y1"])),
                              (round(row["x2"]), round(row["y2"])), color, 2)
                label = f"ID {row['track_id']} {row['action_from_export'] or '?'}"
                cv2.putText(image, label, (round(row["x1"]), max(24, round(row["y1"]) - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            if frame_rows:
                row = frame_rows[0]
                mean_point = (round(row["flock_mean_cx"]), round(row["flock_mean_cy"]))
                median_point = (round(row["flock_median_cx"]), round(row["flock_median_cy"]))
                cv2.drawMarker(image, mean_point, (255, 0, 255), cv2.MARKER_CROSS, 30, 3)
                cv2.drawMarker(image, median_point, (255, 220, 0), cv2.MARKER_DIAMOND, 25, 3)
                nn = row["median_nearest_neighbor_px"]
                scale_text = f"{nn:.2f}px" if nn is not None else "N/A"
                segment_text = f" | clip segment={row['clip_segment_id']}"
            else:
                scale_text = "N/A"
                segment_text = ""
            header = [
                f"METRICS ONLY | frame {decoded} | file t={decoded / fps:.2f}s | visible={len(frame_rows)}{segment_text}",
                f"mean: magenta + | median: cyan diamond | median NN: {scale_text}",
                "green: speed window ready | orange: warm-up/jump | camera motion NOT corrected",
            ]
            cv2.rectangle(image, (0, 0), (video_info["width"], 100), (0, 0, 0), -1)
            for i, label in enumerate(header):
                cv2.putText(image, label, (12, 26 + i * 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.65, (255, 255, 255), 1, cv2.LINE_AA)
            writer.write(image)
            decoded += 1
            if on_progress and decoded % 100 == 0:
                on_progress(decoded, final_frame + 1)
    finally:
        capture.release()
        writer.release()
    # Reopen and verify encoding really produced the expected frames/dimensions.
    result = read_video_info(output_path)
    if result["frame_count"] != decoded or (result["width"], result["height"]) != (video_info["width"], video_info["height"]):
        raise ValueError("Preview verification failed: frame count or dimensions differ")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path, help="Raw video matching frame_index; not an annotated overlay")
    parser.add_argument("--out-dir", required=True, type=Path, help="A new or empty directory; existing results are never overwritten")
    parser.add_argument("--timebase", required=True, choices=("video", "annotation"))
    parser.add_argument("--speed-window-sec", type=float, default=1.0)
    parser.add_argument("--jump-threshold-body", type=float, default=3.0)
    parser.add_argument("--flock-speed-floor-body-sec", type=float, default=0.05)
    parser.add_argument("--segment-start-frame", type=int, action="append", default=[],
                        help="First frame after a known cut/time jump. Repeat for multiple cuts; history resets across cuts.")
    parser.add_argument("--skip-preview", action="store_true")
    args = parser.parse_args()
    try:
        with args.annotation.open("r", encoding="utf-8-sig") as stream:
            data = json.load(stream)
        frames, audit, rejected = parse_annotation(data)
        video_info = read_video_info(args.video)
        timing = resolve_timing(data, video_info, args.timebase)
        config = Config(speed_window_sec=args.speed_window_sec,
                        jump_threshold_body=args.jump_threshold_body,
                        flock_speed_floor_body_sec=args.flock_speed_floor_body_sec,
                        segment_start_frames=tuple(sorted(set(args.segment_start_frame))))
        rows = calculate_metrics(frames, timing["selected_fps"], config)
        if not rows:
            raise ValueError("No usable observations")
        tracks = summarize_tracks(rows, timing["selected_fps"])
        if args.out_dir.exists() and (not args.out_dir.is_dir() or any(args.out_dir.iterdir())):
            raise ValueError("out-dir must be new or empty. Choose another name to preserve previous results.")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": 1,
            "status": "metrics_written_preview_pending" if not args.skip_preview else "complete",
            "purpose": "offline geometry and tracking audit; no behavior/disease alert thresholds",
            "inputs": {"annotation": str(args.annotation.resolve()), "video": str(args.video.resolve())},
            "identifier_mapping": {"track_id_column_zero_based": 4, "assembly_id_column_zero_based": 5,
                                   "evidence": "actions keys and adjacent-frame spatial continuity; no guaranteed bird identity"},
            "label_provenance": "tracker/postprocessed export; manual ground truth is not established",
            "timing": timing,
            "video_info": video_info,
            "config": vars(config),
            "audit": audit,
            "track_id_count": len(tracks),
            "assembly_index_count": len({r["assembly_id"] for r in rows}),
            "visible_count": {"min": min(len(o) for _, o in frames),
                              "max": max(len(o) for _, o in frames),
                              "mean": statistics.mean(len(o) for _, o in frames)},
            "action_counts": dict(Counter(r["action_from_export"] for r in rows if r["action_from_export"] is not None)),
            "clip_segments": [{"clip_segment_id": segment,
                               "first_annotated_frame": min(i for i, _ in frames if i >= start and (end is None or i < end)),
                               "annotated_frames": sum(start <= i and (end is None or i < end) for i, _ in frames)}
                              for segment, (start, end) in enumerate(zip(
                                  [frames[0][0]] + [c for c in config.segment_start_frames if c > frames[0][0]],
                                  [c for c in config.segment_start_frames if c > frames[0][0]] + [None]))],
            "longest_usable_contiguous_track_sec": max(t["longest_usable_contiguous_sec"] for t in tracks),
            "speed_available_rows": sum(r["motion_status"] == "ok" for r in rows),
            "relative_speed_available_rows": sum(r["relative_speed_status"] == "ok" for r in rows),
            "limitations": [
                "Distinct tracker IDs are not a count of animals; fragmentation/switching is possible",
                "No camera motion compensation or ground-plane/perspective calibration",
                "Speed is image displacement over a window, not physical velocity or limb movement",
                "Frame/video alignment assumes no frame sampling or offset; inspect preview",
                "Timestamps measure encoded video playback, not CCTV wall-clock time; supplied cut boundaries reset motion history",
                "Action labels are not disease labels and are not assumed manually verified",
                "Chosen motion quality settings are exploratory, not clinically validated thresholds",
            ],
        }
        write_csv(args.out_dir / "frame_metrics.csv", rows)
        write_csv(args.out_dir / "track_summary.csv", tracks)
        (args.out_dir / "rejected_rows.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest_path = args.out_dir / "summary.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Timebase: {args.timebase}; video FPS={video_info['fps']:.6f}; JSON FPS={timing['annotation_fps']:.6f}", flush=True)
        print(f"Coverage: {timing['annotated_coverage_sec']:.2f}s; IDs={len(tracks)}; rows={len(rows)}; clipped={audit.get('clipped_rows', 0)}", flush=True)
        if not args.skip_preview:
            manifest["preview_info"] = render_preview(args.video, args.out_dir / "metrics_preview.mp4", rows,
                                                     timing["selected_fps"], video_info,
                                                     lambda done, total: print(f"Preview: {done}/{total} frames", flush=True))
            manifest["status"] = "complete"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Completed: {args.out_dir.resolve()}")
        return 0
    except (ValueError, OSError, TypeError, KeyError, ImportError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
