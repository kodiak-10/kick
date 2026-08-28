from __future__ import annotations

from typing import Dict, Optional, Tuple

import cv2
import numpy as np


def _subject_bounds(points: Dict[str, Tuple[float, float]]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def _torso_center(points: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    xs = [
        points["left_shoulder"][0],
        points["right_shoulder"][0],
        points["left_hip"][0],
        points["right_hip"][0],
    ]
    ys = [
        points["left_shoulder"][1],
        points["right_shoulder"][1],
        points["left_hip"][1],
        points["right_hip"][1],
    ]
    return float(sum(xs) / len(xs)), float(sum(ys) / len(ys))


def compute_subject_signature(frame: np.ndarray, points: Dict[str, Tuple[float, float]]):
    h, w = frame.shape[:2]
    x0 = int(max(0, min(points["left_shoulder"][0], points["left_hip"][0]) - 0.03 * w))
    x1 = int(min(w, max(points["right_shoulder"][0], points["right_hip"][0]) + 0.03 * w))
    y0 = int(max(0, min(points["left_shoulder"][1], points["right_shoulder"][1]) - 0.02 * h))
    y1 = int(min(h, max(points["left_hip"][1], points["right_hip"][1]) + 0.02 * h))
    patch = frame[y0:y1, x0:x1]
    if patch.size == 0 or patch.shape[0] < 8 or patch.shape[1] < 8:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [12, 8], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten().astype(np.float32)
    return hist


def update_target_lock(lock_state, points, full_body, vis_avg, body_span, signature):
    center = _torso_center(points)
    bounds = _subject_bounds(points)
    if lock_state is None:
        stable = 1 if full_body and vis_avg > 0.55 else 0
        return {
            "center": center,
            "body_span": float(body_span),
            "stable_frames": stable,
            "misses": 0,
            "lock_score": 0.0,
            "switch_risk": 0.0,
            "dist_ratio": 0.0,
            "size_ratio": 0.0,
            "appearance_score": 1.0 if signature is not None else 0.0,
            "locked": False,
            "bounds": bounds,
            "signature": signature,
        }

    prev_center = lock_state["center"]
    prev_span = max(1.0, float(lock_state["body_span"]))
    dx = center[0] - prev_center[0]
    dy = center[1] - prev_center[1]
    dist_ratio = float((dx * dx + dy * dy) ** 0.5 / max(prev_span, float(body_span), 1.0))
    size_ratio = float(abs(float(body_span) - prev_span) / prev_span)

    appearance_score = 0.0
    prev_signature = lock_state.get("signature")
    if signature is not None and prev_signature is not None:
        appearance_score = max(0.0, 1.0 - float(cv2.compareHist(prev_signature, signature, cv2.HISTCMP_BHATTACHARYYA)))
    elif signature is not None:
        appearance_score = 0.5

    consistent = (
        full_body
        and vis_avg > 0.55
        and dist_ratio < 0.85
        and size_ratio < 0.55
        and appearance_score >= 0.22
    )

    next_state = dict(lock_state)
    next_state["bounds"] = bounds
    next_state["dist_ratio"] = dist_ratio
    next_state["size_ratio"] = size_ratio
    next_state["appearance_score"] = appearance_score

    if consistent:
        alpha = 0.82
        next_state["center"] = (
            prev_center[0] * alpha + center[0] * (1 - alpha),
            prev_center[1] * alpha + center[1] * (1 - alpha),
        )
        next_state["body_span"] = prev_span * alpha + float(body_span) * (1 - alpha)
        next_state["stable_frames"] = min(40, int(next_state["stable_frames"]) + 1)
        next_state["misses"] = max(0, int(next_state["misses"]) - 1)
        next_state["switch_risk"] = max(0.0, 0.48 * dist_ratio + 0.20 * size_ratio + 0.32 * (1.0 - appearance_score))
        if signature is not None and prev_signature is not None:
            next_state["signature"] = 0.86 * prev_signature + 0.14 * signature
        elif signature is not None:
            next_state["signature"] = signature
    else:
        next_state["stable_frames"] = max(0, int(next_state["stable_frames"]) - 2)
        next_state["misses"] = int(next_state["misses"]) + 1
        next_state["switch_risk"] = min(1.0, max(dist_ratio, size_ratio, 1.0 - appearance_score))
        if full_body and next_state["misses"] > 18 and appearance_score >= 0.42:
            next_state["center"] = center
            next_state["body_span"] = float(body_span)
            next_state["stable_frames"] = 1
            next_state["misses"] = 0
            if signature is not None:
                next_state["signature"] = signature

    next_state["lock_score"] = max(
        0.0,
        min(1.0, float(next_state["stable_frames"]) / 8.0)
        * (1.0 - float(next_state["switch_risk"]))
        * max(0.25, appearance_score if signature is not None else 0.55),
    )
    next_state["locked"] = bool(next_state["stable_frames"] >= 8 and next_state["misses"] < 3 and appearance_score >= 0.22)
    return next_state
