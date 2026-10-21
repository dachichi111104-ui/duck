"""Background-based affine camera motion for an offline behavior prototype."""

import math


class BackgroundMotion:
    def __init__(self, mode="background", analysis_width=640):
        import numpy as np

        if mode not in ("background", "fixed"):
            raise ValueError("Unknown camera mode")
        self.mode = mode
        self.width = analysis_width
        self.previous_gray = None
        self.previous_mask = None
        self.reference_to_current = np.eye(3)
        self.epoch = 0

    def reset(self):
        import numpy as np

        self.previous_gray = None
        self.previous_mask = None
        self.reference_to_current = np.eye(3)
        self.epoch += 1

    def update(self, image, body_boxes):
        import cv2
        import numpy as np

        identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        if self.mode == "fixed":
            return {"status": "fixed_assumption", "epoch": self.epoch,
                    "inverse_affine": identity, "inliers": None}
        scale = min(self.width / image.shape[1], 1.0)
        small = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        mask = np.full(gray.shape, 255, dtype=np.uint8)
        # Exclude detected bodies and a margin; legs are not background landmarks.
        for x1, y1, x2, y2 in body_boxes:
            margin = max(x2 - x1, y2 - y1) * 0.2
            left, top = max(0, round((x1 - margin) * scale)), max(0, round((y1 - margin) * scale))
            right, bottom = min(gray.shape[1], round((x2 + margin) * scale)), min(gray.shape[0], round((y2 + margin) * scale))
            mask[top:bottom, left:right] = 0
        status = "initializing"
        inlier_count = 0
        inverse = identity
        if self.previous_gray is not None:
            status = "unavailable"
            points = cv2.goodFeaturesToTrack(self.previous_gray, mask=self.previous_mask,
                                           maxCorners=300, qualityLevel=0.01, minDistance=8)
            if points is not None and len(points) >= 15:
                forward, valid_forward, _ = cv2.calcOpticalFlowPyrLK(self.previous_gray, gray, points, None)
                if forward is not None:
                    backward, valid_backward, _ = cv2.calcOpticalFlowPyrLK(gray, self.previous_gray, forward, None)
                    if backward is not None:
                        old = points.reshape(-1, 2)
                        new = forward.reshape(-1, 2)
                        good = ((valid_forward.ravel() == 1) & (valid_backward.ravel() == 1)
                                & (np.linalg.norm(old - backward.reshape(-1, 2), axis=1) < 1.5)
                                & np.isfinite(new).all(axis=1))
                        candidate_indices = np.flatnonzero(good)
                        for idx in candidate_indices:
                            x, y = new[idx]
                            if not (0 <= x < gray.shape[1] and 0 <= y < gray.shape[0]) or mask[int(y), int(x)] == 0:
                                good[idx] = False
                        if good.sum() >= 15:
                            affine, inliers = cv2.estimateAffinePartial2D(old[good], new[good], method=cv2.RANSAC,
                                                                         ransacReprojThreshold=2.5, maxIters=1000)
                            if affine is not None and np.isfinite(affine).all():
                                inlier_count = int(inliers.sum())
                                step_scale = math.hypot(affine[0, 0], affine[1, 0])
                                rotation = abs(math.degrees(math.atan2(affine[1, 0], affine[0, 0])))
                                translation = math.hypot(affine[0, 2], affine[1, 2])
                                plausible = (inlier_count >= 15 and inlier_count / good.sum() >= 0.5
                                             and 0.95 <= step_scale <= 1.05 and rotation <= 10
                                             and translation <= 0.15 * max(gray.shape))
                                if plausible:
                                    transform = np.eye(3)
                                    transform[:2, :2] = affine[:, :2]
                                    transform[:2, 2] = affine[:, 2] / scale
                                    combined = transform @ self.reference_to_current
                                    if abs(np.linalg.det(combined)) > 1e-9 and np.linalg.cond(combined[:2, :2]) < 100:
                                        self.reference_to_current = combined
                                        inverse = np.linalg.inv(combined)[:2].tolist()
                                        status = "compensated"
            if status != "compensated":
                self.reference_to_current = np.eye(3)
                self.epoch += 1
        self.previous_gray = gray
        self.previous_mask = mask
        return {"status": status, "epoch": self.epoch, "inverse_affine": inverse, "inliers": inlier_count}
