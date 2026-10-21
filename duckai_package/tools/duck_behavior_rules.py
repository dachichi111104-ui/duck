"""Configurable behavior rules. Outputs observations, never injury diagnoses."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuleConfig:
    min_flock_size: int = 4
    min_body_height_px: float = 12.0
    center_distance_ratio: float = 3.0
    neighbor_distance_ratio: float = 2.5
    relative_speed_max: float = 0.25
    own_speed_max_body_sec: float = 0.15
    active_peer_min_body_sec: float = 0.10
    suspect_after_sec: float = 30.0
    alert_after_sec: float = 40.0

    def validate(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.min_flock_size < 4 or int(self.min_flock_size) != self.min_flock_size:
            raise ValueError("min_flock_size must be an integer >= 4")
        if self.relative_speed_max >= 1:
            raise ValueError("relative_speed_max must be < 1")
        if self.alert_after_sec < self.suspect_after_sec:
            raise ValueError("alert_after_sec must be >= suspect_after_sec")
        return self


def load_config(path):
    if path is None:
        return RuleConfig().validate()
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    return RuleConfig(**data["rules"]).validate()


def load_metrics(path):
    """Read our CSV exports with explicit types; reject non-finite numbers."""
    rows = []
    text_keys = {"source", "action_from_export", "geometry_status", "motion_status",
                 "segment_reason", "relative_speed_status", "camera_status",
                 "behavior_motion_status", "behavior_relative_speed_status", "movement_reference"}
    bool_keys = {"bbox_clipped", "camera_motion_compensated"}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        for raw in csv.DictReader(stream):
            row = {}
            for key, value in raw.items():
                if key in text_keys or key.endswith("_status"):
                    row[key] = value or None
                elif key.endswith("_signal"):
                    if value not in ("True", "False", ""):
                        raise ValueError(f"Invalid signal {key}")
                    row[key] = None if value == "" else value == "True"
                elif key in bool_keys:
                    if value not in ("True", "False"):
                        raise ValueError(f"Invalid boolean {key}")
                    row[key] = value == "True"
                elif value == "":
                    row[key] = None
                else:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError(f"Non-finite value in {key}")
                    row[key] = number
            for key in ("frame_index", "track_id", "clip_segment_id", "segment_id"):
                number = row[key]
                if number < 0 or not number.is_integer():
                    raise ValueError(f"{key} must be a non-negative integer")
                row[key] = int(number)
            rows.append(row)
    return rows


def stabilize_motion(rows, fps, camera_frames, window_sec=1.0, jump_body=3.0):
    """Recompute speeds in a background-stabilized coordinate system.

    Camera records contain an inverse affine transform into the current epoch's
    reference frame. Failure starts a new epoch: never bridge unmeasured motion.
    A fixed-camera record is an explicit assumption, not automatic validation.
    """
    if fps <= 0 or window_sec <= 0:
        raise ValueError("FPS and motion window must be positive")
    by_frame = defaultdict(list)
    for row in rows:
        if "timestamp_sec" in row and abs(row["timestamp_sec"] - row["frame_index"] / fps) > 1e-5:
            raise ValueError("FPS does not match timestamps in metrics CSV")
        by_frame[int(row["frame_index"])].append(row.copy())
    histories = defaultdict(deque)
    previous = {}
    segments = defaultdict(int)
    output = []
    for index in sorted(by_frame):
        frame_rows = by_frame[index]
        camera = camera_frames[index]
        camera_valid = camera["status"] in ("compensated", "fixed_assumption")
        matrix = camera["inverse_affine"]
        height_scale = math.sqrt(abs(matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]))
        for row in frame_rows:
            tid = row["track_id"]
            time = index / fps
            x = matrix[0][0] * row["cx"] + matrix[0][1] * row["cy"] + matrix[0][2]
            y = matrix[1][0] * row["cx"] + matrix[1][1] * row["cy"] + matrix[1][2]
            height = row["body_height_px"] * height_scale
            hist = histories[tid]
            prior = previous.get(tid)
            identity = (camera["epoch"], row["clip_segment_id"])
            restarted = prior is not None and (prior[0] != index - 1 or prior[1] != identity or not prior[2])
            if hist and math.hypot(x - hist[-1][1], y - hist[-1][2]) / statistics.mean((height, hist[-1][3])) > jump_body:
                restarted = True
            if restarted or not camera_valid:
                hist.clear()
                if prior is not None:
                    segments[tid] += 1
            speed_px = speed_body = None
            status = "warming_up" if camera_valid else "camera_unavailable"
            if camera_valid:
                hist.append((time, x, y, height))
                while hist[0][0] < time - window_sec - 1e-9:
                    hist.popleft()
                span = time - hist[0][0]
                if len(hist) >= 2 and span + 1e-9 >= max(window_sec - 1 / fps, 1 / fps):
                    speed_px = math.hypot(x - hist[0][1], y - hist[0][2]) / span
                    speed_body = speed_px / statistics.mean(p[3] for p in hist)
                    status = "ok"
            previous[tid] = (index, identity, camera_valid)
            row.update({
                "camera_status": camera["status"],
                "camera_epoch": camera["epoch"],
                "camera_motion_compensated": camera["status"] == "compensated",
                "movement_reference": "background_stabilized" if camera["status"] == "compensated" else camera["status"],
                "behavior_motion_segment_id": segments[tid],
                "stabilized_cx": x, "stabilized_cy": y,
                "behavior_speed_px_sec": speed_px,
                "behavior_speed_body_sec": speed_body,
                "behavior_motion_status": status,
            })
        for row in frame_rows:
            peers = [r["behavior_speed_body_sec"] for r in frame_rows
                     if r["track_id"] != row["track_id"] and r["behavior_motion_status"] == "ok"]
            baseline = statistics.median(peers) if len(peers) >= 3 else None
            if row["behavior_speed_body_sec"] is None:
                status = "own_speed_unavailable"
            elif baseline is None:
                status = "insufficient_speed_peers"
            elif baseline <= 0.05:
                status = "low_activity_baseline"
            else:
                status = "ok"
            row["behavior_peer_median_speed_body_sec"] = baseline
            row["behavior_speed_peer_count"] = len(peers)
            row["behavior_relative_speed_status"] = status
            row["behavior_relative_speed"] = row["behavior_speed_body_sec"] / baseline if status == "ok" else None
        output.extend(frame_rows)
    return output


def fixed_camera_records(rows):
    return {int(row["frame_index"]): {"status": "fixed_assumption", "epoch": int(row["clip_segment_id"]),
                                       "inverse_affine": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]} for row in rows}


def evaluate_rules(rows, fps, config):
    """Continuous evidence only. Missing observations/ID changes reset timers.

    Returns annotated frame rows and all candidate intervals. Only intervals
    reaching suspect/alert time are events. Low motion alone is diagnostic data,
    never an injury or disease alert.
    """
    config.validate()
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Invalid FPS")
    by_frame = defaultdict(list)
    for row in rows:
        if "timestamp_sec" in row and abs(row["timestamp_sec"] - row["frame_index"] / fps) > 1e-5:
            raise ValueError("FPS does not match timestamps in metrics CSV")
        by_frame[int(row["frame_index"])].append(row.copy())
    episodes = {}
    intervals = []
    output = []

    def close(key, reason):
        event = episodes.pop(key)
        duration = event.pop("positive_frames") / fps
        event.pop("signature")
        event["duration_sec"] = round(duration, 6)
        event["start_time_sec"] = event["start_frame"] / fps
        event["end_time_exclusive_sec"] = (event["end_frame"] + 1) / fps
        event["end_reason"] = reason
        if event["behavior"] == "low_motion_observed":
            event["severity"] = "observation_only"
        elif duration + 1e-9 >= config.alert_after_sec:
            event["severity"] = "alert"
        elif duration + 1e-9 >= config.suspect_after_sec:
            event["severity"] = "suspect"
        else:
            event["severity"] = "observing"
        intervals.append(event)

    for index in sorted(by_frame):
        frame_rows = by_frame[index]
        tids = [r["track_id"] for r in frame_rows]
        if len(set(tids)) != len(tids):
            raise ValueError(f"Duplicate track ID at frame {index}")
        for key in list(episodes):
            if key[0] not in tids or episodes[key]["end_frame"] != index - 1:
                close(key, "missing_observation")
        for row in frame_rows:
            camera_ok = row.get("camera_status") in ("compensated", "fixed_assumption")
            geometry_ok = (camera_ok and row["geometry_status"] == "ok"
                           and row["visible_track_count"] >= config.min_flock_size
                           and row["body_height_px"] >= config.min_body_height_px
                           and not row["bbox_clipped"])
            isolated = None if not geometry_ok else (
                row["normalized_distance_median"] >= config.center_distance_ratio
                and row["normalized_neighbor_distance"] >= config.neighbor_distance_ratio)
            motion_ok = (geometry_ok and row.get("behavior_motion_status") == "ok"
                         and row.get("behavior_relative_speed_status") == "ok"
                         and row["behavior_peer_median_speed_body_sec"] >= config.active_peer_min_body_sec)
            slow = None if not motion_ok else (
                row["behavior_relative_speed"] <= config.relative_speed_max
                and row["behavior_speed_body_sec"] <= config.own_speed_max_body_sec)
            combined = False if isolated is False or slow is False else (None if isolated is None or slow is None else True)
            signature = (row["clip_segment_id"], row.get("behavior_motion_segment_id", row["segment_id"]))
            for behavior, signal in (("separation", isolated), ("low_motion_observed", slow),
                                     ("isolated_low_mobility", combined)):
                key = (row["track_id"], behavior)
                if key in episodes and episodes[key]["signature"] != signature:
                    close(key, "continuity_reset")
                if signal is True:
                    if key not in episodes:
                        episodes[key] = {"track_id": row["track_id"], "behavior": behavior,
                                         "clip_segment_id": row["clip_segment_id"], "signature": signature,
                                         "start_frame": index, "end_frame": index, "positive_frames": 0,
                                         "suspect_frame": None, "alert_frame": None}
                    event = episodes[key]
                    event["end_frame"] = index
                    event["positive_frames"] += 1
                    duration = event["positive_frames"] / fps
                    if behavior == "low_motion_observed":
                        status = "observation_only"
                    elif duration + 1e-9 >= config.alert_after_sec:
                        status = "alert"
                        if event["alert_frame"] is None:
                            event["alert_frame"] = index
                    elif duration + 1e-9 >= config.suspect_after_sec:
                        status = "suspect"
                    else:
                        status = "observing"
                    if behavior != "low_motion_observed" and duration + 1e-9 >= config.suspect_after_sec and event["suspect_frame"] is None:
                        event["suspect_frame"] = index
                else:
                    if key in episodes:
                        close(key, "unknown_evidence" if signal is None else "condition_cleared")
                    duration = 0.0
                    status = "unknown" if signal is None else "clear"
                row[behavior + "_signal"] = signal
                row[behavior + "_status"] = status
                row[behavior + "_continuous_sec"] = duration
            output.append(row)
    for key in list(episodes):
        close(key, "end_of_input")
    intervals.sort(key=lambda r: (r["start_frame"], r["track_id"], r["behavior"]))
    return output, intervals


def summarize_events(intervals):
    events = [i for i in intervals if i["severity"] in ("suspect", "alert")]
    return {
        "alerts": [i for i in events if i["severity"] == "alert"],
        "suspects": [i for i in events if i["severity"] == "suspect"],
        "candidate_interval_counts": dict(Counter(i["behavior"] for i in intervals)),
        "max_candidate_duration_sec": {
            b: max((i["duration_sec"] for i in intervals if i["behavior"] == b), default=0.0)
            for b in ("separation", "low_motion_observed", "isolated_low_mobility")
        },
    }
