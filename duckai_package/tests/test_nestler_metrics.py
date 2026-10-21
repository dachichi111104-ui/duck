"""Checks against wrong IDs/clocks, gap bridging and false inactivity baselines."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from nestler_metrics import (Config, Observation, calculate_metrics,
                             parse_annotation, resolve_timing, summarize_tracks)


def obs(index, tid, cx, cy=100, height=10):
    return Observation(index, tid, tid, cx - 5, cy - height / 2,
                       cx + 5, cy + height / 2, False, None)


def annotation(rows):
    return {"fps": 18.8, "frame_width": 1920, "frame_height": 1080,
            "frames_count": 1,
            "frames": [{"frame_index": 0, "tracks_bbox": rows,
                        "actions": {"10": "walk"}}]}


class InputTests(unittest.TestCase):
    def test_track_id_uses_action_key_not_assembly_index(self):
        frames, _, _ = parse_annotation(annotation([[100, 100, 120, 130, 10, 12]]))
        point = frames[0][1][0]
        self.assertEqual((point.track_id, point.assembly_id, point.action), (10, 12, "walk"))

    def test_clip_small_border_overshoot_and_reject_nan(self):
        frames, audit, rejected = parse_annotation(annotation([
            [100, 1000, 120, 1084.42, 10, 12],
            [math.nan, 100, 120, 130, 11, 13],
        ]))
        self.assertEqual(frames[0][1][0].y2, 1080)
        self.assertTrue(frames[0][1][0].clipped)
        self.assertEqual(audit["clipped_rows"], 1)
        self.assertEqual(audit["invalid_rows"], 1)
        self.assertEqual(len(rejected), 1)

    def test_duplicate_id_is_removed_from_flock(self):
        frames, audit, _ = parse_annotation(annotation([
            [100, 100, 120, 130, 10, 12],
            [200, 100, 220, 130, 10, 13],
        ]))
        self.assertEqual(frames[0][1], [])
        self.assertEqual(audit["duplicate_rows_removed"], 2)

    def test_explicit_video_clock_is_not_json_clock(self):
        data = annotation([[100, 100, 120, 130, 10, 12]])
        video = {"fps": 20, "width": 1920, "height": 1080, "frame_count": 400}
        timing = resolve_timing(data, video, "video")
        self.assertEqual(timing["selected_fps"], 20)
        self.assertAlmostEqual(timing["annotated_coverage_sec"], 0.05)
        self.assertAlmostEqual(timing["fps_difference_percent_of_video"], 6)
        self.assertEqual(resolve_timing(data, video, "annotation")["selected_fps"], 18.8)

    def test_repeated_frames_and_video_overflow_fail(self):
        data = annotation([[100, 100, 120, 130, 10, 12]])
        data["frames"].append(data["frames"][0])
        data["frames_count"] = 2
        with self.assertRaises(ValueError):
            parse_annotation(data)
        data = annotation([[100, 100, 120, 130, 10, 12]])
        data["frames"][0]["frame_index"] = 400
        with self.assertRaises(ValueError):
            resolve_timing(data, {"fps": 20, "width": 1920, "height": 1080, "frame_count": 400}, "video")


class GeometryTests(unittest.TestCase):
    def test_even_median_averages_middle_two_without_rounding(self):
        frames = [(0, [obs(0, tid, x) for tid, x in enumerate([100, 102, 108, 114])])]
        rows = calculate_metrics(frames, 20, Config())
        # Nearest distances: 2,2,6,6 -> median 4, not the upper middle 6.
        self.assertEqual(rows[0]["median_nearest_neighbor_px"], 4)
        self.assertEqual(rows[-1]["normalized_neighbor_distance"], 1.5)

    def test_one_track_cannot_supply_flock_scale(self):
        rows = calculate_metrics([(0, [obs(0, 0, 100)])], 20, Config())
        self.assertIsNone(rows[0]["normalized_distance_mean"])
        self.assertIsNone(rows[0]["nearest_track_id"])


class TemporalTests(unittest.TestCase):
    def moving_flock(self, indices, stationary=False):
        return [(i, [obs(i, tid, 100 + tid * 200 + (0 if stationary and tid == 0 else i * 0.5))
                     for tid in range(4)]) for i in indices]

    def test_speed_has_time_units_and_equal_peers_ratio_one(self):
        rows = calculate_metrics(self.moving_flock(range(21)), 20, Config())
        first = rows[0]
        last = rows[-1]
        self.assertIsNone(first["speed_px_sec"])
        self.assertAlmostEqual(last["speed_px_sec"], 10)
        self.assertAlmostEqual(last["speed_body_sec"], 1)
        self.assertAlmostEqual(last["relative_speed"], 1)

    def test_stationary_individual_versus_moving_peers(self):
        rows = calculate_metrics(self.moving_flock(range(21), stationary=True), 20, Config())
        still = next(r for r in rows if r["frame_index"] == 20 and r["track_id"] == 0)
        self.assertEqual(still["relative_speed"], 0)
        self.assertEqual(still["speed_peer_count"], 3)

    def test_resting_flock_produces_no_relative_inactivity_claim(self):
        frames = [(i, [obs(i, tid, 100 + tid * 200) for tid in range(4)]) for i in range(21)]
        row = calculate_metrics(frames, 20, Config())[-1]
        self.assertEqual(row["relative_speed_status"], "low_activity_baseline")
        self.assertIsNone(row["relative_speed"])

    def test_one_frame_gap_restarts_speed_and_continuity(self):
        indices = list(range(21)) + list(range(22, 44))
        rows = calculate_metrics(self.moving_flock(indices), 20, Config())
        restart = next(r for r in rows if r["frame_index"] == 22 and r["track_id"] == 0)
        self.assertIsNone(restart["speed_px_sec"])
        self.assertEqual(restart["segment_reason"], "observation_gap")
        summary = summarize_tracks(rows, 20)[0]
        self.assertEqual(summary["continuous_segments"], 2)
        self.assertEqual(summary["observation_gap_resets"], 1)
        self.assertAlmostEqual(summary["longest_usable_contiguous_sec"], 22 / 20)

    def test_large_position_step_is_not_a_valid_speed(self):
        frames = self.moving_flock(range(21))
        frames.append((21, [obs(21, 0, 1200)]))
        row = calculate_metrics(frames, 20, Config())[-1]
        self.assertEqual(row["segment_reason"], "position_jump")
        self.assertEqual(row["motion_status"], "position_jump")
        self.assertIsNone(row["speed_px_sec"])

    def test_clip_cut_resets_even_a_spatially_stationary_continuous_id(self):
        frames = self.moving_flock(range(45))
        config = Config(segment_start_frames=(21,))
        rows = calculate_metrics(frames, 20, config)
        cut = next(r for r in rows if r["frame_index"] == 21 and r["track_id"] == 0)
        self.assertEqual(cut["segment_reason"], "clip_boundary")
        self.assertEqual(cut["clip_segment_id"], 1)
        self.assertEqual(cut["segment_timestamp_sec"], 0)
        self.assertIsNone(cut["speed_px_sec"])
        summary = summarize_tracks(rows, 20)[0]
        self.assertEqual(summary["clip_boundary_resets"], 1)
        self.assertEqual(summary["continuous_segments"], 2)
        self.assertAlmostEqual(summary["longest_usable_contiguous_sec"], 24 / 20)

    def test_unknown_clip_cut_is_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            calculate_metrics(self.moving_flock(range(21)), 20, Config(segment_start_frames=(30,)))


if __name__ == "__main__":
    unittest.main()
