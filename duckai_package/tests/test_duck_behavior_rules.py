"""False positives, timing/occlusion and camera motion are the key risks."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from duck_behavior_rules import RuleConfig, evaluate_rules, load_config, stabilize_motion, summarize_events
from duck_camera_motion import BackgroundMotion
from nestler_metrics import Config, Observation, calculate_metrics


def evidence(index, **overrides):
    row = {"frame_index": index, "track_id": 1, "clip_segment_id": 0, "segment_id": 0,
           "geometry_status": "ok", "visible_track_count": 8, "body_height_px": 60,
           "bbox_clipped": False, "normalized_distance_median": 4.0,
           "normalized_neighbor_distance": 3.0, "camera_status": "compensated",
           "behavior_motion_segment_id": 0, "behavior_motion_status": "ok",
           "behavior_relative_speed_status": "ok", "behavior_peer_median_speed_body_sec": 0.8,
           "behavior_relative_speed": 0.1, "behavior_speed_body_sec": 0.08}
    row.update(overrides)
    return row


class RuleTests(unittest.TestCase):
    def run_rows(self, rows, fps=2):
        # Preserve the original 60-second baseline regression checks below.
        states, intervals = evaluate_rules(rows, fps, RuleConfig(alert_after_sec=60))
        return states, summarize_events(intervals), intervals

    def test_demo_forty_seconds_not_forty_frames(self):
        for fps in (2, 30):
            with self.subTest(fps=fps):
                states, intervals = evaluate_rules([evidence(i) for i in range(40 * fps)], fps, RuleConfig())
                self.assertEqual(states[30 * fps - 2]["separation_status"], "observing")
                self.assertEqual(states[30 * fps - 1]["separation_status"], "suspect")
                self.assertEqual(states[40 * fps - 2]["separation_status"], "suspect")
                self.assertEqual(states[40 * fps - 1]["separation_status"], "alert")
                alerts = summarize_events(intervals)["alerts"]
                self.assertEqual(len(alerts), 2)
                self.assertTrue(all(e["duration_sec"] == 40 for e in alerts))
                self.assertTrue(all(e["alert_frame"] == 40 * fps - 1 for e in alerts))

    def test_demo_forty_seconds_still_requires_continuous_evidence(self):
        for kind in ("missing_frame", "changed_id"):
            with self.subTest(kind=kind):
                indices = list(range(79)) + list(range(80, 159)) if kind == "missing_frame" else list(range(158))
                rows = [evidence(i, track_id=2 if kind == "changed_id" and i >= 79 else 1) for i in indices]
                _, intervals = evaluate_rules(rows, 2, RuleConfig())
                result = summarize_events(intervals)
                self.assertEqual(result["alerts"], [])
                self.assertEqual(result["max_candidate_duration_sec"]["separation"], 39.5)

    def test_demo_config_changes_only_alert_time_from_saved_baseline(self):
        root = Path(__file__).resolve().parents[1] / "configs"
        current = load_config(root / "duck_behavior_rules.json")
        baseline = load_config(root / "duck_behavior_rules_baseline60.json")
        self.assertEqual(current, RuleConfig())
        self.assertEqual(load_config(None), current)
        self.assertEqual(current.suspect_after_sec, 30)
        self.assertEqual(current.alert_after_sec, 40)
        self.assertEqual(baseline.alert_after_sec, 60)
        from dataclasses import asdict
        current_rules, baseline_rules = asdict(current), asdict(baseline)
        current_rules.pop("alert_after_sec")
        baseline_rules.pop("alert_after_sec")
        self.assertEqual(current_rules, baseline_rules)

    def test_sixty_seconds_not_sixty_frames(self):
        _, results, _ = self.run_rows([evidence(i) for i in range(119)])
        self.assertEqual(len(results["alerts"]), 0)
        self.assertEqual(len(results["suspects"]), 2)
        _, results, _ = self.run_rows([evidence(i) for i in range(120)])
        self.assertEqual(len(results["alerts"]), 2)
        event = next(a for a in results["alerts"] if a["behavior"] == "isolated_low_mobility")
        self.assertEqual(event["duration_sec"], 60)
        self.assertEqual(event["suspect_frame"], 59)
        self.assertEqual(event["alert_frame"], 119)

    def test_far_from_center_but_near_neighbors_is_not_isolation(self):
        _, results, _ = self.run_rows([evidence(i, normalized_neighbor_distance=1.1) for i in range(180)])
        self.assertEqual(results["alerts"], [])
        self.assertEqual(results["suspects"], [])

    def test_low_motion_alone_cannot_be_an_alert(self):
        _, results, intervals = self.run_rows([evidence(i, normalized_distance_median=1.0) for i in range(180)])
        self.assertEqual(results["alerts"], [])
        self.assertEqual(results["suspects"], [])
        self.assertEqual({i["severity"] for i in intervals}, {"observation_only"})

    def test_resting_flock_does_not_prove_mobility_concern(self):
        rows = [evidence(i, behavior_peer_median_speed_body_sec=0,
                         behavior_relative_speed_status="low_activity_baseline",
                         behavior_relative_speed=None, behavior_speed_body_sec=0) for i in range(180)]
        states, result, _ = self.run_rows(rows)
        self.assertTrue(all(s["isolated_low_mobility_status"] == "unknown" for s in states))
        self.assertFalse(any(a["behavior"] == "isolated_low_mobility" for a in result["alerts"]))

    def test_missing_frame_resets_both_timers(self):
        rows = [evidence(i) for i in list(range(60)) + list(range(61, 122))]
        _, result, _ = self.run_rows(rows)
        self.assertEqual(result["alerts"], [])
        self.assertLess(result["max_candidate_duration_sec"]["separation"], 60)

    def test_changed_id_does_not_inherit_previous_time(self):
        rows = [evidence(i, track_id=1 if i < 60 else 2) for i in range(122)]
        _, result, _ = self.run_rows(rows)
        self.assertEqual(result["alerts"], [])

    def test_cut_same_id_starts_new_episode(self):
        rows = [evidence(i, clip_segment_id=0 if i < 60 else 1) for i in range(122)]
        _, result, intervals = self.run_rows(rows)
        self.assertEqual(result["alerts"], [])
        self.assertTrue(any(e["end_reason"] == "continuity_reset" for e in intervals))

    def test_camera_failure_is_unknown_and_resets_timer(self):
        rows = [evidence(i, camera_status="unavailable" if i == 60 else "compensated") for i in range(122)]
        states, result, _ = self.run_rows(rows)
        self.assertEqual(states[60]["separation_status"], "unknown")
        self.assertEqual(result["alerts"], [])

    def test_clipped_box_and_too_few_peers_block_decision(self):
        for override in ({"bbox_clipped": True}, {"visible_track_count": 3}):
            _, result, _ = self.run_rows([evidence(i, **override) for i in range(180)])
            self.assertEqual(result["alerts"], [])
            self.assertEqual(result["suspects"], [])

    def test_wrong_fps_for_cached_metrics_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_rules([evidence(20, timestamp_sec=1.0)], 30, RuleConfig())


class MotionTests(unittest.TestCase):
    def raw_rows(self, animal_motion=False):
        frames = []
        for i in range(24):
            points = []
            for tid in range(4):
                x = 100 + tid * 100 + i * 4 + (i if animal_motion and tid == 0 else 0)
                points.append(Observation(i, tid, None, x - 10, 100, x + 10, 120, False, None))
            frames.append((i, points))
        return calculate_metrics(frames, 20, Config())

    def cameras(self):
        return {i: {"status": "compensated", "epoch": 0,
                    "inverse_affine": [[1, 0, -4 * i], [0, 1, 0]]} for i in range(24)}

    def test_camera_translation_is_removed_from_static_birds(self):
        rows = stabilize_motion(self.raw_rows(), 20, self.cameras())
        last = rows[-1]
        self.assertGreater(last["speed_body_sec"], 0)
        self.assertAlmostEqual(last["behavior_speed_body_sec"], 0)
        self.assertIsNone(last["behavior_relative_speed"])

    def test_real_animal_motion_survives_camera_subtraction(self):
        rows = stabilize_motion(self.raw_rows(animal_motion=True), 20, self.cameras())
        moving = next(r for r in rows if r["frame_index"] == 23 and r["track_id"] == 0)
        self.assertAlmostEqual(moving["behavior_speed_body_sec"], 1)

    def test_failed_camera_frame_restarts_motion_window(self):
        cameras = self.cameras()
        cameras[20]["status"] = "unavailable"
        rows = stabilize_motion(self.raw_rows(), 20, cameras)
        failed = next(r for r in rows if r["frame_index"] == 20 and r["track_id"] == 0)
        recovered = next(r for r in rows if r["frame_index"] == 21 and r["track_id"] == 0)
        self.assertEqual(failed["behavior_motion_status"], "camera_unavailable")
        self.assertEqual(recovered["behavior_motion_status"], "warming_up")
        self.assertIsNone(recovered["behavior_speed_body_sec"])

    def test_background_estimator_recovers_known_image_translation(self):
        import cv2
        import numpy as np

        rng = np.random.default_rng(42)
        image = rng.integers(0, 256, size=(240, 320, 3), dtype=np.uint8)
        image = cv2.GaussianBlur(image, (3, 3), 0)
        moved = cv2.warpAffine(image, np.array([[1, 0, 2], [0, 1, 1]], dtype=np.float32), (320, 240))
        estimator = BackgroundMotion()
        self.assertEqual(estimator.update(image, []) ["status"], "initializing")
        result = estimator.update(moved, [])
        self.assertEqual(result["status"], "compensated")
        self.assertAlmostEqual(result["inverse_affine"][0][2], -2, delta=0.15)
        self.assertAlmostEqual(result["inverse_affine"][1][2], -1, delta=0.15)


if __name__ == "__main__":
    unittest.main()
