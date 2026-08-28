from __future__ import annotations

from typing import Dict, Optional, Tuple

import cv2
import numpy as np


def _roi_from_ankles(frame_shape, ankles: Optional[Dict[str, Tuple[float, float]]], last_ball: Optional[Dict[str, float]] = None):
    h, w = frame_shape[:2]
    if not ankles:
        if last_ball is None:
            return 0, int(h * 0.45), w, h
        pad = max(80, int(6.0 * float(last_ball.get("radius", 14.0))))
        cx = int(last_ball["x"])
        cy = int(last_ball["y"])
        return max(0, cx - pad), max(0, cy - pad), min(w, cx + pad), min(h, cy + pad)

    xs = [ankles["left_ankle"][0], ankles["right_ankle"][0]]
    ys = [ankles["left_ankle"][1], ankles["right_ankle"][1]]
    x0 = max(0, int(min(xs) - 0.18 * w))
    x1 = min(w, int(max(xs) + 0.18 * w))
    y0 = max(0, int(min(ys) - 0.16 * h))
    y1 = min(h, int(max(ys) + 0.10 * h))
    if x1 - x0 < int(0.28 * w):
        pad = int(0.14 * w)
        cx = int(sum(xs) * 0.5)
        x0 = max(0, cx - pad)
        x1 = min(w, cx + pad)
    if last_ball is not None:
        pad = max(50, int(5.5 * float(last_ball.get("radius", 14.0))))
        cx = int(last_ball["x"])
        cy = int(last_ball["y"])
        x0 = max(0, min(x0, cx - pad))
        y0 = max(0, min(y0, cy - pad))
        x1 = min(w, max(x1, cx + pad))
        y1 = min(h, max(y1, cy + pad))
    return x0, y0, x1, y1


def _candidate_score(
    hsv_roi: np.ndarray,
    gray_roi: np.ndarray,
    edges_roi: np.ndarray,
    center: Tuple[int, int],
    center_abs: Tuple[float, float],
    radius: int,
    last_ball: Optional[Dict[str, float]],
    ankles: Optional[Dict[str, Tuple[float, float]]],
):
    cx, cy = center
    mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radius, 255, -1)
    pixels = hsv_roi[mask > 0]
    if len(pixels) == 0:
        return -1.0

    sat = pixels[:, 1]
    val = pixels[:, 2]
    white_ratio = float(np.mean((sat < 110) & (val > 110)))
    bright_ratio = float(np.mean(val > 95))
    hue = pixels[:, 0]
    green_ratio = float(np.mean((hue > 32) & (hue < 96) & (sat > 70)))

    ring_mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)
    cv2.circle(ring_mask, (cx, cy), int(radius * 1.35), 255, -1)
    cv2.circle(ring_mask, (cx, cy), max(1, int(radius * 0.78)), 0, -1)
    ring_pixels = gray_roi[ring_mask > 0]
    core_pixels = gray_roi[mask > 0]
    contrast_score = 0.0
    edge_score = 0.0
    if len(ring_pixels) > 0 and len(core_pixels) > 0:
        contrast = abs(float(np.mean(core_pixels)) - float(np.mean(ring_pixels)))
        contrast_score = min(1.0, contrast / 55.0)
        edge_score = float(np.mean(edges_roi[ring_mask > 0] > 0))

    track_score = 0.0
    if last_ball is not None:
        pred_x = float(last_ball["x"]) + float(last_ball.get("vx", 0.0))
        pred_y = float(last_ball["y"]) + float(last_ball.get("vy", 0.0))
        dx = center_abs[0] - pred_x
        dy = center_abs[1] - pred_y
        dist = (dx * dx + dy * dy) ** 0.5
        track_score = max(0.0, 1.0 - dist / max(40.0, 4.0 * radius))
    radius_score = 0.5
    if last_ball is not None:
        prev_radius = max(1.0, float(last_ball.get("radius", radius)))
        radius_score = max(0.0, 1.0 - abs(radius - prev_radius) / prev_radius)

    foot_score = 0.0
    if ankles:
        dists = []
        for ankle in ankles.values():
            dx = center_abs[0] - ankle[0]
            dy = center_abs[1] - ankle[1]
            dists.append((dx * dx + dy * dy) ** 0.5)
        foot_score = max(0.0, 1.0 - min(dists) / max(60.0, 3.5 * radius))

    vertical_score = float(cy / max(1.0, float(hsv_roi.shape[0])))
    return (
        0.24 * white_ratio
        + 0.10 * bright_ratio
        + 0.24 * track_score
        + 0.13 * foot_score
        + 0.11 * contrast_score
        + 0.10 * edge_score
        + 0.05 * radius_score
        + 0.03 * vertical_score
        - 0.12 * green_ratio
    )


def detect_ball(
    frame: np.ndarray,
    ankles: Optional[Dict[str, Tuple[float, float]]] = None,
    last_ball: Optional[Dict[str, float]] = None,
):
    x0, y0, x1, y1 = _roi_from_ankles(frame.shape, ankles, last_ball=last_ball)
    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2.2)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    edges = cv2.Canny(gray, 70, 140)

    min_r = max(6, int(min(roi.shape[:2]) * 0.025))
    max_r = max(min_r + 2, int(min(roi.shape[:2]) * 0.16))
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(18, min_r * 2),
        param1=120,
        param2=16,
        minRadius=min_r,
        maxRadius=max_r,
    )
    if circles is None:
        return None

    best = None
    best_score = -1.0
    for c in np.round(circles[0]).astype(int):
        cx, cy, r = int(c[0]), int(c[1]), int(c[2])
        center_abs = (float(cx + x0), float(cy + y0))
        score = _candidate_score(hsv, gray, edges, (cx, cy), center_abs, r, last_ball, ankles)
        if score > best_score:
            best_score = score
            best = (cx, cy, r)

    if best is None or best_score < 0.18:
        return None

    cx, cy, r = best
    return {
        "x": float(cx + x0),
        "y": float(cy + y0),
        "radius": float(r),
        "confidence": float(min(0.99, max(0.0, best_score))),
        "source": "detected",
    }


class BallTracker:
    def __init__(self, max_misses: int = 5):
        self.max_misses = max_misses
        self.state: Optional[Dict[str, float]] = None

    def update(self, candidate: Optional[Dict[str, float]], body_span_px: float = 240.0):
        if self.state is None:
            if candidate is None:
                return None
            self.state = {
                "x": float(candidate["x"]),
                "y": float(candidate["y"]),
                "radius": float(candidate["radius"]),
                "vx": 0.0,
                "vy": 0.0,
                "confidence": float(candidate.get("confidence", 0.0)),
                "misses": 0.0,
                "source": "detected",
                "staleness": 0.0,
            }
            return dict(self.state)

        state = dict(self.state)
        pred_x = float(state["x"]) + float(state["vx"])
        pred_y = float(state["y"]) + float(state["vy"])
        gate = max(28.0, 0.25 * float(body_span_px), 4.0 * float(state["radius"]))

        accepted = False
        if candidate is not None:
            dx = float(candidate["x"]) - pred_x
            dy = float(candidate["y"]) - pred_y
            dist = float((dx * dx + dy * dy) ** 0.5)
            if dist <= gate or float(candidate.get("confidence", 0.0)) > 0.58:
                alpha = 0.42 + 0.18 * min(1.0, float(candidate.get("confidence", 0.0)))
                new_x = pred_x * (1.0 - alpha) + float(candidate["x"]) * alpha
                new_y = pred_y * (1.0 - alpha) + float(candidate["y"]) * alpha
                new_r = float(state["radius"]) * 0.65 + float(candidate["radius"]) * 0.35
                state["vx"] = float(state["vx"]) * 0.55 + (new_x - float(state["x"])) * 0.45
                state["vy"] = float(state["vy"]) * 0.55 + (new_y - float(state["y"])) * 0.45
                state["x"] = new_x
                state["y"] = new_y
                state["radius"] = new_r
                state["confidence"] = float(state["confidence"]) * 0.50 + float(candidate.get("confidence", 0.0)) * 0.50
                state["misses"] = 0.0
                state["source"] = "detected"
                state["staleness"] = 0.0
                accepted = True

        if not accepted:
            state["x"] = pred_x
            state["y"] = pred_y
            state["vx"] = float(state["vx"]) * 0.92
            state["vy"] = float(state["vy"]) * 0.92
            state["confidence"] = float(state["confidence"]) * 0.86
            state["misses"] = float(state["misses"]) + 1.0
            state["source"] = "predicted"
            state["staleness"] = float(state["staleness"]) + 1.0

        if float(state["misses"]) > float(self.max_misses) or float(state["confidence"]) < 0.10:
            self.state = None
            return None

        self.state = state
        return dict(state)


def estimate_contact(
    ball: Optional[Dict[str, float]],
    ankles: Dict[str, Tuple[float, float]],
    body_span_px: float,
):
    if ball is None:
        return {"side": "none", "distance_px": None, "contact": False}

    threshold = max(18.0, 0.04 * body_span_px) + 1.65 * float(ball["radius"])
    left_dx = float(ball["x"]) - ankles["left_ankle"][0]
    left_dy = float(ball["y"]) - ankles["left_ankle"][1]
    right_dx = float(ball["x"]) - ankles["right_ankle"][0]
    right_dy = float(ball["y"]) - ankles["right_ankle"][1]
    left_dist = (left_dx * left_dx + left_dy * left_dy) ** 0.5
    right_dist = (right_dx * right_dx + right_dy * right_dy) ** 0.5

    if min(left_dist, right_dist) > threshold:
        return {"side": "none", "distance_px": float(min(left_dist, right_dist)), "contact": False}
    if left_dist <= right_dist:
        return {"side": "left", "distance_px": float(left_dist), "contact": True}
    return {"side": "right", "distance_px": float(right_dist), "contact": True}


def draw_ball(frame: np.ndarray, ball: Optional[Dict[str, float]], contact=None):
    if ball is None:
        return
    center = (int(ball["x"]), int(ball["y"]))
    radius = int(ball["radius"])
    color = (0, 220, 255)
    if contact and contact.get("contact"):
        color = (0, 120, 255)
    thickness = 2
    if ball.get("source") == "predicted":
        color = (120, 180, 220)
        thickness = 1
    cv2.circle(frame, center, radius, color, thickness, cv2.LINE_AA)
    cv2.circle(frame, center, 2, color, -1, cv2.LINE_AA)
