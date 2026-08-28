from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from time import perf_counter
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None

import numpy as np

from analysis.ball_tracking import BallTracker, detect_ball, estimate_contact
from analysis.analyzer_router import resolve_analysis_route
from analysis.action_decision import build_video_action_decision
from analysis.calibration import load_calibration
from analysis.long_video_locator import locate_long_video_action_windows
from analysis.football_scoring import score_football_action
from analysis.football_sequence import compute_football_kinematics, fresh_sequence_state, update_football_sequence
from analysis.score_levels import score_level_from_overall
from analysis.unified_analysis_result import (
    build_debug_context,
    normalize_failure_reason,
    select_best_analysis_payload,
    summarize_window,
)
from analysis.video_windowing import expand_locator_windows
from analysis.temporal_classifier import fresh_temporal_classifier_state, update_temporal_classifier
from feedback_engine import build_feedback_messages
from quality_gate import evaluate_global_quality_gate
from rules_loader import load_football_rules, resolve_action_name
from analysis.shot_rules import ShotIssue, build_shot_issues
from scoring_engine import score_action
from timestamp_error_locator import locate_error_timestamps

ANALYSIS_VERSION = "shot_engine_v1"
ACTION_TYPE = "shooting"
TEMPLATE_CODE = "shooting_quality"

_POSE_INDEX = {
    "nose": 0,
    "left_eye": 2,
    "right_eye": 5,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}


@dataclass(frozen=True)
class ShotScore:
    overall: float
    technical_execution: float
    control_stability: float
    action_safety: float
    level_code: str
    level_label: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(float(self.overall), 1),
            "technical_execution": round(float(self.technical_execution), 1),
            "control_stability": round(float(self.control_stability), 1),
            "action_safety": round(float(self.action_safety), 1),
            "level_code": self.level_code,
            "level_label": self.level_label,
        }


@dataclass(frozen=True)
class ShotAnalysisResult:
    action_type: str
    clip_id: str
    video_path: str
    analysis_version: str
    template_code: str
    generated_at: str
    duration_s: float
    frame_count: int
    score: ShotScore
    summary: str
    issues: List[ShotIssue]
    phase_scores: Dict[str, float]
    analysis_confidence: float
    status: str
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_version": self.analysis_version,
            "action_type": self.action_type,
            "clip_id": self.clip_id,
            "video_path": self.video_path,
            "template_code": self.template_code,
            "generated_at": self.generated_at,
            "duration_s": round(float(self.duration_s), 3),
            "frame_count": int(self.frame_count),
            "score": self.score.to_dict(),
            "overall_score": round(float(self.score.overall), 1),
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "phase_scores": {key: round(float(value), 1) for key, value in self.phase_scores.items()},
            "analysis_confidence": round(float(self.analysis_confidence), 3),
            "status": self.status,
            "warnings": list(self.warnings),
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return slug or "clip"


def _trim_letterbox(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h = gray.shape[0]
    top = 0
    while top < h // 3 and gray[top].mean() > 245 and gray[top].std() < 3:
        top += 1
    bottom = h - 1
    while bottom > (2 * h) // 3 and gray[bottom].mean() > 245 and gray[bottom].std() < 3:
        bottom -= 1
    if top > 5 or bottom < h - 6:
        return frame[top : bottom + 1, :]
    return frame


def _prepare_pose_frame(frame):
    h, w = frame.shape[:2]
    if w <= 1280:
        return frame
    scale = 1280 / float(w)
    new_size = (1280, max(1, int(h * scale)))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)


def _ema_points(prev_points: Optional[Dict[str, Tuple[float, float]]], points: Dict[str, Tuple[float, float]], alpha: float = 0.68):
    if prev_points is None:
        return points
    out = {}
    for key, value in points.items():
        prev = prev_points.get(key, value)
        out[key] = (prev[0] * alpha + value[0] * (1.0 - alpha), prev[1] * alpha + value[1] * (1.0 - alpha))
    return out


def _to_xy(landmark, w: int, h: int) -> Tuple[float, float]:
    return float(landmark.x * w), float(landmark.y * h)


def _full_body_ready(landmarks, frame_h: int) -> Tuple[bool, float]:
    required = [
        _POSE_INDEX["left_shoulder"],
        _POSE_INDEX["right_shoulder"],
        _POSE_INDEX["left_hip"],
        _POSE_INDEX["right_hip"],
        _POSE_INDEX["left_knee"],
        _POSE_INDEX["right_knee"],
        _POSE_INDEX["left_ankle"],
        _POSE_INDEX["right_ankle"],
    ]
    vis = [float(landmarks[idx].visibility) for idx in required]
    vis_ok = min(vis) > 0.55
    ys = [float(landmarks[idx].y * frame_h) for idx in required]
    body_span_ok = (max(ys) - min(ys)) > frame_h * 0.45
    return vis_ok and body_span_ok, float(sum(vis) / len(vis))


def _extract_points(landmarks, w: int, h: int) -> Tuple[Dict[str, Tuple[float, float]], float]:
    points = {
        name: _to_xy(landmarks[idx], w, h)
        for name, idx in _POSE_INDEX.items()
        if idx < len(landmarks)
    }
    vis = [
        float(landmarks[_POSE_INDEX[name]].visibility)
        for name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")
        if _POSE_INDEX[name] < len(landmarks)
    ]
    vis_avg = float(sum(vis) / len(vis)) if vis else 0.0
    return points, vis_avg


def _angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    cx, cy = c
    abx, aby = ax - bx, ay - by
    cbx, cby = cx - bx, cy - by
    dot = abx * cbx + aby * cby
    mag_ab = (abx * abx + aby * aby) ** 0.5
    mag_cb = (cbx * cbx + cby * cby) ** 0.5
    if mag_ab == 0.0 or mag_cb == 0.0:
        return 0.0
    cosang = max(-1.0, min(1.0, dot / (mag_ab * mag_cb)))
    return float(np.degrees(np.arccos(cosang)))


def _body_span(points: Dict[str, Tuple[float, float]]) -> float:
    return max(
        abs(points["left_shoulder"][1] - points["left_ankle"][1]),
        abs(points["right_shoulder"][1] - points["right_ankle"][1]),
        1.0,
    )


def _pose_metrics(points: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    l_knee = _angle(points["left_hip"], points["left_knee"], points["left_ankle"])
    r_knee = _angle(points["right_hip"], points["right_knee"], points["right_ankle"])
    symmetry = abs(l_knee - r_knee)

    shoulder_w = abs(points["left_shoulder"][0] - points["right_shoulder"][0]) + 1e-6
    shoulder_mid_x = (points["left_shoulder"][0] + points["right_shoulder"][0]) * 0.5
    hip_mid_x = (points["left_hip"][0] + points["right_hip"][0]) * 0.5
    shoulder_mid_y = (points["left_shoulder"][1] + points["right_shoulder"][1]) * 0.5
    hip_mid_y = (points["left_hip"][1] + points["right_hip"][1]) * 0.5

    balance = abs(shoulder_mid_x - hip_mid_x) / shoulder_w
    trunk_dx = shoulder_mid_x - hip_mid_x
    trunk_dy = max(1e-6, abs(shoulder_mid_y - hip_mid_y))
    trunk_lean_deg = abs(float(np.degrees(np.arctan2(abs(trunk_dx), trunk_dy))))

    knee_dist = abs(points["left_knee"][0] - points["right_knee"][0])
    ankle_dist = abs(points["left_ankle"][0] - points["right_ankle"][0]) + 1e-6
    valgus_ratio = knee_dist / ankle_dist

    return {
        "symmetry": float(symmetry),
        "balance": float(balance),
        "trunk_lean_deg": float(trunk_lean_deg),
        "valgus_ratio": float(valgus_ratio),
    }


def _safe_mean(values: Iterable[float], default: float = 0.0) -> float:
    vals = [float(v) for v in values if v is not None]
    return float(sum(vals) / len(vals)) if vals else float(default)


def _safe_min(values: Iterable[float], default: float = 0.0) -> float:
    vals = [float(v) for v in values if v is not None]
    return float(min(vals)) if vals else float(default)


def _safe_max(values: Iterable[float], default: float = 0.0) -> float:
    vals = [float(v) for v in values if v is not None]
    return float(max(vals)) if vals else float(default)


def _sample_time(samples: List[Dict[str, Any]], index: Optional[int], default: float = 0.0) -> float:
    if index is None or index < 0 or index >= len(samples):
        return float(default)
    return float(samples[index].get("time", default))


def _first_event_index(samples: List[Dict[str, Any]], event_name: str) -> Optional[int]:
    for idx, sample in enumerate(samples):
        if bool(sample.get("events", {}).get(event_name, False)):
            return idx
    return None


def _first_phase_index(samples: List[Dict[str, Any]], phase_name: str) -> Optional[int]:
    for idx, sample in enumerate(samples):
        if sample.get("phase") == phase_name:
            return idx
    return None


def _indices_between(start: Optional[int], end: Optional[int], total: int) -> List[int]:
    if total <= 0:
        return []
    s = 0 if start is None else max(0, start)
    e = total - 1 if end is None else min(total - 1, end)
    if e < s:
        return []
    return list(range(s, e + 1))


def _best_index(samples: List[Dict[str, Any]], metric: str, indices: List[int], mode: str = "max") -> Optional[int]:
    if not samples:
        return None
    if not indices:
        indices = list(range(len(samples)))
    best_idx: Optional[int] = None
    best_value: Optional[float] = None
    for idx in indices:
        value = samples[idx].get(metric)
        if value is None:
            continue
        value = float(value)
        if best_value is None:
            best_idx = idx
            best_value = value
            continue
        if mode == "min" and value < best_value:
            best_idx = idx
            best_value = value
        elif mode != "min" and value > best_value:
            best_idx = idx
            best_value = value
    return best_idx


def _issue_times(
    samples: List[Dict[str, Any]],
    *,
    support_window: List[int],
    contact_window: List[int],
    post_contact_window: List[int],
    support_event_idx: Optional[int],
    contact_event_idx: Optional[int],
    follow_event_idx: Optional[int],
    complete_event_idx: Optional[int],
) -> Dict[str, float]:
    issue_times: Dict[str, float] = {}

    support_far_idx = _best_index(samples, "support_ball_ratio", support_window, mode="max")
    support_close_idx = _best_index(samples, "support_ball_ratio", support_window, mode="min")
    trunk_idx = _best_index(samples, "trunk_lean_deg", contact_window, mode="max")
    follow_idx = _best_index(samples, "ball_speed_ratio", post_contact_window, mode="max")

    issue_times["support_foot_too_far"] = _sample_time(samples, support_far_idx, _sample_time(samples, support_event_idx))
    issue_times["support_foot_too_close"] = _sample_time(samples, support_close_idx, _sample_time(samples, support_event_idx))
    issue_times["upper_body_back_lean"] = _sample_time(samples, trunk_idx, _sample_time(samples, contact_event_idx))
    issue_times["follow_through_incomplete"] = _sample_time(
        samples,
        follow_idx,
        _sample_time(samples, follow_event_idx, _sample_time(samples, contact_event_idx)),
    )
    issue_times["stable_action"] = _sample_time(samples, complete_event_idx, _sample_time(samples, follow_event_idx, _sample_time(samples, contact_event_idx)))
    return issue_times


def _merge_triggered_rules(*groups: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("id") or item.get("rule_id") or item.get("metric") or "")
            key = rule_id
            if not rule_id or key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
    return merged


def _issue_triggered_rules(issues: List[ShotIssue]) -> List[Dict[str, Any]]:
    return [
        {
            "id": issue.id,
            "metric": issue.id,
            "label": issue.title,
            "severity": "warn" if issue.severity < 0.75 else "fail",
            "reason": issue.explanation,
            "phase": issue.phase,
            "time": round(float(issue.time), 3),
            "role": "primary",
            "quality_impact": "primary",
        }
        for issue in issues
    ]


def _build_rule_metrics(metrics: Dict[str, float], run_data: Dict[str, Any], action_quality) -> Dict[str, Any]:
    fps = float(run_data.get("fps", 30.0) or 30.0)
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.0))
    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28))
    stability = float(metrics.get("stability", 0.0))
    sequence_confidence = float(metrics.get("sequence_confidence", 0.0))
    trunk_lean_deg = float(metrics.get("trunk_lean_deg", 0.0))
    body_span_px = float(metrics.get("body_span_px", 1.0) or 1.0)
    scale_m_per_px = float(metrics.get("scale_m_per_px", 0.0) or run_data.get("scale_m_per_px", 0.0) or 0.0)
    overall = float(action_quality.overall_score)

    if overall >= 85.0:
        target_zone_hit = 3.0
    elif overall >= 70.0:
        target_zone_hit = 2.0
    elif overall >= 55.0:
        target_zone_hit = 1.0
    else:
        target_zone_hit = 0.0

    consistency_cv_pct = max(0.0, 100.0 * (1.0 - _clamp(0.65 * stability + 0.35 * sequence_confidence)))

    ball_speed_measurement_type = "proxy"
    ball_speed_value = max(0.0, ball_speed_ratio * fps * 2.0)
    if scale_m_per_px > 0.0:
        ball_speed_measurement_type = "calibrated"
        ball_speed_value = max(0.0, ball_speed_ratio * body_span_px * scale_m_per_px * fps)

    return {
        ("max_ball_speed_mps" if ball_speed_measurement_type == "calibrated" else "max_ball_speed_proxy_mps"): ball_speed_value,
        "ball_speed_measurement_type": ball_speed_measurement_type,
        "target_zone_hit": target_zone_hit,
        "shot_consistency_cv_pct": consistency_cv_pct,
        "support_foot_lateral_offset_cm": support_ball_ratio * 170.0,
        "support_foot_ap_offset_cm": (support_ball_ratio - 0.20) * 100.0,
        "trunk_lean_deg_at_impact_proxy": trunk_lean_deg,
    }


def _process_video(
    video_path: Path,
    frame_stride: int = 1,
    fast_mode_enabled: bool = False,
    frame_ranges: Optional[List[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    if cv2 is None or mp is None:
        return {
            "samples": [],
            "fps": 30.0,
            "frame_count": 0,
            "valid_pose_frames": 0,
            "ball_frames": 0,
            "contact_frames": 0,
            "active_frames": 0,
            "warnings": ["opencv_or_mediapipe_unavailable"],
        }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {
            "samples": [],
            "fps": 30.0,
            "frame_count": 0,
            "valid_pose_frames": 0,
            "ball_frames": 0,
            "contact_frames": 0,
            "active_frames": 0,
            "warnings": ["video_open_failed"],
        }

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if fps <= 0.0:
        fps = 30.0

    pose = None
    pose_init_warnings: List[str] = []
    pose_init_attempts = [
        {"model_complexity": 1, "smooth_landmarks": True},
        {"model_complexity": 0, "smooth_landmarks": True},
        {"model_complexity": 0, "smooth_landmarks": False},
    ]
    for attempt in pose_init_attempts:
        try:
            pose = mp.solutions.pose.Pose(
                model_complexity=attempt["model_complexity"],
                smooth_landmarks=attempt["smooth_landmarks"],
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            if attempt != pose_init_attempts[0]:
                pose_init_warnings.append("mediapipe_pose_fallback:" + json.dumps(attempt, ensure_ascii=False))
            break
        except Exception as exc:
            pose_init_warnings.append(f"mediapipe_pose_init_failed:{type(exc).__name__}:{json.dumps(attempt, ensure_ascii=False)}")
    if pose is None:
        return {
            "samples": [],
            "fps": fps,
            "frame_count": 0,
            "valid_pose_frames": 0,
            "ball_frames": 0,
            "contact_frames": 0,
            "active_frames": 0,
            "warnings": pose_init_warnings or ["mediapipe_pose_init_failed"],
        }

    source_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    video_duration_s = float(source_frame_count) / fps if source_frame_count > 0 and fps > 0.0 else 0.0
    if frame_ranges:
        analysis_stride = max(1, int(frame_stride))
        sample_windows = _normalize_frame_windows(frame_ranges)
    else:
        analysis_stride, sample_windows = _build_fast_mode_plan(
            frame_count=source_frame_count,
            fps=fps,
            duration_s=video_duration_s,
            frame_stride=frame_stride,
            fast_mode_enabled=fast_mode_enabled,
        )

    samples: List[Dict[str, Any]] = []
    warnings: List[str] = []
    warnings.extend(pose_init_warnings)
    ball_tracker = BallTracker(max_misses=6)
    sequence_state = fresh_sequence_state()
    temporal_state = fresh_temporal_classifier_state()
    prev_raw_points: Optional[Dict[str, Tuple[float, float]]] = None
    prev_points: Optional[Dict[str, Tuple[float, float]]] = None
    prev_ball: Optional[Dict[str, float]] = None
    move_hist = deque(maxlen=8)
    action_vote_counts: Dict[str, int] = {}
    best_temporal_prediction: Optional[Dict[str, Any]] = None
    last_sequence_snapshot: Optional[Dict[str, Any]] = None

    frame_idx = 0
    valid_pose_frames = 0
    ball_frames = 0
    contact_frames = 0
    active_frames = 0

    window_index = 0
    active_window: Optional[Tuple[int, int]] = sample_windows[0] if sample_windows else None

    def _reset_window_state() -> None:
        nonlocal prev_raw_points, prev_points, prev_ball, ball_tracker, sequence_state, temporal_state
        prev_raw_points = None
        prev_points = None
        prev_ball = None
        move_hist.clear()
        ball_tracker = BallTracker(max_misses=6)
        sequence_state = fresh_sequence_state()
        temporal_state = fresh_temporal_classifier_state()

    if active_window is not None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(active_window[0]))
        frame_idx = int(active_window[0])
        _reset_window_state()

    try:
        while True:
            if active_window is not None and frame_idx > active_window[1]:
                window_index += 1
                if window_index >= len(sample_windows):
                    break
                active_window = sample_windows[window_index]
                cap.set(cv2.CAP_PROP_POS_FRAMES, float(active_window[0]))
                frame_idx = int(active_window[0])
                _reset_window_state()
                continue

            ok, frame = cap.read()
            if not ok or frame is None:
                if active_window is not None:
                    window_index += 1
                    if window_index >= len(sample_windows):
                        break
                    active_window = sample_windows[window_index]
                    cap.set(cv2.CAP_PROP_POS_FRAMES, float(active_window[0]))
                    frame_idx = int(active_window[0])
                    _reset_window_state()
                    continue
                break

            sample_offset = frame_idx - active_window[0] if active_window is not None else frame_idx
            if analysis_stride > 1 and sample_offset % analysis_stride != 0:
                frame_idx += 1
                continue

            frame = _trim_letterbox(frame)
            frame = _prepare_pose_frame(frame)
            h, w = frame.shape[:2]
            now_t = frame_idx / fps

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                result = pose.process(rgb)
            except Exception as exc:
                warnings.append(f"mediapipe_pose_runtime_failed:{type(exc).__name__}")
                break

            raw_points: Optional[Dict[str, Tuple[float, float]]] = None
            vis_avg = 0.0
            full_body = False
            if result.pose_landmarks:
                landmarks = result.pose_landmarks.landmark
                raw_points, vis_avg = _extract_points(landmarks, w, h)
                full_body, vis_avg = _full_body_ready(landmarks, h)
                valid_pose_frames += 1 if full_body else 0
                if prev_raw_points is not None:
                    diffs = [
                        abs(raw_points[key][0] - prev_raw_points[key][0]) + abs(raw_points[key][1] - prev_raw_points[key][1])
                        for key in raw_points.keys()
                        if key in prev_raw_points
                    ]
                    if diffs:
                        move_hist.append(sum(diffs) / len(diffs))
                prev_raw_points = raw_points

            current_points = _ema_points(prev_points, raw_points) if raw_points is not None else prev_points
            if current_points is None:
                sample = {
                    "index": frame_idx,
                    "time": now_t,
                    "phase": "set",
                    "phase_confidence": 0.0,
                    "phase_locked": False,
                    "sequence_active": False,
                    "support_ball_ratio": 0.28,
                    "swing_ball_ratio": 0.16,
                    "ball_speed_ratio": 0.0,
                    "balance": 0.0,
                    "trunk_lean_deg": 0.0,
                    "valgus_ratio": 1.0,
                    "symmetry": 0.0,
                    "stability": 0.0,
                    "visibility": vis_avg,
                    "move_score": 0.0,
                    "body_span": 1.0,
                    "contact": False,
                    "contact_side": "none",
                    "support_side": "none",
                    "swing_side": "none",
                    "ball_x": None,
                    "ball_y": None,
                    "ball_vx": 0.0,
                    "ball_vy": 0.0,
                    "ball_radius": None,
                    "ball_confidence": 0.0,
                    "goal_visible": False,
                    "events": {
                        "support_plant": False,
                        "contact": False,
                        "follow_through_complete": False,
                        "sequence_complete": False,
                    },
                    "ball_present": False,
                }
                samples.append(sample)
                frame_idx += 1
                continue

            body_span = _body_span(current_points)
            move_score = _safe_mean(move_hist, default=0.0)
            move_ratio = move_score / max(1.0, body_span)
            stability = _clamp(1.0 - move_score / max(20.0, 0.12 * body_span))
            pose_metrics = _pose_metrics(current_points)

            ankles = {"left_ankle": current_points["left_ankle"], "right_ankle": current_points["right_ankle"]}
            ball_candidate = None
            if frame_idx % 2 == 0 or ball_tracker.state is None or float(ball_tracker.state.get("confidence", 0.0)) < 0.42 or ball_tracker.state.get("source") != "detected":
                ball_candidate = detect_ball(frame, ankles=ankles, last_ball=prev_ball)
            tracked_ball = ball_tracker.update(ball_candidate, body_span_px=body_span)
            if tracked_ball is not None:
                ball_frames += 1

            contact = estimate_contact(tracked_ball, ankles, body_span) if tracked_ball is not None else {"side": "none", "distance_px": None, "contact": False}
            if contact.get("contact"):
                contact_frames += 1

            previous_ball = prev_ball
            kin = compute_football_kinematics(
                current_points,
                prev_points,
                tracked_ball,
                previous_ball,
                contact,
                body_span,
                move_ratio,
            )
            seq = update_football_sequence(sequence_state, kin, now_t)
            temporal_prediction = update_temporal_classifier(temporal_state, seq, kin, now_t)
            if temporal_prediction.label and temporal_prediction.label != "soccer_idle":
                action_vote_counts[temporal_prediction.label] = action_vote_counts.get(temporal_prediction.label, 0) + 1
                if (
                    best_temporal_prediction is None
                    or float(temporal_prediction.confidence) > float(best_temporal_prediction.get("confidence", 0.0))
                ):
                    best_temporal_prediction = {
                        "label": temporal_prediction.label,
                        "confidence": float(temporal_prediction.confidence),
                        "source": temporal_prediction.source,
                        "features": dict(temporal_prediction.features or {}),
                    }
            if seq.sequence_active:
                active_frames += 1
            last_sequence_snapshot = {
                "phase": seq.phase,
                "phase_confidence": float(seq.phase_confidence),
                "phase_locked": bool(seq.phase_locked),
                "sequence_active": bool(seq.sequence_active),
                "sequence_ready": bool(seq.sequence_ready),
                "action_label": str(seq.action_label),
                "support_side": str(seq.support_side),
                "swing_side": str(seq.swing_side),
                "events": dict(seq.events),
                "metrics": dict(seq.metrics),
            }

            sample = {
                "index": frame_idx,
                "time": now_t,
                "phase": seq.phase,
                "phase_confidence": float(seq.phase_confidence),
                "phase_locked": bool(seq.phase_locked),
                "sequence_active": bool(seq.sequence_active),
                "sequence_ready": bool(seq.sequence_ready),
                "support_ball_ratio": float(seq.metrics.get("support_ball_ratio", 0.28)),
                "swing_ball_ratio": float(seq.metrics.get("swing_ball_ratio", 0.16)),
                "ball_speed_ratio": float(seq.metrics.get("ball_speed_ratio", 0.0)),
                "balance": float(pose_metrics["balance"]),
                "trunk_lean_deg": float(pose_metrics["trunk_lean_deg"]),
                "valgus_ratio": float(pose_metrics["valgus_ratio"]),
                "symmetry": float(pose_metrics["symmetry"]),
                "stability": float(stability),
                "visibility": float(vis_avg),
                "move_score": float(move_score),
                "body_span": float(body_span),
                "contact": bool(contact.get("contact")),
                "contact_side": str(contact.get("side", "none")),
                "support_side": str(seq.support_side),
                "swing_side": str(seq.swing_side),
                "events": dict(seq.events),
                "ball_present": tracked_ball is not None,
                "ball_x": float(tracked_ball["x"]) if tracked_ball is not None else None,
                "ball_y": float(tracked_ball["y"]) if tracked_ball is not None else None,
                "ball_vx": float(tracked_ball.get("vx", 0.0)) if tracked_ball is not None else 0.0,
                "ball_vy": float(tracked_ball.get("vy", 0.0)) if tracked_ball is not None else 0.0,
                "ball_radius": float(tracked_ball.get("radius", 0.0)) if tracked_ball is not None else None,
                "ball_confidence": float(tracked_ball.get("confidence", 0.0)) if tracked_ball is not None else 0.0,
                "goal_visible": False,
                "temporal_action_label": str(temporal_prediction.label),
                "temporal_action_confidence": float(temporal_prediction.confidence),
                "temporal_action_source": str(temporal_prediction.source),
            }
            samples.append(sample)

            prev_points = current_points
            if tracked_ball is not None:
                prev_ball = tracked_ball
            frame_idx += 1
    finally:
        cap.release()
        pose.close()

    return {
        "samples": samples,
        "fps": fps,
        "frame_count": source_frame_count if source_frame_count > 0 else frame_idx,
        "source_frame_count": source_frame_count if source_frame_count > 0 else frame_idx,
        "video_duration_s": round(float(video_duration_s), 3),
        "fast_mode_enabled": bool(fast_mode_enabled),
        "frame_ranges": [
            [int(start), int(end)]
            for start, end in (frame_ranges or [])
        ],
        "analysis_frame_stride": int(analysis_stride),
        "analysis_windows": [
            {
                "start_frame": int(start),
                "end_frame": int(end),
                "start_time": round(float(start) / fps, 3) if fps > 0.0 else 0.0,
                "end_time": round(float(end) / fps, 3) if fps > 0.0 else 0.0,
            }
            for start, end in sample_windows
        ],
        "sampled_frame_count": len(samples),
        "valid_pose_frames": valid_pose_frames,
        "ball_frames": ball_frames,
        "contact_frames": contact_frames,
        "active_frames": active_frames,
        "temporal_action_votes": action_vote_counts,
        "temporal_best_prediction": best_temporal_prediction,
        "sequence_snapshot": last_sequence_snapshot,
        "sequence_action_label": str(last_sequence_snapshot.get("action_label", "soccer_idle")) if last_sequence_snapshot else "soccer_idle",
        "warnings": warnings,
    }


def _aggregate_metrics(samples: List[Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], List[str]]:
    if not samples:
        return (
            {
                "support_ball_ratio": 0.28,
                "swing_ball_ratio": 0.16,
                "ball_speed_ratio": 0.0,
                "balance": 0.0,
                "trunk_lean_deg": 0.0,
                "valgus_ratio": 1.0,
                "symmetry": 0.0,
                "stability": 0.0,
                "visibility": 0.0,
                "ball_contact": 0.0,
                "sequence_confidence": 0.0,
                "phase_locked": 0.0,
            },
            {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            {},
            {},
            {},
            [],
        )

    support_event_idx = _first_event_index(samples, "support_plant")
    contact_event_idx = _first_event_index(samples, "contact")
    follow_event_idx = _first_event_index(samples, "follow_through_complete")
    complete_event_idx = _first_event_index(samples, "sequence_complete")
    first_active_idx = _first_phase_index(samples, "support")
    if first_active_idx is None:
        first_active_idx = _first_phase_index(samples, "contact")
    if first_active_idx is None:
        first_active_idx = _first_phase_index(samples, "follow_through")

    if contact_event_idx is None:
        contact_event_idx = _best_index(samples, "ball_speed_ratio", _indices_between(first_active_idx, complete_event_idx, len(samples)), mode="max")
    if support_event_idx is None:
        support_event_idx = _best_index(samples, "support_ball_ratio", _indices_between(first_active_idx, contact_event_idx, len(samples)), mode="min")
    if follow_event_idx is None:
        follow_event_idx = _first_phase_index(samples, "follow_through")
        if follow_event_idx is None and contact_event_idx is not None:
            follow_event_idx = min(len(samples) - 1, contact_event_idx + 1)

    support_window = _indices_between(first_active_idx, contact_event_idx, len(samples))
    if not support_window:
        support_window = _indices_between(None, contact_event_idx, len(samples))
    contact_window = _indices_between(max(0, (contact_event_idx or 0) - 2), (contact_event_idx or 0) + 2, len(samples))
    if not contact_window:
        contact_window = support_window
    post_contact_window = _indices_between(contact_event_idx, complete_event_idx, len(samples))
    if not post_contact_window:
        post_contact_window = _indices_between(contact_event_idx, None, len(samples))
    active_window = _indices_between(first_active_idx, complete_event_idx, len(samples))
    if not active_window:
        active_window = [idx for idx, sample in enumerate(samples) if sample.get("sequence_active")]
    if not active_window:
        active_window = list(range(len(samples)))

    pose_frames = sum(1 for sample in samples if float(sample.get("visibility", 0.0)) > 0.55)
    ball_frames = sum(1 for sample in samples if bool(sample.get("ball_present", False)))
    total_frames = len(samples)
    body_span_px = _safe_mean((samples[idx]["body_span"] for idx in active_window), default=_safe_mean((sample.get("body_span", 1.0) for sample in samples), default=1.0))
    move_ratio = _safe_mean(
        (
            float(samples[idx].get("move_score", 0.0)) / max(1.0, float(samples[idx].get("body_span", 1.0)))
            for idx in active_window
        ),
        default=0.0,
    )

    support_ball_ratio = _safe_min((samples[idx]["support_ball_ratio"] for idx in support_window), default=0.28)
    swing_ball_ratio = _safe_min((samples[idx]["swing_ball_ratio"] for idx in support_window), default=0.16)
    ball_speed_ratio = _safe_max((samples[idx]["ball_speed_ratio"] for idx in post_contact_window), default=0.0)
    balance = _safe_max((samples[idx]["balance"] for idx in contact_window), default=0.0)
    trunk_lean_deg = _safe_max((samples[idx]["trunk_lean_deg"] for idx in contact_window), default=0.0)
    valgus_ratio = _safe_min((samples[idx]["valgus_ratio"] for idx in contact_window), default=1.0)
    symmetry = _safe_max((samples[idx]["symmetry"] for idx in contact_window), default=0.0)
    stability = _clamp(_safe_mean((samples[idx]["stability"] for idx in active_window), default=0.0))
    visibility = _clamp(_safe_mean((samples[idx]["visibility"] for idx in active_window), default=0.0))
    sequence_confidence = _clamp(_safe_mean((samples[idx]["phase_confidence"] for idx in active_window), default=0.0))
    phase_locked = 1.0 if any(bool(samples[idx].get("phase_locked", False)) for idx in active_window) else 0.0
    ball_contact = 1.0 if contact_event_idx is not None else 0.0

    metrics = {
        "support_ball_ratio": float(support_ball_ratio),
        "swing_ball_ratio": float(swing_ball_ratio),
        "ball_speed_ratio": float(ball_speed_ratio),
        "balance": float(balance),
        "trunk_lean_deg": float(trunk_lean_deg),
        "valgus_ratio": float(valgus_ratio),
        "symmetry": float(symmetry),
        "stability": float(stability),
        "visibility": float(visibility),
        "ball_contact": float(ball_contact),
        "sequence_confidence": float(sequence_confidence),
        "phase_locked": float(phase_locked),
        "body_span_px": float(body_span_px),
        "ball_confidence": float(ball_frames / max(1, total_frames)),
        "move_ratio": float(move_ratio),
    }

    phase_scores = {
        "preparation": 0.0,
        "support": 0.0,
        "contact": 0.0,
        "follow_through": 0.0,
    }

    action_quality = score_football_action(metrics, "shoot_like", TEMPLATE_CODE)
    phase_scores.update(action_quality.phase_scores)

    event_times = {
        "support": float(samples[support_event_idx]["time"]) if support_event_idx is not None else float(samples[support_window[0]]["time"]) if support_window else 0.0,
        "contact": float(samples[contact_event_idx]["time"]) if contact_event_idx is not None else float(samples[contact_window[0]]["time"]) if contact_window else 0.0,
        "follow_through": float(samples[follow_event_idx]["time"]) if follow_event_idx is not None else float(samples[post_contact_window[0]]["time"]) if post_contact_window else 0.0,
        "sequence_complete": float(samples[complete_event_idx]["time"]) if complete_event_idx is not None else float(samples[-1]["time"]),
    }
    issue_times = _issue_times(
        samples,
        support_window=support_window,
        contact_window=contact_window,
        post_contact_window=post_contact_window,
        support_event_idx=support_event_idx,
        contact_event_idx=contact_event_idx,
        follow_event_idx=follow_event_idx,
        complete_event_idx=complete_event_idx,
    )

    evidence = {
        "pose_frames": float(pose_frames),
        "ball_frames": float(ball_frames),
        "total_frames": float(total_frames),
        "analysis_confidence": float(_clamp(0.48 * (pose_frames / max(1, total_frames)) + 0.26 * (ball_frames / max(1, total_frames)) + 0.16 * (len(active_window) / max(1, total_frames)) + 0.10 * ball_contact)),
    }

    warnings: List[str] = []
    if pose_frames < max(4, int(total_frames * 0.18)):
        warnings.append("pose_evidence_low")
    if ball_frames < max(2, int(total_frames * 0.08)):
        warnings.append("ball_evidence_low")
    if contact_event_idx is None:
        warnings.append("contact_not_detected")

    return metrics, phase_scores, event_times, evidence, issue_times, warnings


def _build_summary(action_quality, issues: List[ShotIssue], evidence: Dict[str, float]) -> str:
    overall = float(action_quality.overall_score)
    if issues and issues[0].id == "capture_quality_low":
        return "视频证据不足，本次分析结果偏保守；请补拍全身清晰射门视频后再看关键问题。"

    if issues:
        primary = issues[0]
        if primary.id == "stable_action":
            if overall >= 90.0:
                return f"射门动作得分 {overall:.0f}/100，完成度很高，当前重点是继续稳定支撑与收尾节奏。"
            if overall >= 75.0:
                return f"射门动作得分 {overall:.0f}/100，整体表现良好，仍需继续打磨支撑与收尾节奏。"
            if overall >= 60.0:
                return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度还不够稳定。"
            if overall >= 40.0:
                return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度不足，建议先把结构稳定下来。"
            return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度较弱，建议优先纠正。"
        if len(issues) > 1 and issues[1].id not in {"stable_action", "capture_quality_low"}:
            return f"射门动作得分 {overall:.0f}/100，主要问题是{primary.title}，其次是{issues[1].title}。"
        if overall < 40.0:
            return f"射门动作得分 {overall:.0f}/100，当前主要问题是{primary.title}，建议优先纠正。"
        if overall < 60.0:
            return f"射门动作得分 {overall:.0f}/100，当前主要问题是{primary.title}。"
        return f"射门动作得分 {overall:.0f}/100，主要问题是{primary.title}。"

    if float(evidence.get("analysis_confidence", 0.0)) < 0.45:
        if overall < 60.0:
            return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度还不够稳定；但当前证据偏少，结论请先按保守结果理解。"
        return f"射门动作得分 {overall:.0f}/100，但当前证据还偏少，结论请先按保守结果理解。"

    if overall < 40.0:
        return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度较弱。"
    if overall < 60.0:
        return f"射门动作得分 {overall:.0f}/100，当前主要问题是动作完成度还不够稳定。"
    if overall < 75.0:
        return f"射门动作得分 {overall:.0f}/100，整体可用，仍有少量细节需要优化。"
    return f"射门动作整体得分 {overall:.0f}/100，当前没有看到特别突出的关键失误。"


def _build_result(video_path: Path, run_data: Dict[str, Any]) -> Dict[str, Any]:
    samples = run_data["samples"]
    if not samples:
        warnings = list(dict.fromkeys(run_data.get("warnings", []) + ["no_valid_samples"]))
        score = ShotScore(0.0, 0.0, 0.0, 0.0, "needs_strengthen", "需加强")
        issues = [
            ShotIssue(
                id="capture_quality_low",
                title="视频证据不足",
                phase="setup",
                time=0.0,
                short_hint="请补拍全身清晰射门视频",
                explanation="当前视频没有可用的分析帧，系统无法稳定读取射门动作。",
                fix_advice="请确保视频可播放，并让球和全身关键关节都能清楚入镜。",
                training_advice="先补拍一条清晰视频，再做射门技术分析。",
                severity=1.0,
            )
        ]
        payload = ShotAnalysisResult(
            action_type=ACTION_TYPE,
            clip_id=_slugify(video_path.stem),
            video_path=str(video_path.resolve()),
            analysis_version=ANALYSIS_VERSION,
            template_code=TEMPLATE_CODE,
            generated_at=_now_iso(),
            duration_s=0.0,
            frame_count=0,
            score=score,
            summary="视频证据不足，本次射门分析未能稳定读取有效帧。",
            issues=issues,
            phase_scores={"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            analysis_confidence=0.0,
            status="error",
            warnings=warnings,
        ).to_dict()
        payload.update(
            {
                "action_name": "shot_instep",
                "resolved_action_name": "shot_instep",
                "action_display_name": "射门",
                "overall_score": 0.0,
                "outcome_score": 0.0,
                "technique_score": None,
                "primary_score": 0.0,
                "sub_scores": {},
                "triggered_rules": [
                    {
                        "id": "video_quality_fail",
                        "metric": "video_quality_fail",
                        "label": "视频质量不足",
                        "severity": "fail",
                        "reason": "当前视频没有可用的分析帧，系统无法稳定读取射门动作。",
                        "phase": "setup",
                        "time": 0.0,
                        "role": "primary",
                        "quality_impact": "primary",
                    }
                ],
                "fail_reasons": ["当前视频没有可用的分析帧，系统无法稳定读取射门动作。"],
                "feedback_messages": ["请补拍一条清晰视频，再做射门技术分析。"],
                "error_timestamps": [
                    {
                        "rule_id": "video_quality_fail",
                        "phase": "setup",
                        "time": 0.0,
                        "severity": "fail",
                        "reason": "当前视频没有可用的分析帧，系统无法稳定读取射门动作。",
                    }
                ],
                "quality_status": "fail",
                "best_trial": {
                    "metric": "overall",
                    "label": "射门",
                    "score": 0.0,
                    "raw_value": None,
                    "role": "summary",
                    "band": "unknown",
                    "source": "overall_proxy",
                },
                "worst_trial": {
                    "metric": "overall",
                    "label": "射门",
                    "score": 0.0,
                    "raw_value": None,
                    "role": "summary",
                    "band": "unknown",
                    "source": "overall_proxy",
                },
                "quality_gate": {
                    "quality_status": "fail",
                    "passed": False,
                    "allow_micro_technique_score": False,
                    "hide_micro_technique_score": True,
                    "should_reshoot": True,
                    "reshoot_hint": "请补拍更清晰的全身视频，确保球、支撑脚和关键触球瞬间都入镜。",
                    "triggered_rules": [
                        {
                            "id": "video_quality_fail",
                            "severity": "fail",
                            "reason": "当前视频没有可用的分析帧，系统无法稳定读取射门动作。",
                        }
                    ],
                    "fail_reasons": ["当前视频没有可用的分析帧，系统无法稳定读取射门动作。"],
                    "thresholds": {},
                    "observed": {},
                },
                "rule_metrics": {},
            }
        )
        return payload
    metrics, phase_scores, event_times, evidence, issue_times, warnings = _aggregate_metrics(samples)
    action_quality = score_football_action(metrics, "shoot_like", TEMPLATE_CODE)

    issues = build_shot_issues(
        metrics=metrics,
        phase_scores=phase_scores,
        evidence=evidence,
        event_times=event_times,
        issue_times=issue_times,
        fallback_issue=action_quality.key_issues[0] if action_quality.key_issues else None,
    )

    rules = load_football_rules()
    quality_result = evaluate_global_quality_gate(
        run_data=run_data,
        metrics=metrics,
        rules=rules,
        action_name="shot_instep",
    )
    rule_metrics = _build_rule_metrics(metrics, run_data, action_quality)
    score_result = score_action(
        "shot_instep",
        rule_metrics,
        rules,
        audience="beginner",
        quality_result=quality_result,
        analysis_context={
            "rule_metrics": rule_metrics,
            "legacy_metrics": metrics,
            "run_data": run_data,
            "event_times": event_times,
            "issue_times": issue_times,
            "legacy_quality": action_quality,
        },
    )
    issue_triggers = _issue_triggered_rules(issues)
    combined_triggers = _merge_triggered_rules(
        quality_result.get("triggered_rules") or [],
        score_result.get("triggered_rules") or [],
        issue_triggers,
    )
    score_result_for_feedback = dict(score_result)
    score_result_for_feedback["triggered_rules"] = combined_triggers
    feedback_result = build_feedback_messages(
        action_name="shot_instep",
        rules=rules,
        score_result=score_result_for_feedback,
        quality_result=quality_result,
        analysis_context={
            "issues": issues,
            "legacy_quality": action_quality,
            "run_data": run_data,
        },
    )
    timestamp_result = locate_error_timestamps(
        action_name="shot_instep",
        triggered_rules=combined_triggers,
        rule_times=issue_times,
        event_times=event_times,
    )

    score = ShotScore(
        overall=action_quality.overall_score,
        technical_execution=action_quality.technical_execution_score,
        control_stability=action_quality.control_stability_score,
        action_safety=action_quality.action_safety_score,
        level_code=action_quality.level_code,
        level_label=action_quality.level_label,
    )

    summary = _build_summary(action_quality, issues, evidence)
    if quality_result.get("should_reshoot"):
        summary = str(quality_result.get("reshoot_hint") or summary)
    generated_at = _now_iso()
    if quality_result.get("quality_status") == "pass" and float(evidence["analysis_confidence"]) >= 0.45 and "pose_evidence_low" not in warnings and "ball_evidence_low" not in warnings:
        status = "ok"
    elif quality_result.get("quality_status") == "outcome_only":
        status = "provisional"
    else:
        status = "provisional"

    payload = ShotAnalysisResult(
        action_type=ACTION_TYPE,
        clip_id=_slugify(video_path.stem),
        video_path=str(video_path.resolve()),
        analysis_version=ANALYSIS_VERSION,
        template_code=TEMPLATE_CODE,
        generated_at=generated_at,
        duration_s=float(run_data["frame_count"]) / float(run_data["fps"] or 30.0) if run_data["frame_count"] else 0.0,
        frame_count=int(run_data["frame_count"]),
        score=score,
        summary=summary,
        issues=issues,
        phase_scores=phase_scores,
        analysis_confidence=float(evidence["analysis_confidence"]),
        status=status,
        warnings=list(dict.fromkeys(run_data.get("warnings", []) + warnings)),
    ).to_dict()
    payload.update(
        {
            "action_name": score_result.get("action_name", "shot_instep"),
            "input_action_name": score_result.get("input_action_name", score_result.get("action_name", "shot_instep")),
            "resolved_action_name": score_result.get("resolved_action_name", score_result.get("action_name", "shot_instep")),
            "action_display_name": score_result.get("action_display_name", "射门"),
            "overall_score": float(score_result.get("overall_score", 0.0)),
            "outcome_score": score_result.get("outcome_score"),
            "technique_score": score_result.get("technique_score") if quality_result.get("passed") else None,
            "primary_score": score_result.get("primary_score"),
            "sub_scores": score_result.get("sub_scores", {}),
            "triggered_rules": combined_triggers,
            "fail_reasons": feedback_result.get("fail_reasons", []) or list(quality_result.get("fail_reasons") or []),
            "feedback_messages": feedback_result.get("feedback_messages", []),
            "error_timestamps": timestamp_result.get("error_timestamps", []),
            "quality_status": quality_result.get("quality_status", "pass"),
            "best_trial": score_result.get("best_trial"),
            "worst_trial": score_result.get("worst_trial"),
            "quality_gate": quality_result,
            "rule_metrics": rule_metrics,
        }
    )

    if payload["best_trial"] is None:
        payload["best_trial"] = {
            "metric": "overall",
            "label": "射门",
            "score": round(float(payload.get("overall_score", 0.0)), 2),
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        }
    if payload["worst_trial"] is None:
        payload["worst_trial"] = {
            "metric": "overall",
            "label": "射门",
            "score": round(float(payload.get("overall_score", 0.0)), 2),
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        }

    return payload


def _default_work_dir(video_path: Path, work_dir: Optional[Path]) -> Path:
    root = work_dir if work_dir is not None else Path(__file__).resolve().parent.parent / ".cache" / "shot_engine"
    return root / _slugify(video_path.stem)


def _normalize_frame_windows(windows: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    normalized: List[List[int]] = []
    for start, end in sorted(
        (
            (int(start), int(end))
            for start, end in windows
            if int(end) >= int(start)
        ),
        key=lambda item: (item[0], item[1]),
    ):
        if not normalized:
            normalized.append([start, end])
            continue
        prev_start, prev_end = normalized[-1]
        if start <= prev_end + 1:
            normalized[-1][1] = max(prev_end, end)
        else:
            normalized.append([start, end])
    return [(start, end) for start, end in normalized]


def _build_fast_mode_plan(
    *,
    frame_count: int,
    fps: float,
    duration_s: float,
    frame_stride: int,
    fast_mode_enabled: bool,
) -> Tuple[int, List[Tuple[int, int]]]:
    requested_stride = max(1, int(frame_stride))
    analysis_stride = requested_stride
    if not fast_mode_enabled:
        return analysis_stride, []

    analysis_stride = max(analysis_stride, 2)
    if frame_count <= 0 or fps <= 0.0 or duration_s <= 0.0:
        return analysis_stride, []

    if duration_s <= VIDEO_FAST_MODE_DURATION_THRESHOLD_S:
        return analysis_stride, []

    analysis_stride = max(analysis_stride, min(VIDEO_FAST_MODE_MAX_STRIDE, 2 + int(duration_s // 10)))
    window_duration_s = min(VIDEO_FAST_MODE_WINDOW_DURATION_S, max(2.0, duration_s * VIDEO_FAST_MODE_WINDOW_RATIO))
    window_duration_frames = max(1, int(round(window_duration_s * fps)))
    half_window_frames = max(1, window_duration_frames // 2)
    center_frame = max(0, min(frame_count - 1, int(round(frame_count * 0.5))))

    raw_windows = [
        (0, min(frame_count - 1, window_duration_frames - 1)),
        (max(0, center_frame - half_window_frames), min(frame_count - 1, center_frame + half_window_frames)),
        (max(0, frame_count - window_duration_frames), frame_count - 1),
    ]
    return analysis_stride, _normalize_frame_windows(raw_windows)


def analyze_shot(
    video_path: str | Path,
    *,
    output_path: str | Path | None = None,
    work_dir: str | Path | None = None,
    frame_stride: int = 1,
) -> Dict[str, Any]:
    video_path = Path(video_path)
    if not video_path.exists():
        result = ShotAnalysisResult(
            action_type=ACTION_TYPE,
            clip_id=_slugify(video_path.stem),
            video_path=str(video_path),
            analysis_version=ANALYSIS_VERSION,
            template_code=TEMPLATE_CODE,
            generated_at=_now_iso(),
            duration_s=0.0,
            frame_count=0,
            score=ShotScore(0.0, 0.0, 0.0, 0.0, "needs_strengthen", "需加强"),
            summary="视频路径不存在，无法执行射门分析。",
            issues=[
                ShotIssue(
                    id="video_not_found",
                    title="视频不存在",
                    phase="setup",
                    time=0.0,
                    short_hint="请检查视频路径",
                    explanation="系统没有找到输入视频文件，因此无法继续分析。",
                    fix_advice="请把有效视频路径传给 analyze_shot(video_path)。",
                    training_advice="先确认素材可读，再进行动作分析。",
                    severity=1.0,
                )
            ],
            phase_scores={"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            analysis_confidence=0.0,
            status="error",
            warnings=["video_not_found"],
        )
        payload = result.to_dict()
        payload.update(
            {
                "action_name": "shot_instep",
                "resolved_action_name": "shot_instep",
                "action_display_name": "射门",
                "overall_score": 0.0,
                "outcome_score": 0.0,
                "technique_score": None,
                "primary_score": 0.0,
                "sub_scores": {},
                "triggered_rules": [
                    {
                        "id": "video_not_found",
                        "metric": "video_not_found",
                        "label": "视频不存在",
                        "severity": "fail",
                        "reason": "系统没有找到输入视频文件，因此无法继续分析。",
                        "phase": "setup",
                        "time": 0.0,
                        "role": "primary",
                        "quality_impact": "primary",
                    }
                ],
                "fail_reasons": ["系统没有找到输入视频文件，因此无法继续分析。"],
                "feedback_messages": ["请把有效视频路径传给 analyze_shot(video_path)。"],
                "error_timestamps": [
                    {
                        "rule_id": "video_not_found",
                        "phase": "setup",
                        "time": 0.0,
                        "severity": "fail",
                        "reason": "系统没有找到输入视频文件，因此无法继续分析。",
                    }
                ],
                "quality_status": "fail",
                "best_trial": {
                    "metric": "overall",
                    "label": "射门",
                    "score": 0.0,
                    "raw_value": None,
                    "role": "summary",
                    "band": "unknown",
                    "source": "overall_proxy",
                },
                "worst_trial": {
                    "metric": "overall",
                    "label": "射门",
                    "score": 0.0,
                    "raw_value": None,
                    "role": "summary",
                    "band": "unknown",
                    "source": "overall_proxy",
                },
                "quality_gate": {
                    "quality_status": "fail",
                    "passed": False,
                    "allow_micro_technique_score": False,
                    "hide_micro_technique_score": True,
                    "should_reshoot": True,
                    "reshoot_hint": "请检查视频路径并重新传入可播放的视频文件。",
                    "triggered_rules": [
                        {
                            "id": "video_not_found",
                            "severity": "fail",
                            "reason": "系统没有找到输入视频文件，因此无法继续分析。",
                        }
                    ],
                    "fail_reasons": ["系统没有找到输入视频文件，因此无法继续分析。"],
                    "thresholds": {},
                    "observed": {},
                },
                "rule_metrics": {},
            }
        )
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    if output_path is None and work_dir is not None:
        output_path = _default_work_dir(video_path, Path(work_dir)) / "shot_analysis.json"

    run_data = _process_video(video_path, frame_stride=max(1, int(frame_stride)))
    payload = _build_result(video_path, run_data)
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


VIDEO_ANALYSIS_VERSION = "video_engine_v1"
VIDEO_ANALYZER_USED = "generic_video_analyzer_v1"
VIDEO_ANALYSIS_MODE = "analyze_video"
VIDEO_FALLBACK_TEMPLATE = "short_pass"
VIDEO_ACTION_CONFIDENCE_THRESHOLD = 0.55
VIDEO_SCORE_READY_THRESHOLD = 0.35
VIDEO_FAST_MODE_DURATION_THRESHOLD_S = 8.0
VIDEO_FAST_MODE_WINDOW_DURATION_S = 3.0
VIDEO_FAST_MODE_WINDOW_RATIO = 0.12
VIDEO_FAST_MODE_MAX_STRIDE = 6
VIDEO_LONG_VIDEO_LIMIT_S = 30.0
VIDEO_SINGLE_PLAYER_VIDEO_LIMIT_S = 140.0 * 60.0
VIDEO_LONG_VIDEO_LOCALIZE_THRESHOLD_S = 15.0
VIDEO_LONG_VIDEO_WINDOW_PRE_BUFFER_S = 1.5
VIDEO_LONG_VIDEO_WINDOW_POST_BUFFER_S = 2.5
VIDEO_LONG_VIDEO_WINDOW_MIN_DURATION_S = 4.0
VIDEO_LONG_VIDEO_WINDOW_MAX_DURATION_S = 6.0
VIDEO_LONG_VIDEO_COARSE_SAMPLE_FPS_LOW = 6.0
VIDEO_LONG_VIDEO_COARSE_SAMPLE_FPS_HIGH = 8.0
VIDEO_LONG_VIDEO_MAX_CANDIDATE_WINDOWS = 3
_VIDEO_ANALYSIS_RESULT_CACHE: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
# Keep this comfortably below the iOS request timeout so genuinely stalled
# analyses can still fail fast, but do not penalize valid long-running runs.
VIDEO_ANALYSIS_TIMEOUT_S = 55.0
VIDEO_ROUTER_ANALYZER = "video_analysis_router_v1"
VIDEO_PASS_RECEIVE_SEQUENCE_ANALYZER = "pass_receive_sequence_engine_v1"
VIDEO_SHORT_PASS_ANALYZER = "short_pass_analyzer_v1"
VIDEO_SHOT_ANALYZER = "shot_instep_analyzer_v1"
VIDEO_RECEIVE_CONTROL_ANALYZER = "receive_control_analyzer_v1"
VIDEO_FULL_MATCH_ANALYZER = "full_match_player_analyzer_v1"

_VIDEO_ACTION_MAPPING = {
    "pass": "short_pass",
    "pass_like": "short_pass",
    "pass_receive_sequence_like": "pass_receive_sequence",
    "shot": "shot_instep",
    "shot_like": "shot_instep",
    "shoot_like": "shot_instep",
    "first_touch": "receive_control",
    "first_touch_like": "receive_control",
    "clearance": "shot_instep",
    "long_ball": "short_pass",
    "non_kick": "short_pass",
    "uncertain": "short_pass",
    "dribble_like": "dribble_change_direction",
    "juggle_like": "juggling",
    "full_match": "full_match_player",
    "full_match_player": "full_match_player",
}

_VIDEO_SUPPORTED_ANALYZERS = {
    "pass_receive_sequence": VIDEO_PASS_RECEIVE_SEQUENCE_ANALYZER,
    "short_pass": VIDEO_SHORT_PASS_ANALYZER,
    "shot_instep": VIDEO_SHOT_ANALYZER,
    "receive_control": VIDEO_RECEIVE_CONTROL_ANALYZER,
    "full_match_player": VIDEO_FULL_MATCH_ANALYZER,
}

_VIDEO_RULE_PHASES = {
    "max_ball_speed_mps": "contact",
    "max_ball_speed_proxy_mps": "contact",
    "target_zone_hit": "contact",
    "shot_consistency_cv_pct": "follow_through",
    "support_foot_lateral_offset_cm": "support",
    "support_foot_ap_offset_cm": "support",
    "trunk_lean_deg_at_impact_proxy": "contact",
    "endpoint_error_m": "contact",
    "pass_endpoint_error_m": "contact",
    "pass_execution_time_s": "follow_through",
    "receive_control_zone_success_rate": "contact",
    "receive_stabilization_time_s": "follow_through",
    "receive_corrective_touch_count": "follow_through",
    "sequence_continuity_score": "follow_through",
    "next_action_readiness": "follow_through",
    "pass_receive_gap_s": "follow_through",
    "execution_time_s": "follow_through",
    "penalty_events": "contact",
    "control_zone_success_rate": "contact",
    "stabilization_time_s": "follow_through",
    "corrective_touch_count": "follow_through",
    "lateral_offset_m": "support",
    "body_open_angle_deg": "support",
    "recenter_time_s": "follow_through",
    "completion_time_s": "follow_through",
    "cone_hit_count": "contact",
    "out_of_lane_count": "support",
    "control_loss_count": "contact",
    "drop_count": "contact",
    "consecutive_touches_dominant_foot": "follow_through",
    "consecutive_touches_freestyle": "follow_through",
}


def _video_score_level(overall_score: float) -> Tuple[str, str]:
    return score_level_from_overall(overall_score)


def _load_video_calibration(calibration_path: str | Path | None = None) -> Optional[Dict[str, Any]]:
    if calibration_path is not None:
        try:
            return load_calibration(calibration_path)
        except Exception:
            return None

    default_path = Path(__file__).resolve().parent.parent / "calibration" / "user_profile.json"
    if default_path.exists():
        try:
            return load_calibration(default_path)
        except Exception:
            return None
    return None


def _probe_video_metadata(video_path: Path) -> Dict[str, Any]:
    if cv2 is None:
        return {
            "video_opened": False,
            "fps": 30.0,
            "frame_count": 0,
            "duration_s": 0.0,
            "warnings": ["opencv_unavailable"],
        }

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return {
                "video_opened": False,
                "fps": 30.0,
                "frame_count": 0,
                "duration_s": 0.0,
                "warnings": ["video_open_failed"],
            }

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0.0:
            fps = 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_s = float(frame_count) / fps if frame_count > 0 else 0.0
        return {
            "video_opened": True,
            "fps": fps,
            "frame_count": frame_count,
            "duration_s": round(float(duration_s), 3),
            "warnings": [],
        }
    finally:
        cap.release()


def _video_file_sha256(video_path: Path) -> str:
    digest = hashlib.sha256()
    with video_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _video_cache_key(
    video_path: Path,
    *,
    selected_action: str,
    analysis_template: Optional[str],
    frame_ranges: Optional[List[Tuple[int, int]]],
    long_video_localized: bool,
    skip_long_video_limit_check: bool,
) -> Optional[Tuple[str, str, str, str]]:
    if frame_ranges is not None or long_video_localized or skip_long_video_limit_check:
        return None
    route_key = _video_selected_action_canonical(selected_action)
    if not route_key:
        return None
    try:
        content_hash = _video_file_sha256(video_path)
    except Exception:
        return None
    template_key = str(analysis_template or "").strip().lower()
    version_key = (
        f"{VIDEO_ANALYSIS_VERSION}:"
        f"localize>{VIDEO_LONG_VIDEO_LOCALIZE_THRESHOLD_S}:"
        f"timeout>{VIDEO_ANALYSIS_TIMEOUT_S}"
    )
    return (content_hash, route_key, template_key, version_key)


def _video_cache_get(cache_key: Optional[Tuple[str, str, str, str]], video_path: Path) -> Optional[Dict[str, Any]]:
    if cache_key is None:
        return None
    cached = _VIDEO_ANALYSIS_RESULT_CACHE.get(cache_key)
    if not cached:
        return None
    payload = deepcopy(cached)
    payload.update(
        {
            "input_video_path": str(video_path),
            "video_path": str(video_path),
            "cache_hit": True,
            "analysis_cache_hit": True,
        }
    )
    return payload


def _video_cache_store(cache_key: Optional[Tuple[str, str, str, str]], payload: Dict[str, Any]) -> None:
    if cache_key is None:
        return
    status = str(payload.get("status") or "").lower()
    analysis_status = str(payload.get("analysis_status") or "").lower()
    if status == "error" or analysis_status in {"failed", "failure", "error"} or str(payload.get("error_code") or "").strip():
        return
    cached = deepcopy(payload)
    cached["cache_hit"] = False
    cached["analysis_cache_hit"] = False
    _VIDEO_ANALYSIS_RESULT_CACHE[cache_key] = cached


def _video_first_warning(warnings: Iterable[str], *needles: str) -> Optional[str]:
    warning_set = [str(warning) for warning in warnings if warning]
    for needle in needles:
        for warning in warning_set:
            if warning == needle or warning.startswith(f"{needle}:"):
                return needle
    return None


def _video_failure_message(
    reason: str,
    *,
    video_duration_s: float = 0.0,
    selected_action: str = "",
    system_action_suggestion: str = "",
    routed_analyzer: str = "",
    processing_time_s: float = 0.0,
) -> str:
    duration_text = f"{video_duration_s:.1f}"
    selected_text = _video_main_action_display_name(selected_action) if selected_action else "本次动作"
    suggestion_text = _video_main_action_display_name(system_action_suggestion) if system_action_suggestion else "系统建议"

    if reason == "video_too_long":
        return f"当前视频为 {duration_text} 秒，当前版本支持 30 秒以内视频自动分析。"
    if reason == "analysis_timeout":
        return "当前分析耗时过长，请稍后重试或换更短视频。"
    if reason == "unsupported_action":
        return "当前动作暂不支持，请切换到已支持的分析模板。"
    if reason == "no_action_window_found":
        return f"请确保视频里包含完整{selected_text}动作，且人物和球清晰可见。"
    if reason == "low_motion_signal":
        return f"当前视频动作信号太弱，请确保视频里包含完整{selected_text}动作，且人物和球清晰可见。"
    if reason == "route_mismatch":
        if selected_action and routed_analyzer and _video_main_action_class(selected_action) != _video_main_action_class(routed_analyzer):
            return "本次结果存在异常，请重新分析。"
        return f"你当前选择的是“{selected_text}”，但系统自动识别更像“{suggestion_text}”，已按当前选择继续分析。"
    if reason == "video_open_failed":
        return "视频无法打开，请检查文件是否损坏或格式是否受支持。"
    if reason == "mediapipe_pose_init_failed":
        return "姿态模型初始化失败，请稍后重试。"
    if reason == "mediapipe_pose_runtime_failed":
        return "姿态分析运行失败，请稍后重试。"
    if reason == "pose_evidence_low":
        return "请确保全身、球、支撑脚完整入镜，机位固定，动作前后保留 1 秒。"
    if reason == "ball_evidence_low":
        return "请确保球体完整入镜并持续可见，机位固定，动作前后保留 1 秒。"
    if reason == "contact_not_detected":
        return "请确保触球瞬间清晰入镜，球、支撑脚和全身都能同时看到。"
    if reason == "analysis_result_empty":
        return "当前视频没有可用的分析结果，请重试。"
    if reason == "unknown_error":
        return "本次分析未完成，请重试。"
    return "本次分析未完成，请重试。"


def _video_detect_failure_reason(
    payload: Dict[str, Any],
    *,
    run_data: Optional[Dict[str, Any]] = None,
    probe: Optional[Dict[str, Any]] = None,
    processing_time_s: float = 0.0,
    selected_action: str = "",
    routed_analyzer: str = "",
    system_action_suggestion: str = "",
    long_video_localized: bool = False,
) -> Tuple[Optional[str], str, str, Optional[str]]:
    run_data = run_data or {}
    probe = probe or {}
    warnings = list(dict.fromkeys(
        list(run_data.get("warnings", []) or [])
        + list(payload.get("warnings", []) or [])
    ))
    duration_s = float(
        probe.get("duration_s")
        or run_data.get("video_duration_s")
        or payload.get("duration_s")
        or 0.0
    )
    frame_count = int(
        probe.get("frame_count")
        or run_data.get("source_frame_count")
        or run_data.get("frame_count")
        or payload.get("frame_count")
        or 0
    )
    sampled_frame_count = int(run_data.get("sampled_frame_count") or len(run_data.get("samples") or []))
    fast_mode_enabled = bool(run_data.get("fast_mode_enabled") or payload.get("fast_mode_enabled") or False)
    candidate_window_count = int(
        payload.get("candidate_window_count")
        or run_data.get("candidate_window_count")
        or len(run_data.get("candidate_windows") or [])
        or 0
    )
    normalized_selected_action = _video_main_action_class(selected_action)
    normalized_routed_analyzer = _video_main_action_class(routed_analyzer)
    normalized_system_suggestion = _video_main_action_class(system_action_suggestion)
    if normalized_selected_action == "full_match" or normalized_routed_analyzer == "full_match":
        if str(payload.get("status") or "").lower() == "error" or str(payload.get("error_code") or "").strip():
            reason = str(payload.get("error_code") or payload.get("failure_reason") or "unknown_error")
            return reason, "failed", "normal", _video_failure_message(reason, video_duration_s=duration_s)
        return None, str(payload.get("analysis_status") or "success"), "normal", None
    actual_route_mismatch = (
        normalized_selected_action not in {"unknown", "review_required"}
        and normalized_routed_analyzer not in {"unknown", "review_required"}
        and normalized_selected_action != normalized_routed_analyzer
    )
    suggestion_mismatch = (
        normalized_selected_action not in {"unknown", "review_required"}
        and normalized_system_suggestion not in {"unknown", "review_required"}
        and normalized_selected_action != normalized_system_suggestion
    )

    if actual_route_mismatch or str(payload.get("result_kind") or "") == "anomaly" or str(payload.get("scoring_state") or "") == "result_inconsistent":
        reason = "route_mismatch"
        message = _video_failure_message(
            reason,
            video_duration_s=duration_s,
            selected_action=selected_action,
            system_action_suggestion=system_action_suggestion,
            routed_analyzer=routed_analyzer,
            processing_time_s=processing_time_s,
        )
        return reason, "failed", "anomaly", message

    if bool(payload.get("evidence_limited_fallback", False)) or str(payload.get("scoring_state") or "") == "evidence_limited_reference":
        return None, "partial", "normal", None

    if duration_s > VIDEO_LONG_VIDEO_LIMIT_S:
        reason = "video_too_long"
        return reason, "failed", "normal", _video_failure_message(reason, video_duration_s=duration_s)

    if any(warning.startswith("video_open_failed") for warning in warnings) or bool(probe.get("video_opened") is False and probe.get("warnings")):
        reason = "video_open_failed"
        return reason, "failed", "normal", _video_failure_message(reason)

    if "mediapipe_pose_init_failed" in warnings:
        reason = "mediapipe_pose_init_failed"
        return reason, "failed", "normal", _video_failure_message(reason)

    if "mediapipe_pose_runtime_failed" in warnings:
        reason = "mediapipe_pose_runtime_failed"
        return reason, "failed", "normal", _video_failure_message(reason)

    if processing_time_s >= VIDEO_ANALYSIS_TIMEOUT_S:
        reason = "analysis_timeout"
        return reason, "failed", "normal", _video_failure_message(reason, processing_time_s=processing_time_s)

    result_has_score = bool(payload.get("score"))
    result_has_summary = bool(str(payload.get("summary") or "").strip())
    if sampled_frame_count <= 0 or frame_count <= 0 or not result_has_score or str(payload.get("status") or "").lower() == "error":
        if result_has_score and result_has_summary and frame_count > 0 and str(payload.get("status") or "").lower() != "error":
            analysis_status = (
                "partial"
                if (fast_mode_enabled and duration_s > VIDEO_FAST_MODE_DURATION_THRESHOLD_S)
                or long_video_localized
                or suggestion_mismatch
                or str(payload.get("status") or "").lower() == "provisional"
                else "success"
            )
            integrity_state = "route_mismatch" if suggestion_mismatch else "normal"
            route_mismatch_message = None
            if suggestion_mismatch:
                route_mismatch_message = _video_failure_message(
                    "route_mismatch",
                    video_duration_s=duration_s,
                    selected_action=selected_action,
                    system_action_suggestion=system_action_suggestion,
                    routed_analyzer=routed_analyzer,
                    processing_time_s=processing_time_s,
                )
            return None, analysis_status, integrity_state, route_mismatch_message
        if "pose_evidence_low" in warnings:
            reason = "pose_evidence_low"
        elif "ball_evidence_low" in warnings:
            reason = "ball_evidence_low"
        elif "contact_not_detected" in warnings:
            reason = "contact_not_detected"
        elif "no_action_window_found" in warnings or (long_video_localized and candidate_window_count <= 0):
            reason = "no_action_window_found"
        elif "low_motion_signal" in warnings:
            reason = "low_motion_signal"
        elif str(payload.get("error_code") or "") == "unsupported_action_for_current_analyzer" or bool(payload.get("unsupported_action_for_current_analyzer", False)):
            reason = "unsupported_action"
        else:
            reason = "analysis_result_empty"
        message = _video_failure_message(
            reason,
            video_duration_s=duration_s,
            selected_action=selected_action,
            system_action_suggestion=system_action_suggestion,
            routed_analyzer=routed_analyzer,
            processing_time_s=processing_time_s,
        )
        return reason, "failed", "normal", message

    if "pose_evidence_low" in warnings:
        reason = "pose_evidence_low"
        return reason, "failed", "normal", _video_failure_message(reason)
    if "ball_evidence_low" in warnings:
        reason = "ball_evidence_low"
        return reason, "failed", "normal", _video_failure_message(reason)
    if "contact_not_detected" in warnings:
        reason = "contact_not_detected"
        return reason, "failed", "normal", _video_failure_message(reason)
    if "no_action_window_found" in warnings or (long_video_localized and candidate_window_count <= 0):
        reason = "no_action_window_found"
        return reason, "failed", "normal", _video_failure_message(reason)
    if "low_motion_signal" in warnings:
        reason = "low_motion_signal"
        return reason, "failed", "normal", _video_failure_message(reason)
    if "unsupported_action_for_current_analyzer" in warnings or bool(payload.get("unsupported_action_for_current_analyzer", False)):
        reason = "unsupported_action"
        return reason, "failed", "normal", _video_failure_message(reason)

    analysis_status = (
        "partial"
        if (fast_mode_enabled and duration_s > VIDEO_FAST_MODE_DURATION_THRESHOLD_S)
        or long_video_localized
        or suggestion_mismatch
        or str(payload.get("status") or "").lower() == "provisional"
        else "success"
    )
    integrity_state = "route_mismatch" if suggestion_mismatch else "normal"
    route_mismatch_message = None
    if suggestion_mismatch:
        route_mismatch_message = _video_failure_message(
            "route_mismatch",
            video_duration_s=duration_s,
            selected_action=selected_action,
            system_action_suggestion=system_action_suggestion,
            routed_analyzer=routed_analyzer,
            processing_time_s=processing_time_s,
        )
    return None, analysis_status, integrity_state, route_mismatch_message


def _video_attach_response_metadata(
    payload: Dict[str, Any],
    *,
    run_data: Optional[Dict[str, Any]] = None,
    probe: Optional[Dict[str, Any]] = None,
    processing_time_s: float = 0.0,
    long_video_localized: bool = False,
) -> Dict[str, Any]:
    run_data = run_data or {}
    probe = probe or {}
    merged = dict(payload)
    warnings = list(dict.fromkeys(
        list(run_data.get("warnings", []) or [])
        + list(merged.get("warnings", []) or [])
    ))
    selected_action = str(merged.get("selected_action") or "")
    system_action_suggestion = str(
        merged.get("system_action_suggestion")
        or merged.get("suggested_action")
        or merged.get("action_label")
        or ""
    )
    routed_analyzer = str(merged.get("routed_analyzer") or "")
    video_duration_s = float(
        probe.get("duration_s")
        or run_data.get("video_duration_s")
        or merged.get("duration_s")
        or 0.0
    )
    frame_count = int(
        probe.get("frame_count")
        or run_data.get("source_frame_count")
        or run_data.get("frame_count")
        or merged.get("frame_count")
        or 0
    )
    sampled_frame_count = int(run_data.get("sampled_frame_count") or len(run_data.get("samples") or []))
    fast_mode_enabled = bool(run_data.get("fast_mode_enabled") or merged.get("fast_mode_enabled") or False)
    candidate_windows = list(merged.get("candidate_windows") or run_data.get("candidate_windows") or [])
    candidate_window_count = int(
        merged.get("candidate_window_count")
        or run_data.get("candidate_window_count")
        or len(candidate_windows)
        or 0
    )
    selected_window = merged.get("selected_window") or run_data.get("selected_window")
    selected_window_index = merged.get("selected_window_index", run_data.get("selected_window_index"))
    selected_window_start_s = merged.get("selected_window_start_s", run_data.get("selected_window_start_s"))
    selected_window_end_s = merged.get("selected_window_end_s", run_data.get("selected_window_end_s"))
    selected_window_duration_s = merged.get("selected_window_duration_s", run_data.get("selected_window_duration_s"))
    failure_reason, analysis_status, integrity_state, route_mismatch_message = _video_detect_failure_reason(
        merged,
        run_data=run_data,
        probe=probe,
        processing_time_s=processing_time_s,
        selected_action=selected_action,
        routed_analyzer=routed_analyzer,
        system_action_suggestion=system_action_suggestion,
        long_video_localized=long_video_localized or bool(merged.get("long_video_localized") or run_data.get("long_video_localized")),
    )
    if failure_reason is not None:
        failure_message = _video_failure_message(
            failure_reason,
            video_duration_s=video_duration_s,
            selected_action=selected_action,
            system_action_suggestion=system_action_suggestion,
            routed_analyzer=routed_analyzer,
            processing_time_s=processing_time_s,
        )
    else:
        failure_message = None

    merged.update(
        {
            "analysis_status": analysis_status,
            "failure_reason": failure_reason,
            "failure_message": failure_message,
            "integrity_state": integrity_state,
            "route_mismatch_message": route_mismatch_message,
            "system_action_suggestion": system_action_suggestion,
            "fast_mode_enabled": fast_mode_enabled,
            "long_video_localized": bool(long_video_localized or merged.get("long_video_localized") or run_data.get("long_video_localized")),
            "candidate_window_count": candidate_window_count,
            "selected_window_index": selected_window_index,
            "selected_window_start_s": round(float(selected_window_start_s), 3) if selected_window_start_s is not None else None,
            "selected_window_end_s": round(float(selected_window_end_s), 3) if selected_window_end_s is not None else None,
            "selected_window_duration_s": round(float(selected_window_duration_s), 3) if selected_window_duration_s is not None else None,
            "candidate_windows": candidate_windows,
            "selected_window": selected_window if isinstance(selected_window, dict) else None,
            "sampled_frame_count": sampled_frame_count,
            "video_duration_s": round(float(video_duration_s), 3),
            "frame_count": frame_count,
            "processing_time_s": round(float(processing_time_s), 3),
            "debug_context": build_debug_context(
                selected_action=selected_action,
                system_action_suggestion=system_action_suggestion,
                analysis_routed_by=str(merged.get("analysis_routed_by") or ""),
                routed_analyzer=routed_analyzer,
                video_duration=video_duration_s,
                frame_count=frame_count,
                sampled_frame_count=sampled_frame_count,
                candidate_windows=candidate_windows,
                selected_window=selected_window if isinstance(selected_window, dict) else None,
                warnings=warnings,
                fast_mode_enabled=fast_mode_enabled,
                long_video_localized=bool(long_video_localized or merged.get("long_video_localized") or run_data.get("long_video_localized")),
                candidate_window_count=candidate_window_count,
                selected_window_index=selected_window_index if selected_window_index is not None else None,
                selected_window_start_s=selected_window_start_s if selected_window_start_s is not None else None,
                selected_window_end_s=selected_window_end_s if selected_window_end_s is not None else None,
                selected_window_duration_s=selected_window_duration_s if selected_window_duration_s is not None else None,
                processing_time=processing_time_s,
                failure_reason=failure_reason or "",
                failure_message=failure_message or "",
                route_mismatch_message=route_mismatch_message or "",
            ),
            "warnings": warnings,
        }
    )
    return merged


def _score_level_from_overall(overall_score: float) -> Dict[str, str]:
    code, label = _video_score_level(float(overall_score))
    return {"level_code": code, "level_label": label}


def _video_main_action_class(value: Any) -> str:
    lower = str(value or "").strip().lower()
    if not lower:
        return "unknown"
    if "full_match_player" in lower or "full_match" in lower or "match_player" in lower or "整场比赛" in lower or "全场" in lower or "比赛分析" in lower:
        return "full_match"
    if "review_required" in lower or "动作待确认" in lower:
        return "review_required"
    if "pass_receive_sequence" in lower or "sequence" in lower or "传接球" in lower:
        return "pass_receive_sequence"
    if "receive_control" in lower or "first_touch" in lower or "stop_ball" in lower or "receive" == lower or "touch" in lower or "停球" in lower or "接球" in lower:
        return "receive"
    if "shot_instep" in lower or "shoot_like" in lower or "shot_like" in lower or "shoot" in lower or "shot" in lower or "射门" in lower or "clearance" in lower:
        return "shot"
    if "short_pass" in lower or lower == "pass" or "pass_like" in lower or "long_ball" in lower or "长传" in lower or "传球" in lower:
        return "pass"
    if "non_kick" in lower or "soccer_idle" in lower or "uncertain" in lower or "pending_confirmation" in lower or "unknown" in lower or "待确认" in lower:
        return "unknown"
    return "unknown"


def _video_selected_action_canonical(value: Any) -> str:
    lower = str(value or "").strip().lower()
    if not lower:
        return ""
    if "full_match_player" in lower or "full_match" in lower or "match_player" in lower or "整场比赛" in lower or "全场" in lower or "比赛分析" in lower:
        return "full_match"
    if "pass_receive_sequence" in lower or "sequence" in lower or "传接球" in lower:
        return "pass_receive_sequence"
    if "receive_control" in lower or "first_touch" in lower or "stop_ball" in lower or lower == "receive" or "touch" in lower or "接球" in lower or "停球" in lower:
        return "receive_control"
    if "shot_instep" in lower or "shoot_like" in lower or "shot_like" in lower or "shoot" in lower or "shot" in lower or "射门" in lower or "clearance" in lower:
        return "shot"
    if "short_pass" in lower or lower == "pass" or "pass_like" in lower or "long_ball" in lower or "传球" in lower:
        return "pass"
    if "review_required" in lower or "uncertain" in lower or "unknown" in lower or "待确认" in lower:
        return "review_required"
    return lower


def _video_main_action_display_name(main_action: str) -> str:
    return {
        "pass": "传球",
        "shot": "射门",
        "receive": "停球",
        "pass_receive_sequence": "传接球",
        "full_match": "单一球员分析",
        "unknown": "动作待确认",
        "review_required": "动作待确认",
    }.get(str(main_action or "").strip(), "动作待确认")


def _video_main_action_template(main_action: str) -> str:
    return {
        "pass": "short_pass",
        "shot": "shot_instep",
        "receive": "receive_control",
        "pass_receive_sequence": "pass_receive_sequence",
        "full_match": "full_match_player",
        "unknown": "review_required",
        "review_required": "review_required",
    }.get(str(main_action or "").strip(), "review_required")


def _safe_round(value: Any, digits: int = 1) -> Optional[float]:
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _full_match_capture_quality(probe: Dict[str, Any]) -> Tuple[str, List[str], float]:
    fps = float(probe.get("fps") or 0.0)
    frame_count = int(probe.get("frame_count") or 0)
    duration_s = float(probe.get("duration_s") or 0.0)
    notes: List[str] = []
    score = 100.0

    if frame_count <= 0 or duration_s <= 0.0:
        notes.append("视频元数据不足，无法建立比赛时间轴。")
        score -= 45.0
    if fps < 25.0:
        notes.append(f"帧率约 {fps:.1f}fps，低于稳定动作事件识别建议值。")
        score -= 20.0
    elif fps < 50.0:
        notes.append(f"帧率约 {fps:.1f}fps，可用于比赛事件统计，微观生物力学结论需保守。")
        score -= 8.0
    if duration_s < 600.0:
        notes.append("当前片段短于完整半场，跑动距离和换人后负荷只能作为片段样本。")
        score -= 15.0

    score = max(0.0, min(100.0, score))
    if score >= 82:
        label = "可进入全场追踪"
    elif score >= 60:
        label = "可做参考分析"
    else:
        label = "需要补充标定"
    return label, notes, round(score, 1)


def _full_match_stat(
    *,
    key: str,
    title: str,
    value: Any,
    unit: str = "",
    detail: str,
    status: str = "needs_tracking",
    source: str = "requires_player_lock",
) -> Dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "value": value,
        "unit": unit,
        "display_value": "待锁定球员" if value is None else f"{value}{unit}",
        "detail": detail,
        "status": status,
        "source": source,
    }


def _single_player_lock_step(
    step_id: str,
    title: str,
    detail: str,
    *,
    status: str = "required",
) -> Dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "detail": detail,
        "status": status,
    }


def _build_full_match_payload(
    video_path: Path,
    *,
    probe: Dict[str, Any],
    selected_action: str,
    analysis_template: Optional[str],
    calibration: Optional[Dict[str, Any]],
    analysis_started_at: float,
) -> Dict[str, Any]:
    generated_at = _now_iso()
    duration_s = float(probe.get("duration_s") or 0.0)
    duration_min = round(duration_s / 60.0, 2) if duration_s > 0 else 0.0
    fps = float(probe.get("fps") or 0.0)
    frame_count = int(probe.get("frame_count") or 0)
    clip_id = _slugify(video_path.stem)
    calibrated = bool(calibration and float((calibration or {}).get("scale_m_per_px", 0.0) or 0.0) > 0.0)
    capture_label, capture_notes, capture_score = _full_match_capture_quality(probe)
    score_level = _score_level_from_overall(capture_score)

    player_lock_steps = [
        _single_player_lock_step(
            "manual_player_box",
            "框选目标球员",
            "在开场或目标球员首次清晰出现的画面框住整个人，后续所有事件只归属这个球员。",
        ),
        _single_player_lock_step(
            "appearance_hint",
            "补充球衣颜色和号码",
            "填写上衣颜色、裤袜颜色、号码和惯用脚，用于跨镜头重识别，减少跟队友或裁判混淆。",
        ),
        _single_player_lock_step(
            "substitution_markers",
            "标记上场/换下时间",
            "如果视频包含换人，先标出上场、换下和中场节点，再按实际在场时间统计片段表现。",
        ),
        _single_player_lock_step(
            "pitch_scale",
            "补充球场尺度参考",
            "需要跑动距离或速度时，至少标定边线、中线、禁区线等场地线；未标定时不输出米制跑动。",
            status="optional",
        ),
    ]

    methodology = [
        "当前不做成熟穿戴式运动监测的重复功能，只做上传视频里的单一球员技术与事件分析。",
        "第一步必须锁定目标球员；没有球员锁定时，不输出跑动距离、传球次数或射门次数。",
        "传球、射门、接球和带球事件会结合目标球员、球轨迹和触球时序共同确认，避免把一次踢球默认成射门。",
        "换人后只按该球员真实在场片段分析，替补前后的比较需要用户标记上场和换下时间点。",
        "生物力学只在清晰关键动作窗口输出，重点看支撑脚、髋-膝-踝发力链、躯干控制和触球结果。"
    ]

    reliability_notes = [
        "当前版本已读取长视频元数据，但尚未收到目标球员锁定框，因此不会假装已经完成比赛监测。",
        "没有球场标定时，不输出精确米制跑动距离，避免把视觉像素位移当作真实距离。",
        "事件统计将以可追踪球员、球轨迹和控球归属共同确认，避免把背景人员或镜头运动计入目标球员。",
        "长视频最多支持 140 分钟；超过上限应先裁剪或分段上传。"
    ] + capture_notes

    match_analysis = {
        "title": "长视频单一球员分析",
        "status": "requires_player_lock",
        "summary": "视频已读取。下一步请先框选目标球员，并补充球衣颜色、号码和换人时间点；未锁定前不输出跑动或传射统计。",
        "capture": {
            "duration_s": round(duration_s, 3),
            "duration_min": duration_min,
            "max_duration_min": 140,
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "quality_label": capture_label,
            "quality_score": capture_score,
            "is_calibrated": calibrated,
            "needs_player_lock": True,
            "needs_pitch_calibration": not calibrated,
            "needs_substitution_markers": True,
        },
        "player_lock_workflow": {
            "status": "required",
            "title": "先锁定目标球员",
            "summary": "请在视频中框选目标球员，所有后续技术动作、传射事件和换人片段都会绑定到同一个 player_id。",
            "steps": player_lock_steps,
            "output_after_lock": [
                "传球、射门、接球、触球和带球事件时间线",
                "该球员关键动作窗口的支撑脚、躯干、触球面和出球结果",
                "换人前后按实际上场分钟拆分的技术效率对比",
                "有场地标定时再输出米制跑动距离、速度和热区"
            ],
        },
        "methodology": methodology,
        "player_tracking": {
            "status": "requires_player_lock",
            "stats": [],
            "heatmap_zones": [],
        },
        "events": {
            "status": "requires_ball_and_player_tracking",
            "stats": [],
            "timeline": [],
        },
        "substitution_analysis": {
            "status": "requires_substitution_markers",
            "segments": [],
            "comparison_rules": [
                "换人后数据按实际出场分钟折算，不直接和首发球员总量比较。",
                "重点看高强度跑占比、冲刺恢复间隔、触球效率和传射选择变化。",
                "如果球员被换下，换下前 5-10 分钟单独检查疲劳导致的速度和决策下降。"
            ],
        },
        "biomechanics": {
            "status": "key_action_windows_required",
            "items": [
                "射门：结合支撑脚位置、髋-膝-踝发力链、躯干前压、出球速度、是否射正和进门区域。",
                "传球：结合支撑脚指向、触球面稳定、出球线路、接球队友关系和下一动作准备度。",
                "跑动：结合加减速、变向角度、步频节奏、疲劳后动作变形和潜在负荷风险。"
            ],
        },
        "reliability_notes": reliability_notes,
    }

    score_block = {
        "overall": round(capture_score, 1),
        **score_level,
        "source": "match_capture_readiness",
        "measurement_mode": "calibrated" if calibrated else "requires_pitch_calibration",
        "action_label": "full_match",
        "action_display_name": "单一球员分析",
    }

    payload: Dict[str, Any] = {
        "analysis_version": VIDEO_ANALYSIS_VERSION,
        "analysis_mode": VIDEO_ANALYSIS_MODE,
        "analyzer_used": VIDEO_FULL_MATCH_ANALYZER,
        "routed_analyzer": VIDEO_FULL_MATCH_ANALYZER,
        "input_video_path": str(video_path),
        "video_path": str(video_path.resolve()),
        "clip_id": clip_id,
        "generated_at": generated_at,
        "duration_s": round(duration_s, 3),
        "video_duration_s": round(duration_s, 3),
        "frame_count": frame_count,
        "sampled_frame_count": 0,
        "selected_action": "full_match",
        "analysis_template": "full_match_player",
        "analysis_routed_by": "user_selected",
        "suggested_action": "full_match",
        "suggestion_reason": "用户选择长视频单一球员分析，自动识别仅作为后续事件辅助。",
        "system_action_suggestion": "full_match",
        "detected_action": "full_match",
        "raw_detected_action": "full_match",
        "final_detected_action": "full_match",
        "mapped_rule_key": "full_match_player",
        "final_mapped_rule_key": "full_match_player",
        "recommended_template": "full_match_player",
        "action_name": "full_match_player",
        "resolved_action_name": "full_match_player",
        "action_label": "full_match",
        "action_display_name": "单一球员分析",
        "route_mismatch": False,
        "route_mismatch_message": "",
        "score": score_block,
        "overall_score": round(capture_score, 1),
        "summary": match_analysis["summary"],
        "match_analysis": match_analysis,
        "primary_metrics": [],
        "rule_metrics": {},
        "feedback_messages": [
            "先完成目标球员锁定，再输出该球员的传球、射门、触球和关键动作窗口。",
            "需要跑动距离和速度时再做球场标定；未标定时不输出虚假的米制数据。"
        ],
        "warnings": list(dict.fromkeys(["requires_player_lock", "requires_pitch_calibration", "requires_substitution_markers"] + ([] if calibrated else ["uncalibrated_pitch"]))),
        "status": "ok",
        "analysis_status": "success",
        "failure_reason": None,
        "failure_message": None,
        "integrity_state": "normal",
        "processing_time_s": round(perf_counter() - analysis_started_at, 3),
        "debug_context": build_debug_context(
            selected_action=selected_action or "full_match",
            system_action_suggestion="full_match",
            analysis_routed_by="user_selected",
            routed_analyzer=VIDEO_FULL_MATCH_ANALYZER,
            video_duration=duration_s,
            frame_count=frame_count,
            sampled_frame_count=0,
            candidate_windows=[],
            selected_window=None,
            warnings=["requires_player_lock", "requires_substitution_markers"],
            fast_mode_enabled=False,
            long_video_localized=False,
            candidate_window_count=0,
            selected_window_index=None,
            selected_window_start_s=None,
            selected_window_end_s=None,
            selected_window_duration_s=None,
            processing_time=round(perf_counter() - analysis_started_at, 3),
            failure_reason="",
            failure_message="",
            route_mismatch_message="",
        ),
    }
    return payload


def _video_resolve_user_selection(
    selected_action: Any = None,
    analysis_template: Any = None,
    *,
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    selected_action_value = _video_selected_action_canonical(selected_action)
    selected_action_family = _video_main_action_class(selected_action_value)
    if selected_action_family in {"pass", "shot", "pass_receive_sequence", "receive", "full_match"}:
        return {
            "has_selection": True,
            "analysis_routed_by": "user_selected",
            "selected_action": selected_action_value,
            "analysis_template": _video_main_action_template(selected_action_family),
            "selection_source": "selected_action",
            "selection_input": str(selected_action or "").strip(),
            "selection_display_name": _video_main_action_display_name(selected_action_family),
            "selection_template": _video_main_action_template(selected_action_family),
            "analysis_template_input": str(analysis_template or "").strip(),
            "selected_action_input": str(selected_action or "").strip(),
        }

    return {
        "has_selection": False,
        "analysis_routed_by": "auto_detected",
        "selected_action": "",
        "analysis_template": "",
        "selection_source": "",
        "selection_input": "",
        "selection_display_name": "",
        "selection_template": "",
        "analysis_template_input": str(analysis_template or "").strip(),
        "selected_action_input": str(selected_action or "").strip(),
    }


def _video_main_action_from_payload(payload: Dict[str, Any]) -> str:
    score = dict(payload.get("score") or {})
    candidates = [
        payload.get("action_name"),
        payload.get("action_label"),
        payload.get("detected_action"),
        payload.get("final_detected_action"),
        payload.get("mapped_rule_key"),
        payload.get("final_mapped_rule_key"),
        payload.get("recommended_template"),
        payload.get("action_display_name"),
        score.get("action_label"),
        score.get("action_display_name"),
    ]
    for candidate in candidates:
        main_action = _video_main_action_class(candidate)
        if main_action not in {"unknown", "review_required"}:
            return main_action
    for candidate in candidates:
        main_action = _video_main_action_class(candidate)
        if main_action == "review_required":
            return "review_required"
    return "unknown"


def _video_coerce_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except Exception:
        return None


def _video_metric_score(metric_results: List[Dict[str, Any]], metric_name: str) -> float:
    for item in metric_results or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("metric")) != metric_name:
            continue
        score = item.get("score")
        if score is None:
            return 0.0
        try:
            return float(score)
        except Exception:
            return 0.0
    return 0.0


def _video_group_score(metric_results: List[Dict[str, Any]], metric_names: Iterable[str]) -> float:
    wanted = {str(name) for name in metric_names}
    scored: List[Tuple[float, float]] = []
    fallback_scores: List[float] = []
    for item in metric_results or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("metric")) not in wanted:
            continue
        score = item.get("score")
        if score is None:
            continue
        try:
            score_value = float(score)
        except Exception:
            continue
        fallback_scores.append(score_value)
        try:
            weight = float(item.get("weight") or 0.0)
        except Exception:
            weight = 0.0
        if weight > 0.0:
            scored.append((score_value, weight))
    if scored:
        total_weight = sum(weight for _, weight in scored)
        if total_weight > 0.0:
            return round(float(sum(score * weight for score, weight in scored) / total_weight), 1)
    if fallback_scores:
        return round(float(sum(fallback_scores) / len(fallback_scores)), 1)
    return 0.0


def _video_pass_receive_time_debug(run_data: Dict[str, Any], event_times: Dict[str, float]) -> Dict[str, Any]:
    samples = list(run_data.get("samples") or [])
    fps = float(run_data.get("fps", 30.0) or 30.0)
    duration_s = float(run_data.get("frame_count", 0) or 0) / fps if fps > 0.0 else 0.0
    clip_end_time = float(samples[-1].get("time", duration_s) or duration_s) if samples else duration_s
    def _event_indices(event_name: str) -> List[int]:
        return [idx for idx, sample in enumerate(samples) if bool((sample.get("events") or {}).get(event_name, False))]

    def _time_at(idx: Optional[int], default: Optional[float] = None) -> Optional[float]:
        if idx is None or idx < 0 or idx >= len(samples):
            return default
        return float(samples[idx].get("time", default if default is not None else 0.0))

    def _first_phase_index_before(phases: Iterable[str], before_idx: Optional[int]) -> Optional[int]:
        limit = len(samples) if before_idx is None else max(0, before_idx)
        wanted = {str(phase) for phase in phases}
        for idx in range(limit):
            if str(samples[idx].get("phase", "")) in wanted:
                return idx
        return None

    def _first_phase_index_after(phases: Iterable[str], after_idx: Optional[int]) -> Optional[int]:
        start = 0 if after_idx is None else min(len(samples), max(0, after_idx + 1))
        wanted = {str(phase) for phase in phases}
        for idx in range(start, len(samples)):
            if str(samples[idx].get("phase", "")) in wanted:
                return idx
        return None

    def _local_peak_speed(start_idx: Optional[int], stop_idx: Optional[int] = None, limit_s: float = 1.25) -> float:
        if start_idx is None:
            return 0.0
        start_time = _time_at(start_idx, 0.0) or 0.0
        peak = 0.0
        for idx in range(start_idx, len(samples)):
            sample_time = _time_at(idx, start_time) or 0.0
            if sample_time - start_time > limit_s:
                break
            if stop_idx is not None and idx > stop_idx:
                break
            peak = max(peak, float(samples[idx].get("ball_speed_ratio", 0.0) or 0.0))
        return peak

    def _build_window(
        *,
        start_time: Optional[float],
        end_time: Optional[float],
        start_event: str,
        end_event: str,
        event_source: str,
        resolved: bool,
        low_confidence: bool,
        confidence: float,
        fallback_to_video_end: bool = False,
    ) -> Dict[str, Any]:
        return {
            "start_time": None if start_time is None else round(float(start_time), 3),
            "end_time": None if end_time is None else round(float(end_time), 3),
            "start_event": start_event,
            "end_event": end_event,
            "event_source": event_source,
            "resolved": resolved,
            "low_confidence": low_confidence,
            "confidence": round(float(confidence), 3),
            "fallback_to_video_end": fallback_to_video_end,
        }

    empty_debug = _build_window(
        start_time=None,
        end_time=None,
        start_event="unresolved",
        end_event="unresolved",
        event_source="unresolved",
        resolved=False,
        low_confidence=True,
        confidence=0.0,
    )
    empty_result = {
        "pass_execution_time_s": {
            "value": None,
            "resolved": False,
            "low_confidence": True,
            "confidence": 0.0,
            **dict(empty_debug),
        },
        "pass_receive_gap_s": {
            "value": None,
            "resolved": False,
            "low_confidence": True,
            "confidence": 0.0,
            **dict(empty_debug),
        },
        "receive_stabilization_time_s": {
            "value": None,
            "resolved": False,
            "low_confidence": True,
            "confidence": 0.0,
            **dict(empty_debug),
        },
        "metric_debug": {
            "pass_execution_time": dict(empty_debug),
            "pass_receive_gap": dict(empty_debug),
            "receive_stabilization_time": dict(empty_debug),
            "fallback_flags": {
                "contact_detected": False,
                "receive_contact_detected": False,
                "stabilization_detected": False,
                "used_proxy_local_window": True,
                "used_video_end_time": False,
                "pass_execution_low_confidence": True,
                "pass_receive_gap_low_confidence": True,
                "receive_stabilization_low_confidence": True,
            },
        },
    }
    if not samples:
        return empty_result

    contact_indices = _event_indices("contact")
    support_indices = _event_indices("support_plant")
    follow_indices = _event_indices("follow_through_complete")
    complete_indices = _event_indices("sequence_complete")

    first_contact_idx = contact_indices[0] if contact_indices else None
    first_contact_time = _time_at(first_contact_idx, float(event_times.get("contact", 0.0) or 0.0))

    pass_start_idx = support_indices[0] if support_indices else None
    if pass_start_idx is None:
        pass_start_idx = _first_phase_index_before(["support", "approach", "preparation"], first_contact_idx)
    if pass_start_idx is None and first_contact_idx is not None:
        pass_start_idx = max(0, first_contact_idx - 1)
    pass_start_time = _time_at(pass_start_idx, max(0.0, float(first_contact_time or 0.0) * 0.2))
    pass_start_time = min(float(pass_start_time or 0.0), float(first_contact_time or 0.0))

    pass_end_idx = None
    if pass_start_idx is not None:
        for idx in contact_indices:
            if idx > pass_start_idx and (_time_at(idx, 0.0) or 0.0) > float(pass_start_time or 0.0) + 0.04:
                pass_end_idx = idx
                break
    if pass_end_idx is None and first_contact_idx is not None:
        pass_end_idx = first_contact_idx
    pass_end_time = _time_at(pass_end_idx, first_contact_time)
    pass_delta = None
    pass_resolved = False
    pass_low_confidence = True
    pass_confidence = 0.0
    pass_start_event = "support_plant"
    pass_start_source = "contact_event"
    if support_indices and pass_start_idx == support_indices[0]:
        pass_start_event = "support_plant"
        pass_start_source = "sample_event"
    elif pass_start_idx is not None and str(samples[pass_start_idx].get("phase", "")) in {"support", "approach", "preparation"}:
        pass_start_event = f"phase_{samples[pass_start_idx].get('phase')}_proxy"
        pass_start_source = "phase_proxy"
    elif pass_start_idx is not None:
        pass_start_event = "pre_contact_proxy"
        pass_start_source = "frame_proxy"

    pass_end_event = "unresolved"
    if pass_start_time is not None and pass_end_time is not None:
        delta = float(pass_end_time) - float(pass_start_time)
        if delta > 0.06:
            pass_delta = delta
            pass_resolved = True
            pass_low_confidence = pass_start_source != "sample_event"
            pass_confidence = 1.0 if pass_start_source == "sample_event" else 0.78
            pass_end_event = "pass_contact"
        else:
            pass_delta = None
            pass_resolved = False
            pass_low_confidence = True
            pass_confidence = 0.0

    receive_contact_idx = None
    if pass_end_idx is not None:
        for idx in contact_indices:
            if idx > pass_end_idx and (_time_at(idx, 0.0) or 0.0) > float(pass_end_time or 0.0) + 0.08:
                receive_contact_idx = idx
                break

    receive_contact_time = _time_at(receive_contact_idx, None)
    receive_contact_event = "receive_contact"
    receive_contact_source = "sample_event"
    receive_gap_value = None
    receive_gap_resolved = False
    receive_gap_low_confidence = True
    receive_gap_confidence = 0.0
    receive_gap_proxy_idx: Optional[int] = None

    if receive_contact_idx is None and pass_end_idx is not None:
        post_peak = _local_peak_speed(pass_end_idx, limit_s=1.20)
        control_speed_limit = max(0.10, post_peak * 0.70)
        for idx in range(pass_end_idx + 1, len(samples)):
            sample = samples[idx]
            sample_time = _time_at(idx, None)
            if sample_time is None or sample_time <= float(pass_end_time or 0.0) + 0.10:
                continue
            phase = str(sample.get("phase", ""))
            support_ball_ratio = float(sample.get("support_ball_ratio", 1.0) or 1.0)
            swing_ball_ratio = float(sample.get("swing_ball_ratio", 1.0) or 1.0)
            ball_speed_ratio = float(sample.get("ball_speed_ratio", 0.0) or 0.0)
            sequence_ready = bool(sample.get("sequence_ready", False)) or phase in {"recovery", "set"}
            if (
                ball_speed_ratio <= control_speed_limit
                and support_ball_ratio <= 0.42
                and swing_ball_ratio <= 0.35
                and sequence_ready
            ):
                receive_gap_proxy_idx = idx
                break
        if receive_gap_proxy_idx is not None:
            receive_contact_time = _time_at(receive_gap_proxy_idx, None)
            receive_contact_event = "receive_contact"
            receive_contact_source = "proxy_control_zone_entry"
            if receive_contact_time is not None and pass_end_time is not None:
                receive_gap_value = float(receive_contact_time) - float(pass_end_time)
                receive_gap_resolved = False
                receive_gap_low_confidence = True
                receive_gap_confidence = 0.45

    if receive_contact_idx is not None and pass_end_time is not None and receive_contact_time is not None:
        receive_gap_value = float(receive_contact_time) - float(pass_end_time)
        receive_gap_resolved = True
        receive_gap_low_confidence = False
        receive_gap_confidence = 1.0

    stabilization_start_idx = receive_contact_idx if receive_contact_idx is not None else receive_gap_proxy_idx
    stabilization_start_time = _time_at(stabilization_start_idx, receive_contact_time)
    stabilization_end_idx = None
    stabilization_value = None
    stabilization_resolved = False
    stabilization_low_confidence = True
    stabilization_confidence = 0.0
    stabilization_event_source = "unresolved"
    stabilization_end_event = "unresolved"

    if stabilization_start_idx is not None and stabilization_start_time is not None:
        post_peak = _local_peak_speed(stabilization_start_idx, limit_s=1.40)
        speed_limit = max(0.05, post_peak * 0.35)
        control_limit = 0.38
        for idx in range(stabilization_start_idx + 1, len(samples) - 1):
            sample = samples[idx]
            next_sample = samples[idx + 1]
            sample_time = _time_at(idx, None)
            if sample_time is None or sample_time <= float(stabilization_start_time) + 0.10:
                continue
            phase = str(sample.get("phase", ""))
            ready = bool(sample.get("sequence_ready", False)) or phase in {"recovery", "set"}
            if not ready:
                continue
            speed = float(sample.get("ball_speed_ratio", 0.0) or 0.0)
            next_speed = float(next_sample.get("ball_speed_ratio", 0.0) or 0.0)
            support_ratio = float(sample.get("support_ball_ratio", 1.0) or 1.0)
            next_support_ratio = float(next_sample.get("support_ball_ratio", 1.0) or 1.0)
            if speed <= speed_limit and next_speed <= speed_limit and support_ratio <= control_limit and next_support_ratio <= control_limit:
                stabilization_end_idx = idx + 1
                stabilization_value = float(_time_at(stabilization_end_idx, sample_time) or sample_time) - float(stabilization_start_time)
                stabilization_event_source = "stable_control_window"
                stabilization_end_event = "receive_stable_state"
                stabilization_resolved = receive_contact_idx is not None
                stabilization_low_confidence = receive_contact_idx is None
                stabilization_confidence = 1.0 if receive_contact_idx is not None else 0.55
                break

    if stabilization_value is None and stabilization_start_time is not None:
        stabilization_low_confidence = True
        stabilization_confidence = 0.0

    if pass_delta is not None:
        pass_execution_value = float(pass_delta)
    else:
        pass_execution_value = None

    if receive_gap_value is not None and receive_gap_resolved:
        pass_receive_gap_value = float(receive_gap_value)
    elif receive_gap_value is not None:
        pass_receive_gap_value = float(receive_gap_value)
    else:
        pass_receive_gap_value = None

    if stabilization_value is not None and stabilization_resolved and not stabilization_low_confidence:
        receive_stabilization_value = float(stabilization_value)
    elif stabilization_value is not None:
        receive_stabilization_value = float(stabilization_value)
    else:
        receive_stabilization_value = None

    pass_execution_debug = _build_window(
        start_time=pass_start_time,
        end_time=pass_end_time,
        start_event=pass_start_event,
        end_event=pass_end_event,
        event_source=pass_start_source if pass_start_idx is not None else "unresolved",
        resolved=pass_resolved,
        low_confidence=pass_low_confidence,
        confidence=pass_confidence,
    )
    pass_gap_debug = _build_window(
        start_time=pass_end_time,
        end_time=receive_contact_time,
        start_event="pass_contact",
        end_event=receive_contact_event,
        event_source="contact_pair" if receive_contact_time is not None else "unresolved",
        resolved=receive_gap_resolved,
        low_confidence=receive_gap_low_confidence,
        confidence=receive_gap_confidence,
    )
    receive_stability_debug = _build_window(
        start_time=receive_contact_time,
        end_time=None if stabilization_end_idx is None else _time_at(stabilization_end_idx, None),
        start_event=receive_contact_event,
        end_event=stabilization_end_event,
        event_source=stabilization_event_source,
        resolved=stabilization_resolved,
        low_confidence=stabilization_low_confidence,
        confidence=stabilization_confidence,
    )

    if pass_execution_value is None:
        pass_execution_debug["low_confidence"] = True
        pass_execution_debug["resolved"] = False
        pass_execution_debug["confidence"] = 0.0
    if pass_gap_debug["end_time"] is None:
        pass_gap_debug["low_confidence"] = True
        pass_gap_debug["resolved"] = False
        pass_gap_debug["confidence"] = 0.0
    if receive_stability_debug["end_time"] is None:
        receive_stability_debug["low_confidence"] = True
        receive_stability_debug["resolved"] = False
        receive_stability_debug["confidence"] = 0.0

    fallback_flags = {
        "contact_detected": first_contact_idx is not None,
        "receive_contact_detected": receive_contact_idx is not None,
        "stabilization_detected": stabilization_end_idx is not None,
        "used_proxy_local_window": pass_start_source != "sample_event" or receive_gap_proxy_idx is not None or receive_contact_idx is None,
        "used_video_end_time": False,
        "pass_execution_low_confidence": bool(pass_execution_debug["low_confidence"]),
        "pass_receive_gap_low_confidence": bool(pass_gap_debug["low_confidence"]),
        "receive_stabilization_low_confidence": bool(receive_stability_debug["low_confidence"]),
    }

    metric_debug = {
        "pass_execution_time": dict(pass_execution_debug),
        "pass_receive_gap": dict(pass_gap_debug),
        "receive_stabilization_time": dict(receive_stability_debug),
        "fallback_flags": dict(fallback_flags),
    }

    return {
        "pass_execution_time_s": {
            "value": round(float(pass_execution_value), 3) if pass_execution_value is not None else None,
            "resolved": bool(pass_execution_debug["resolved"]),
            "low_confidence": bool(pass_execution_debug["low_confidence"]),
            "confidence": float(pass_execution_debug["confidence"]),
            **dict(pass_execution_debug),
        },
        "pass_receive_gap_s": {
            "value": round(float(pass_receive_gap_value), 3) if pass_receive_gap_value is not None else None,
            "resolved": bool(pass_gap_debug["resolved"]),
            "low_confidence": bool(pass_gap_debug["low_confidence"]),
            "confidence": float(pass_gap_debug["confidence"]),
            **dict(pass_gap_debug),
        },
        "receive_stabilization_time_s": {
            "value": round(float(receive_stabilization_value), 3) if receive_stabilization_value is not None else None,
            "resolved": bool(receive_stability_debug["resolved"]),
            "low_confidence": bool(receive_stability_debug["low_confidence"]),
            "confidence": float(receive_stability_debug["confidence"]),
            **dict(receive_stability_debug),
        },
        "metric_debug": metric_debug,
    }


def _video_collect_action_candidates(run_data: Dict[str, Any], evidence: Dict[str, float]) -> Dict[str, Any]:
    temporal_prediction = dict(run_data.get("temporal_best_prediction") or {})
    votes = dict(run_data.get("temporal_action_votes") or {})
    sequence_snapshot = dict(run_data.get("sequence_snapshot") or {})
    features = dict(temporal_prediction.get("features") or {})
    sequence_label = str(run_data.get("sequence_action_label") or sequence_snapshot.get("action_label") or "soccer_idle")
    sequence_confidence = float(sequence_snapshot.get("phase_confidence", 0.0) or 0.0)
    evidence_confidence = float(evidence.get("analysis_confidence", 0.0) or 0.0)

    candidate_map: Dict[str, Dict[str, Any]] = {}

    def _record_candidate(action_name: str, score: float, source: str) -> None:
        action = str(action_name or "").strip()
        if not action or action in {"uncertain", "soccer_idle"}:
            return
        try:
            score_value = float(_clamp(score, 0.0, 1.0))
        except Exception:
            score_value = 0.0
        if score_value <= 0.0:
            return
        entry = candidate_map.setdefault(action, {"action": action, "score": 0.0, "sources": []})
        entry["score"] = round(float(max(float(entry["score"]), score_value)), 3)
        if source not in entry["sources"]:
            entry["sources"].append(source)

    feature_scores = {
        "pass_like": float(features.get("pass_score", 0.0) or 0.0),
        "shot_like": float(features.get("shoot_score", 0.0) or 0.0),
        "first_touch_like": float(features.get("first_touch_score", 0.0) or 0.0),
        "dribble_like": float(features.get("dribble_score", 0.0) or 0.0),
        "juggle_like": float(features.get("juggle_score", 0.0) or 0.0),
    }
    for action_name, score in feature_scores.items():
        _record_candidate(action_name, score, f"temporal_features.{action_name}")

    if temporal_prediction.get("label") and str(temporal_prediction.get("label")) != "soccer_idle":
        _record_candidate(
            str(temporal_prediction.get("label")),
            float(temporal_prediction.get("confidence", 0.0) or 0.0),
            "temporal_best_prediction",
        )

    total_votes = float(sum(int(count) for count in votes.values()) or 0.0)
    if total_votes > 0.0:
        for vote_action, vote_count in votes.items():
            vote_ratio = float(vote_count) / max(1.0, total_votes)
            _record_candidate(str(vote_action), min(0.90, 0.34 + 0.58 * vote_ratio), "temporal_action_votes")

    if sequence_label and sequence_label != "soccer_idle":
        _record_candidate(sequence_label, max(0.25, min(0.92, 0.30 + 0.55 * sequence_confidence + 0.15 * evidence_confidence)), "sequence_snapshot.action_label")

    raw_action_candidates = sorted(candidate_map.values(), key=lambda item: (-float(item["score"]), str(item["action"])))
    candidate_scores = {str(item["action"]): float(item["score"]) for item in raw_action_candidates}
    sequence_context = {
        "sequence_label": sequence_label,
        "sequence_confidence": round(float(sequence_confidence), 3),
        "sequence_active": bool(sequence_snapshot.get("sequence_active")),
        "sequence_ready": bool(sequence_snapshot.get("sequence_ready")),
        "phase_locked": bool(sequence_snapshot.get("phase_locked")),
        "events": dict(sequence_snapshot.get("events") or {}),
        "votes": votes,
        "pass_votes": int(votes.get("pass_like", 0) or 0),
        "first_touch_votes": int(votes.get("first_touch_like", 0) or 0),
        "pass_score": round(float(feature_scores["pass_like"]), 3),
        "first_touch_score": round(float(feature_scores["first_touch_like"]), 3),
        "shot_score": round(float(feature_scores["shot_like"]), 3),
        "evidence_confidence": round(float(evidence_confidence), 3),
    }
    return {
        "raw_action_candidates": raw_action_candidates,
        "candidate_scores": candidate_scores,
        "sequence_context": sequence_context,
    }


def _video_sequence_upgrade_decision(
    raw_detected_action: str,
    candidate_scores: Dict[str, Any],
    sequence_context: Dict[str, Any],
) -> Tuple[bool, str, float]:
    pass_score = float(candidate_scores.get("pass_like", 0.0) or 0.0)
    first_touch_score = float(candidate_scores.get("first_touch_like", 0.0) or 0.0)
    sequence_label = str(sequence_context.get("sequence_label", "soccer_idle") or "soccer_idle")
    sequence_label_score = float(candidate_scores.get(sequence_label, 0.0) or 0.0)
    sequence_confidence = float(sequence_context.get("sequence_confidence", 0.0) or 0.0)
    evidence_confidence = float(sequence_context.get("evidence_confidence", 0.0) or 0.0)
    sequence_active = bool(sequence_context.get("sequence_active"))
    sequence_ready = bool(sequence_context.get("sequence_ready"))
    phase_locked = bool(sequence_context.get("phase_locked"))
    events = dict(sequence_context.get("events") or {})
    pass_votes = int(sequence_context.get("pass_votes", 0) or 0)
    first_touch_votes = int(sequence_context.get("first_touch_votes", 0) or 0)
    joint_votes = pass_votes > 0 and first_touch_votes > 0
    event_chain = bool(events.get("support_plant")) and bool(events.get("contact")) and (
        bool(events.get("follow_through_complete")) or bool(events.get("sequence_complete"))
    )
    sequence_support = sequence_active or sequence_ready or phase_locked or joint_votes or event_chain
    pair_signal = 0.44 * pass_score + 0.44 * first_touch_score + 0.06 * sequence_confidence + 0.06 * evidence_confidence

    if pass_score >= 0.50 and first_touch_score >= 0.50:
        return True, (
            f"pass_like={pass_score:.2f}, first_touch_like={first_touch_score:.2f}, "
            f"sequence_confidence={sequence_confidence:.2f}, sequence_support={sequence_support}, "
            f"joint_votes={joint_votes}"
        ), float(pair_signal)

    if pass_score >= 0.35 and first_touch_score >= 0.45 and sequence_support and pair_signal >= 0.55:
        return True, (
            f"pass_like={pass_score:.2f}, first_touch_like={first_touch_score:.2f}, "
            f"pair_signal={pair_signal:.2f}, sequence_label={sequence_label}, sequence_support={sequence_support}"
        ), float(pair_signal)

    if raw_detected_action == "first_touch_like" and pass_score >= 0.30 and first_touch_score >= 0.50 and sequence_support and pair_signal >= 0.50:
        return True, (
            f"first_touch_like 主标签但存在前置传球信号，pass_like={pass_score:.2f}, "
            f"first_touch_like={first_touch_score:.2f}, pair_signal={pair_signal:.2f}, "
            f"sequence_label={sequence_label}, sequence_support={sequence_support}"
        ), float(pair_signal)

    if sequence_label_score >= 0.55 and pass_score >= 0.30 and first_touch_score >= 0.45 and sequence_support:
        return True, (
            f"序列候选已显著，sequence_label={sequence_label}, sequence_label_score={sequence_label_score:.2f}, "
            f"pass_like={pass_score:.2f}, first_touch_like={first_touch_score:.2f}, sequence_support={sequence_support}"
        ), float(pair_signal)

    return False, (
        f"未达到序列升级阈值：pass_like={pass_score:.2f}, first_touch_like={first_touch_score:.2f}, "
        f"pair_signal={pair_signal:.2f}, sequence_label={sequence_label}, sequence_support={sequence_support}"
    ), float(pair_signal)


def _video_map_detected_action(detected_action: str, rules: Optional[Dict[str, Any]] = None) -> str:
    action_name = str(detected_action or "").strip()
    if not action_name or action_name in {"uncertain", "soccer_idle"}:
        return VIDEO_FALLBACK_TEMPLATE
    mapped = _VIDEO_ACTION_MAPPING.get(action_name, _VIDEO_ACTION_MAPPING.get(action_name.lower(), action_name))
    if not mapped:
        return VIDEO_FALLBACK_TEMPLATE
    try:
        return resolve_action_name(mapped, rules or load_football_rules())
    except Exception:
        return mapped or VIDEO_FALLBACK_TEMPLATE


def video_analysis_router_v1(
    detected_action: str | Dict[str, Any],
    action_confidence: float | None = None,
    *,
    rules: Optional[Dict[str, Any]] = None,
    run_data: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, float]] = None,
    evidence: Optional[Dict[str, float]] = None,
    selected_action: str | None = None,
    analysis_template: str | None = None,
) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    evidence = evidence or {}
    detection_context = dict(detected_action) if isinstance(detected_action, dict) else {}
    raw_detected_action = str(
        detection_context.get(
            "raw_detected_action",
            detection_context.get("detected_action", detected_action if isinstance(detected_action, str) else "uncertain"),
        )
    ).strip() or "uncertain"
    action_confidence_value = float(
        detection_context.get("action_confidence", action_confidence if action_confidence is not None else 0.0) or 0.0
    )
    semantic_action_label = str(detection_context.get("action_label") or raw_detected_action or "uncertain").strip() or "uncertain"
    action_display_name = str(detection_context.get("action_display_name") or "").strip() or _video_action_display_name(semantic_action_label)
    confidence_gap = float(detection_context.get("confidence_gap", 0.0) or 0.0)
    needs_confirmation = bool(detection_context.get("needs_confirmation", False))
    uncertainty_reasons = list(detection_context.get("uncertainty_reasons") or [])
    action_candidates = list(detection_context.get("action_candidates") or [])
    stage1_action_label = str(detection_context.get("stage1_action_label") or "non_kick")
    stage1_confidence = float(detection_context.get("stage1_confidence", 0.0) or 0.0)
    goal_visible = bool(detection_context.get("goal_visible", False))

    candidate_context = _video_collect_action_candidates(run_data or {}, evidence)
    raw_action_candidates = list(detection_context.get("raw_action_candidates") or candidate_context.get("raw_action_candidates") or [])
    candidate_scores = dict(detection_context.get("candidate_scores") or candidate_context.get("candidate_scores") or {})
    sequence_context = dict(detection_context.get("sequence_context") or candidate_context.get("sequence_context") or {})

    if not candidate_scores and raw_action_candidates:
        candidate_scores = {
            str(item.get("action")): float(item.get("score", 0.0) or 0.0)
            for item in raw_action_candidates
            if str(item.get("action") or "").strip()
        }
    if not raw_action_candidates and candidate_scores:
        raw_action_candidates = [
            {"action": str(action_name), "score": round(float(score_value), 3), "sources": ["candidate_scores"]}
            for action_name, score_value in candidate_scores.items()
            if float(score_value or 0.0) > 0.0
        ]
        raw_action_candidates.sort(key=lambda item: (-float(item["score"]), str(item["action"])))

    sequence_upgrade_applied, sequence_upgrade_reason, sequence_upgrade_score = _video_sequence_upgrade_decision(
        raw_detected_action,
        candidate_scores,
        sequence_context,
    )

    if sequence_upgrade_applied:
        action_confidence_value = max(float(action_confidence_value), float(sequence_upgrade_score))

    if needs_confirmation:
        final_detected_action = "uncertain"
    elif sequence_upgrade_applied or raw_detected_action in {"pass_receive_sequence", "pass_receive_sequence_like"}:
        final_detected_action = "pass_receive_sequence"
    else:
        final_detected_action = semantic_action_label if semantic_action_label else raw_detected_action
    mapped_rule_key = _video_map_detected_action(final_detected_action, rules)
    supported = mapped_rule_key in _VIDEO_SUPPORTED_ANALYZERS and (not needs_confirmation or final_detected_action not in {"soccer_idle"})
    confidence_low = action_confidence_value < VIDEO_ACTION_CONFIDENCE_THRESHOLD
    fallback_used = needs_confirmation or final_detected_action in {"uncertain", "soccer_idle"} or confidence_low or not supported
    if sequence_upgrade_applied and supported and not needs_confirmation:
        fallback_used = False
    analyzer_used = _VIDEO_SUPPORTED_ANALYZERS.get(mapped_rule_key, VIDEO_ROUTER_ANALYZER) if supported else VIDEO_ROUTER_ANALYZER
    system_action_suggestion = _video_main_action_class(final_detected_action if final_detected_action else semantic_action_label)
    if system_action_suggestion in {"unknown", "review_required"}:
        system_action_suggestion = ""

    route = {
        "raw_detected_action": raw_detected_action,
        "action_label": semantic_action_label,
        "action_display_name": action_display_name,
        "action_candidates": action_candidates,
        "confidence": float(_clamp(action_confidence_value, 0.0, 1.0)),
        "confidence_gap": float(_clamp(confidence_gap, 0.0, 1.0)),
        "needs_confirmation": needs_confirmation,
        "uncertainty_reasons": uncertainty_reasons,
        "stage1_action_label": stage1_action_label,
        "stage1_confidence": float(_clamp(stage1_confidence, 0.0, 1.0)),
        "detected_action": final_detected_action,
        "final_detected_action": final_detected_action,
        "action_confidence": float(_clamp(action_confidence_value, 0.0, 1.0)),
        "mapped_rule_key": mapped_rule_key,
        "final_mapped_rule_key": mapped_rule_key,
        "recommended_template": mapped_rule_key,
        "analyzer_used": analyzer_used,
        "fallback_used": bool(fallback_used),
        "whether_fallback_template_used": bool(fallback_used),
        "unsupported_action_for_current_analyzer": not supported,
        "raw_action_candidates": raw_action_candidates,
        "candidate_scores": candidate_scores,
        "sequence_upgrade_applied": bool(sequence_upgrade_applied),
        "sequence_upgrade_reason": sequence_upgrade_reason,
        "sequence_context": sequence_context,
        "system_action_suggestion": system_action_suggestion,
        "route_mismatch": False,
        "route_mismatch_message": "",
    }

    manual_selection = _video_resolve_user_selection(selected_action, analysis_template, rules=rules)
    if manual_selection.get("has_selection"):
        manual_action = str(manual_selection.get("selected_action") or "").strip() or final_detected_action
        manual_template = str(manual_selection.get("analysis_template") or "").strip() or _video_main_action_template(manual_action)
        manual_display_name = str(manual_selection.get("selection_display_name") or "").strip() or _video_main_action_display_name(manual_action)
        auto_action = _video_main_action_class(final_detected_action if final_detected_action else semantic_action_label)
        if auto_action in {"unknown", "review_required"}:
            auto_action = _video_main_action_class(semantic_action_label)
        route_mismatch = bool(
            auto_action not in {"unknown", "review_required"}
            and auto_action != manual_action
        )
        suggestion_reason = ""
        suggested_action = ""
        route_policy = resolve_analysis_route(
            manual_action,
            analysis_template=manual_template,
            system_action_suggestion=auto_action if auto_action not in {"unknown", "review_required"} else "",
            analysis_routed_by="user_selected",
        )
        if auto_action not in {"unknown", "review_required"} and auto_action != manual_action:
            suggested_action = auto_action
            suggestion_reason = f"系统自动识别更像{_video_main_action_display_name(auto_action)}，已按用户选择的{manual_display_name}分析。"
        elif needs_confirmation or confidence_low:
            suggestion_reason = f"系统自动识别暂不稳定，已按用户选择的{manual_display_name}分析。"

        route.update(
            {
                "selected_action": manual_action,
                "analysis_template": manual_template,
                "analysis_routed_by": route_policy.analysis_routed_by,
                "routed_analyzer": route_policy.routed_analyzer,
                "suggested_action": suggested_action,
                "suggestion_reason": suggestion_reason,
                "system_action_suggestion": route_policy.system_action_suggestion,
                "route_mismatch": bool(route_mismatch or route_policy.route_mismatch),
                "route_mismatch_message": route_policy.route_mismatch_message
                or (
                    f"你当前选择的是“{manual_display_name}”，但系统自动识别更像“{_video_main_action_display_name(auto_action)}”。已按当前选择继续分析。"
                    if route_mismatch
                    else ""
                ),
                "detected_action": manual_action,
                "final_detected_action": manual_action,
                "action_label": manual_action,
                "action_display_name": manual_display_name,
                "mapped_rule_key": manual_template,
                "final_mapped_rule_key": manual_template,
                "recommended_template": manual_template,
                "analyzer_used": route_policy.routed_analyzer,
                "fallback_used": False,
                "whether_fallback_template_used": False,
                "needs_confirmation": False,
                "unsupported_action_for_current_analyzer": manual_template not in _VIDEO_SUPPORTED_ANALYZERS,
                "integrity_state": route_policy.integrity_state,
                "warnings": list(dict.fromkeys(list(route.get("warnings") or []) + list(route_policy.warnings))),
            }
        )
    else:
        route_policy = resolve_analysis_route(
            final_detected_action,
            analysis_template=mapped_rule_key,
            system_action_suggestion=system_action_suggestion,
            analysis_routed_by="auto_detected",
        )
        route.update(
            {
                "selected_action": final_detected_action,
                "analysis_template": mapped_rule_key,
                "analysis_routed_by": route_policy.analysis_routed_by,
                "routed_analyzer": route_policy.routed_analyzer or final_detected_action,
                "suggested_action": "",
                "suggestion_reason": "",
                "system_action_suggestion": route_policy.system_action_suggestion or system_action_suggestion,
                "route_mismatch": bool(route_policy.route_mismatch),
                "route_mismatch_message": route_policy.route_mismatch_message,
                "analyzer_used": route_policy.routed_analyzer or VIDEO_ROUTER_ANALYZER,
                "integrity_state": route_policy.integrity_state,
                "warnings": list(dict.fromkeys(list(route.get("warnings") or []) + list(route_policy.warnings))),
            }
        )

    return route


def video_analysis_router(
    detected_action: str | Dict[str, Any],
    action_confidence: float | None = None,
    *,
    rules: Optional[Dict[str, Any]] = None,
    run_data: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, float]] = None,
    evidence: Optional[Dict[str, float]] = None,
    selected_action: str | None = None,
    analysis_template: str | None = None,
) -> Dict[str, Any]:
    return video_analysis_router_v1(
        detected_action,
        action_confidence,
        rules=rules,
        run_data=run_data,
        metrics=metrics,
        evidence=evidence,
        selected_action=selected_action,
        analysis_template=analysis_template,
    )


def _unsupported_action_issue(detected_action: str, mapped_rule_key: str, action_confidence: float) -> Dict[str, Any]:
    return {
        "id": "unsupported_action_for_current_analyzer",
        "title": "当前分析器暂不支持该动作",
        "phase": "setup",
        "time": 0.0,
        "short_hint": f"当前仅接入 short_pass / pass_receive_sequence / receive_control / shot_instep 最小分析器，{mapped_rule_key} 暂未进入正式评分。",
        "explanation": (
            f"检测到 {detected_action}（置信度 {float(action_confidence):.2f}），"
            f"已映射到 {mapped_rule_key}，但当前分析器暂未支持该动作。"
        ),
        "fix_advice": "请接入对应动作的专项分析器后，再输出正式评分。",
        "training_advice": "先继续录制本次动作，但结果暂时只作为路由参考。",
        "severity": 0.85,
    }


def _proxy_action_safety(metrics: Dict[str, float], quality_result: Dict[str, Any]) -> float:
    visibility = _clamp(float(metrics.get("visibility", 0.0)))
    stability = _clamp(float(metrics.get("stability", 0.0)))
    balance = abs(float(metrics.get("balance", 0.0)))
    ball_contact = _clamp(float(metrics.get("ball_contact", 0.0)))
    safety = 100.0 * (
        0.34 * visibility
        + 0.30 * stability
        + 0.18 * ball_contact
        + 0.18 * max(0.0, 1.0 - min(1.0, balance / 0.30))
    )
    if str(quality_result.get("quality_status", "pass")) == "fail":
        safety *= 0.55
    elif str(quality_result.get("quality_status", "pass")) == "outcome_only":
        safety *= 0.85
    return round(float(_clamp(safety, 0.0, 100.0)), 1)


def _video_rule_phase(rule_id: str) -> str:
    return _VIDEO_RULE_PHASES.get(str(rule_id), "contact")


def _video_rule_time(rule_id: str, event_times: Dict[str, float]) -> float:
    phase = _video_rule_phase(rule_id)
    return float(event_times.get(phase, event_times.get("contact", 0.0)))


def _video_issue_from_rule(
    rule: Dict[str, Any],
    *,
    mapped_rule_key: str,
    event_times: Dict[str, float],
    fallback_hint: str,
) -> Dict[str, Any]:
    rule_id = str(rule.get("id") or rule.get("metric") or "issue")
    severity = rule.get("severity", 0.0)
    try:
        severity_num = float(severity)
    except Exception:
        severity_num = 0.0
    title = str(rule.get("label") or rule.get("metric") or rule_id)
    reason = str(rule.get("reason") or title)
    return {
        "id": rule_id,
        "title": title,
        "phase": _video_rule_phase(rule_id),
        "time": round(float(_video_rule_time(rule_id, event_times)), 3),
        "short_hint": title,
        "explanation": reason,
        "fix_advice": fallback_hint or reason,
        "training_advice": fallback_hint or reason,
        "severity": round(float(_clamp(severity_num, 0.0, 1.0)), 3),
    }


def _uncertainty_issue(action_confidence: float, mapped_rule_key: str) -> Dict[str, Any]:
    return {
        "id": "action_pattern_unclear",
        "title": "动作识别不够明确",
        "phase": "setup",
        "time": 0.0,
        "short_hint": f"当前按 {mapped_rule_key} 模板做保守分析",
        "explanation": f"动作识别置信度偏低（{action_confidence:.2f}），系统已使用推荐模板进行保守分析。",
        "fix_advice": "请把动作做得更完整、更清晰，再重新录制一条稳定视频。",
        "training_advice": "先放慢节奏，把动作模式做明确，再逐步提速。",
        "severity": 0.55,
    }


def _video_detect_action_context(run_data: Dict[str, Any], metrics: Dict[str, float], evidence: Dict[str, float]) -> Dict[str, Any]:
    candidate_context = _video_collect_action_candidates(run_data, evidence)
    legacy_raw_candidates = list(candidate_context.get("raw_action_candidates") or [])
    legacy_candidate_scores = dict(candidate_context.get("candidate_scores") or {})
    sequence_context = dict(candidate_context.get("sequence_context") or {})

    decision = build_video_action_decision(run_data, metrics, evidence)
    raw_action_candidates = list(decision.get("raw_action_candidates") or [])
    candidate_scores = dict(decision.get("candidate_scores") or {})
    action_candidates = list(decision.get("action_candidates") or [])
    uncertainty_reasons = list(decision.get("uncertainty_reasons") or [])
    needs_confirmation = bool(decision.get("needs_confirmation", False))
    confidence = float(decision.get("confidence", 0.0) or 0.0)
    confidence_gap = float(decision.get("confidence_gap", 0.0) or 0.0)
    action_label = str(decision.get("action_label") or "uncertain")
    action_display_name = str(decision.get("action_display_name") or "动作待确认")
    stage1_action_label = str(decision.get("stage1_action_label") or "non_kick")
    stage1_confidence = float(decision.get("stage1_confidence", 0.0) or 0.0)
    detection_source = str(decision.get("detection_source") or "rule_based_temporal_kick_v2")
    recommended_template = str(decision.get("recommended_template") or VIDEO_FALLBACK_TEMPLATE)
    goal_visible = bool(decision.get("goal_visible", False))

    if not raw_action_candidates and legacy_raw_candidates:
        raw_action_candidates = legacy_raw_candidates
    if not candidate_scores and legacy_candidate_scores:
        candidate_scores = legacy_candidate_scores
    if not action_candidates and raw_action_candidates:
        action_candidates = [
            {
                "label": str(item.get("action") or item.get("label") or "uncertain"),
                "action": str(item.get("action") or item.get("label") or "uncertain"),
                "display_name": str(item.get("display_name") or item.get("action") or item.get("label") or "候选动作"),
                "score": float(item.get("score", 0.0) or 0.0),
                "sources": list(item.get("sources") or []),
                "template": str(item.get("template") or VIDEO_FALLBACK_TEMPLATE),
            }
            for item in raw_action_candidates
        ]

    detected_action = action_label if not needs_confirmation else "uncertain"
    final_detected_action = detected_action
    action_confidence = confidence if not needs_confirmation else min(confidence, 0.59)
    source = detection_source
    if not raw_action_candidates:
        source = "none"

    feature_scores = {
        "short_pass": float(candidate_scores.get("pass_like", 0.0) or candidate_scores.get("pass", 0.0) or 0.0),
        "shot_instep": float(candidate_scores.get("shot_like", 0.0) or candidate_scores.get("shot", 0.0) or 0.0),
        "receive_control": float(candidate_scores.get("first_touch_like", 0.0) or candidate_scores.get("first_touch", 0.0) or 0.0),
        "dribble_change_direction": float(candidate_scores.get("dribble_like", 0.0) or 0.0),
        "juggling": float(candidate_scores.get("juggle_like", 0.0) or 0.0),
    }
    direct_rule_key = None
    if not needs_confirmation and action_label not in {"uncertain", "non_kick"}:
        try:
            direct_rule_key = resolve_action_name(recommended_template, load_football_rules())
        except Exception:
            direct_rule_key = None

    if needs_confirmation:
        ranked_features = sorted(feature_scores.items(), key=lambda item: (-item[1], item[0]))
        best_feature_rule, best_feature_score = ranked_features[0]
        if best_feature_score >= 0.30:
            recommended_template = best_feature_rule
        else:
            recommended_template = VIDEO_FALLBACK_TEMPLATE
    elif direct_rule_key is None:
        ranked_features = sorted(feature_scores.items(), key=lambda item: (-item[1], item[0]))
        best_feature_rule, best_feature_score = ranked_features[0]
        if best_feature_score >= 0.25:
            recommended_template = best_feature_rule

    whether_fallback_template_used = bool(needs_confirmation or recommended_template != direct_rule_key or action_label == "uncertain")

    return {
        "stage1_action_label": stage1_action_label,
        "stage1_confidence": round(float(stage1_confidence), 3),
        "detected_action": detected_action,
        "final_detected_action": final_detected_action,
        "action_label": action_label,
        "action_display_name": action_display_name,
        "action_confidence": float(_clamp(action_confidence, 0.0, 1.0)),
        "confidence": float(_clamp(confidence, 0.0, 1.0)),
        "confidence_gap": float(_clamp(confidence_gap, 0.0, 1.0)),
        "needs_confirmation": needs_confirmation,
        "uncertainty_reasons": uncertainty_reasons,
        "action_candidates": action_candidates,
        "detection_source": source,
        "recommended_template": recommended_template,
        "raw_action_candidates": raw_action_candidates,
        "candidate_scores": candidate_scores,
        "sequence_context": {**sequence_context, "goal_visible": goal_visible},
        "whether_fallback_template_used": whether_fallback_template_used,
        "fallback_used": whether_fallback_template_used,
        "mapped_rule_key": recommended_template,
        "final_mapped_rule_key": recommended_template,
        "analyzer_used": str(decision.get("analyzer_used") or VIDEO_ROUTER_ANALYZER),
    }


def _video_rule_metrics(
    mapped_rule_key: str,
    metrics: Dict[str, float],
    run_data: Dict[str, Any],
    event_times: Dict[str, float],
    calibration: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    fps = float(run_data.get("fps", 30.0) or 30.0)
    body_span_px = float(metrics.get("body_span_px", 1.0) or 1.0)
    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28) or 0.28)
    swing_ball_ratio = float(metrics.get("swing_ball_ratio", 0.16) or 0.16)
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.0) or 0.0)
    stability = float(metrics.get("stability", 0.0) or 0.0)
    sequence_confidence = float(metrics.get("sequence_confidence", 0.0) or 0.0)
    visibility = float(metrics.get("visibility", 0.0) or 0.0)
    ball_contact = float(metrics.get("ball_contact", 0.0) or 0.0)
    ball_confidence = float(metrics.get("ball_confidence", 0.0) or 0.0)
    move_ratio = float(metrics.get("move_ratio", 0.0) or 0.0)
    scale_m_per_px = float((calibration or {}).get("scale_m_per_px", 0.0) or 0.0)
    measurement_mode = "calibrated" if scale_m_per_px > 0.0 else "proxy"
    duration_s = float(run_data.get("frame_count", 0) or 0) / fps if fps > 0.0 else 0.0

    if mapped_rule_key == "shot_instep":
        if scale_m_per_px > 0.0:
            max_ball_speed = max(0.0, ball_speed_ratio * body_span_px * scale_m_per_px * fps)
            speed_metric_key = "max_ball_speed_mps"
        else:
            max_ball_speed = max(0.0, ball_speed_ratio * fps * 2.0)
            speed_metric_key = "max_ball_speed_proxy_mps"
        target_zone_hit = 3.0 if ball_contact > 0.5 and ball_speed_ratio >= 0.18 else (2.0 if ball_contact > 0.5 and ball_speed_ratio >= 0.10 else (1.0 if ball_contact > 0.0 else 0.0))
        consistency_cv_pct = max(0.0, 100.0 * (1.0 - _clamp(0.62 * stability + 0.38 * sequence_confidence)))
        return {
            speed_metric_key: round(float(max_ball_speed), 3),
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "target_zone_hit": float(target_zone_hit),
            "shot_consistency_cv_pct": round(float(consistency_cv_pct), 2),
            "support_foot_lateral_offset_cm": round(float(support_ball_ratio * body_span_px * (scale_m_per_px or 0.02) * 100.0), 2),
            "support_foot_ap_offset_cm": round(float((support_ball_ratio - 0.20) * body_span_px * (scale_m_per_px or 0.02) * 100.0), 2),
            "trunk_lean_deg_at_impact_proxy": round(float(metrics.get("trunk_lean_deg", 0.0) or 0.0), 2),
            "move_ratio_proxy": round(float(move_ratio), 3),
        }

    if mapped_rule_key == "short_pass":
        time_debug = _video_pass_receive_time_debug(run_data, event_times)
        pass_execution_time_s = dict(time_debug.get("pass_execution_time_s") or {})
        receive_stabilization_time_s = dict(time_debug.get("receive_stabilization_time_s") or {})
        pass_receive_gap_s = dict(time_debug.get("pass_receive_gap_s") or {})
        endpoint_error_m = max(0.0, min(1.8, support_ball_ratio * 1.6 + (0.16 if ball_contact < 0.5 else 0.0) + (0.10 if stability < 0.58 else 0.0)))
        receive_control_zone_success_rate = _clamp(
            0.40 * ball_contact
            + 0.24 * sequence_confidence
            + 0.24 * stability
            + 0.12 * (1.0 if support_ball_ratio <= 0.38 else max(0.0, 1.0 - support_ball_ratio))
        )
        receive_corrective_touch_count = float(
            max(
                0,
                int(round((1.0 - receive_control_zone_success_rate) * 3.0 + (0 if ball_confidence >= 0.5 else 1))),
            )
        )
        pass_execution_time_value = pass_execution_time_s.get("value")
        receive_stabilization_time_value = receive_stabilization_time_s.get("value")
        pass_receive_gap_value = pass_receive_gap_s.get("value")
        stabilization_factor = 0.35
        if receive_stabilization_time_value is not None:
            stabilization_factor = 1.0 - min(1.0, float(receive_stabilization_time_value) / max(1.0, duration_s or 1.0))
        sequence_continuity_score = _clamp(
            0.34 * stability
            + 0.24 * sequence_confidence
            + 0.22 * receive_control_zone_success_rate
            + 0.20 * (1.0 - min(1.0, endpoint_error_m / 1.2))
        )
        next_action_readiness = _clamp(
            0.34 * receive_control_zone_success_rate
            + 0.28 * sequence_continuity_score
            + 0.20 * stabilization_factor
            + 0.18 * ball_confidence
        )

        def _lower_band(value: Optional[float], excellent_max: float, good_max: float, poor_over: float) -> str:
            if value is None:
                return "reference"
            numeric = float(value)
            if numeric <= excellent_max:
                return "excellent"
            if numeric <= good_max:
                return "good"
            if numeric > poor_over:
                return "needs_work"
            return "needs_work"

        def _higher_band(value: Optional[float], excellent_min: float, good_min: float, needs_work_below: float) -> str:
            if value is None:
                return "reference"
            numeric = float(value)
            if numeric >= excellent_min:
                return "excellent"
            if numeric >= good_min:
                return "good"
            if numeric < needs_work_below:
                return "needs_work"
            return "needs_work"

        def _metric_object(value: Optional[float], band: str, confidence: float, low_confidence: bool = False) -> Dict[str, Any]:
            return {
                "value": None if value is None else round(float(value), 3),
                "band": band,
                "confidence": round(float(confidence), 3),
                "low_confidence": bool(low_confidence),
                "source": "short_pass_temporal_features",
            }

        penalty_events = 0
        penalty_events += 1 if ball_contact < 0.5 else 0
        penalty_events += 1 if stability < 0.58 else 0
        penalty_events += 1 if sequence_confidence < 0.40 else 0
        return {
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "endpoint_error_m": round(float(endpoint_error_m), 3),
            "execution_time_s": round(float(pass_execution_time_value if pass_execution_time_value is not None else duration_s), 3),
            "penalty_events": float(penalty_events),
            "plant_foot_orientation_deg": round(float(12.0 + support_ball_ratio * 22.0), 2),
            "body_open_angle_deg_before_pass": round(float(18.0 + visibility * 35.0), 2),
            "pass_endpoint_error_m": _metric_object(
                endpoint_error_m,
                _lower_band(endpoint_error_m, excellent_max=0.25, good_max=0.50, poor_over=1.00),
                confidence=max(0.55, min(0.92, 0.40 * ball_confidence + 0.32 * stability + 0.28 * max(ball_contact, 0.2))),
                low_confidence=ball_confidence < 0.35,
            ),
            "pass_execution_time_s": {
                **pass_execution_time_s,
                "band": _lower_band(
                    None if pass_execution_time_value is None else float(pass_execution_time_value),
                    excellent_max=1.8,
                    good_max=2.8,
                    poor_over=4.0,
                ),
                "source": "short_pass_temporal_features",
            },
            "receive_control_zone_success_rate": _metric_object(
                receive_control_zone_success_rate,
                _higher_band(receive_control_zone_success_rate, excellent_min=0.82, good_min=0.65, needs_work_below=0.45),
                confidence=max(0.55, min(0.90, 0.45 * ball_confidence + 0.30 * stability + 0.25 * sequence_confidence)),
                low_confidence=ball_confidence < 0.35 and sequence_confidence < 0.35,
            ),
            "receive_stabilization_time_s": {
                **receive_stabilization_time_s,
                "band": _lower_band(
                    None if receive_stabilization_time_value is None else float(receive_stabilization_time_value),
                    excellent_max=0.9,
                    good_max=1.3,
                    poor_over=1.8,
                ),
                "source": "short_pass_temporal_features",
            },
            "receive_corrective_touch_count": _metric_object(
                receive_corrective_touch_count,
                _lower_band(receive_corrective_touch_count, excellent_max=0, good_max=1, poor_over=2),
                confidence=max(0.52, min(0.88, 0.38 * ball_confidence + 0.32 * stability + 0.30 * sequence_confidence)),
                low_confidence=ball_confidence < 0.35,
            ),
            "sequence_continuity_score": _metric_object(
                sequence_continuity_score,
                _higher_band(sequence_continuity_score, excellent_min=0.78, good_min=0.60, needs_work_below=0.40),
                confidence=max(0.54, min(0.90, 0.42 * sequence_confidence + 0.34 * stability + 0.24 * ball_confidence)),
                low_confidence=sequence_confidence < 0.35,
            ),
            "next_action_readiness": _metric_object(
                next_action_readiness,
                _higher_band(next_action_readiness, excellent_min=0.75, good_min=0.55, needs_work_below=0.35),
                confidence=max(0.50, min(0.86, 0.38 * sequence_confidence + 0.34 * ball_confidence + 0.28 * stability)),
                low_confidence=sequence_confidence < 0.35 and ball_confidence < 0.45,
            ),
            "pass_receive_gap_s": {
                **pass_receive_gap_s,
                "band": _lower_band(
                    None if pass_receive_gap_value is None else float(pass_receive_gap_value),
                    excellent_max=0.35,
                    good_max=0.75,
                    poor_over=1.25,
                ),
                "source": "short_pass_temporal_features",
            },
            "metric_debug": dict(time_debug.get("metric_debug") or {}),
        }

    if mapped_rule_key == "pass_receive_sequence":
        time_debug = _video_pass_receive_time_debug(run_data, event_times)
        pass_execution_time_s = dict(time_debug.get("pass_execution_time_s") or {})
        receive_stabilization_time_s = dict(time_debug.get("receive_stabilization_time_s") or {})
        pass_receive_gap_s = dict(time_debug.get("pass_receive_gap_s") or {})
        pass_endpoint_error_m = max(
            0.0,
            min(
                1.6,
                support_ball_ratio * 1.45
                + (0.12 if ball_contact < 0.5 else 0.0)
                + (0.08 if stability < 0.58 else 0.0),
            ),
        )
        receive_control_zone_success_rate = _clamp(
            0.36 * ball_contact
            + 0.30 * sequence_confidence
            + 0.22 * stability
            + 0.12 * (1.0 if move_ratio < 0.02 else 0.0)
        )
        receive_corrective_touch_count = float(
            max(
                0,
                int(round((1.0 - receive_control_zone_success_rate) * 3.0 + (0 if ball_confidence >= 0.5 else 1))),
            )
        )
        receive_stabilization_time_value = receive_stabilization_time_s.get("value")
        pass_execution_time_value = pass_execution_time_s.get("value")
        pass_receive_gap_value = pass_receive_gap_s.get("value")
        receive_stabilization_confidence = float(receive_stabilization_time_s.get("confidence", 0.0) or 0.0)
        pass_execution_confidence = float(pass_execution_time_s.get("confidence", 0.0) or 0.0)
        pass_receive_gap_confidence = float(pass_receive_gap_s.get("confidence", 0.0) or 0.0)
        stabilization_factor = 0.35
        if receive_stabilization_time_value is not None and receive_stabilization_confidence >= 0.6:
            stabilization_factor = 1.0 - min(1.0, float(receive_stabilization_time_value) / max(1.0, duration_s or 1.0))
        sequence_continuity_score = _clamp(
            0.34 * stability
            + 0.28 * sequence_confidence
            + 0.20 * receive_control_zone_success_rate
            + 0.18 * (1.0 - min(1.0, pass_endpoint_error_m / 1.2))
        )
        next_action_readiness = _clamp(
            0.32 * receive_control_zone_success_rate
            + 0.28 * sequence_continuity_score
            + 0.20 * stabilization_factor
            + 0.20 * ball_confidence
        )
        return {
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "pass_endpoint_error_m": round(float(pass_endpoint_error_m), 3),
            "pass_execution_time_s": pass_execution_time_s,
            "receive_control_zone_success_rate": round(float(receive_control_zone_success_rate), 3),
            "receive_stabilization_time_s": receive_stabilization_time_s,
            "receive_corrective_touch_count": receive_corrective_touch_count,
            "sequence_continuity_score": round(float(sequence_continuity_score), 3),
            "next_action_readiness": round(float(next_action_readiness), 3),
            "pass_receive_gap_s": pass_receive_gap_s,
            "support_ball_ratio": round(float(support_ball_ratio), 3),
            "stability": round(float(stability), 3),
            "sequence_confidence": round(float(sequence_confidence), 3),
            "metric_debug": dict(time_debug.get("metric_debug") or {}),
        }

    if mapped_rule_key == "receive_control":
        control_zone_success_rate = _clamp(0.46 * ball_contact + 0.30 * sequence_confidence + 0.24 * stability)
        stabilization_time_s = max(0.0, duration_s)
        corrective_touch_count = float(max(0, int(round((1.0 - control_zone_success_rate) * 3.0 + (0 if ball_confidence >= 0.5 else 1)))))
        lateral_offset_m = max(0.0, min(1.2, support_ball_ratio * body_span_px * (scale_m_per_px or 0.02)))
        return {
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "control_zone_success_rate": round(float(control_zone_success_rate), 3),
            "stabilization_time_s": round(float(stabilization_time_s), 3),
            "corrective_touch_count": corrective_touch_count,
            "lateral_offset_m": round(float(lateral_offset_m), 3),
            "body_open_angle_deg": round(float(16.0 + visibility * 32.0), 2),
            "recenter_time_s": round(float(max(0.0, duration_s * 0.65)), 3),
        }

    if mapped_rule_key == "dribble_change_direction":
        completion_time_s = max(0.0, duration_s)
        cone_hit_count = float(max(0, int(round((1.0 - stability) * 2.0))))
        out_of_lane_count = float(max(0, int(round((1.0 - sequence_confidence) * 2.0))))
        control_loss_count = float(max(0, int(round((1.0 - ball_confidence) * 2.0))))
        return {
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "completion_time_s": round(float(completion_time_s), 3),
            "cone_hit_count": cone_hit_count,
            "out_of_lane_count": out_of_lane_count,
            "control_loss_count": control_loss_count,
            "mean_touches_per_meter": round(float(max(0.0, 1.0 + stability * 2.4)), 3),
            "max_ball_body_separation_m": round(float(max(0.0, support_ball_ratio * body_span_px * (scale_m_per_px or 0.02))), 3),
        }

    if mapped_rule_key == "juggling":
        dominant = max(0, int(round(float(run_data.get("ball_frames", 0) or 0) / max(1.0, duration_s * fps * 0.35))))
        freestyle = max(0, dominant - 1)
        drop_count = float(max(0, int(round((1.0 - stability) * 3.0 + (0 if ball_confidence >= 0.5 else 1)))))
        return {
            "ball_speed_measurement_type": measurement_mode,
            "body_span_px": round(float(body_span_px), 2),
            "consecutive_touches_dominant_foot": float(dominant),
            "consecutive_touches_freestyle": float(freestyle),
            "drop_count": drop_count,
            "non_dominant_foot_juggling": float(max(0, dominant - 2)),
            "complex_sequence_juggling": float(max(0, dominant - 3)),
        }

    return {
        "ball_speed_measurement_type": measurement_mode,
        "body_span_px": round(float(body_span_px), 2),
        "endpoint_error_m": round(float(max(0.0, support_ball_ratio * 1.6)), 3),
        "execution_time_s": round(float(duration_s), 3),
        "penalty_events": float(0 if ball_contact > 0.0 else 1),
    }


def _video_summary_primary_issue(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_id = str(issue.get("id") or "")
        if issue_id in {"stable_action", "action_pattern_unclear"}:
            continue
        return issue
    return issues[0] if issues else {}


def _video_action_display_name(action_name: str) -> str:
    lower = str(action_name or "").lower()
    if lower in {"uncertain", "pending_confirmation", "needs_confirmation", "review_required"}:
        return "动作待确认"
    if "pass_receive_sequence" in lower or "sequence" in lower:
        return "传接球"
    if "pass" in lower or "short_pass" in lower or "pass_like" in lower:
        return "传球"
    if "shot" in lower or "shoot" in lower or "shoot_like" in lower:
        return "射门"
    if "first_touch" in lower or "receive_control" in lower or lower == "receive" or "touch" in lower:
        return "停球"
    if "clearance" in lower:
        return "解围"
    if "long_ball" in lower:
        return "长传"
    return action_name or "动作待确认"


def _video_uncertainty_reason_text(reasons: List[str]) -> str:
    mapping = {
        "no_pose": "人体姿态证据不足",
        "target_unstable": "主目标跟踪不稳定",
        "ball_unstable": "球轨迹证据不足",
        "goal_not_visible": "球门上下文不清晰",
        "low_confidence": "动作置信度偏低",
        "confidence_gap_low": "传球与射门候选分差过小",
        "ambiguous_pass_shot": "传球与射门边界模糊",
        "ambiguous_action": "动作候选仍有歧义",
        "short_clip": "视频时长太短",
        "kick_stage_uncertain": "踢球阶段还不够明确",
        "too_many_uncertainty_reasons": "低置信度指标过多",
        "unsupported_action_for_current_analyzer": "当前动作暂未进入正式评分",
        "action_unstable": "当前结果不稳定",
    }
    labels = [mapping.get(reason, reason) for reason in reasons if reason]
    deduped: List[str] = []
    for label in labels:
        if label and label not in deduped:
            deduped.append(label)
    return "、".join(deduped[:3])


def _video_summary_needs_rewrite(
    summary: str,
    action_display_name: str,
    score_block: Dict[str, Any],
    issues: List[Dict[str, Any]],
    *,
    needs_confirmation: bool = False,
) -> bool:
    text = " ".join(str(summary or "").split())
    if not text:
        return True

    if any(phrase in text for phrase in ("当前动作", "最值得继续保持的是当前动作", "继续保持的是当前动作", "当前最值得继续保持")):
        return True
    if needs_confirmation and not any(marker in text for marker in ("待确认", "不确定", "候选")):
        return True

    overall = float(score_block.get("overall", 0.0) or 0.0)
    primary_issue = _video_summary_primary_issue(issues)
    primary_title = str(primary_issue.get("title") or "").strip()
    if overall < 60.0:
        if primary_title in {"动作整体稳定", "动作识别不够明确", "视频证据不足", "视频质量问题", "动作质量"}:
            return True
        if primary_title and primary_title not in text:
            return True
        if not primary_title and "主要问题" not in text:
            return True

    return False


def _rewrite_video_summary(
    action_display_name: str,
    score_block: Dict[str, Any],
    issues: List[Dict[str, Any]],
    evidence: Dict[str, float],
    *,
    fallback_used: bool,
    needs_confirmation: bool = False,
    uncertainty_reasons: Optional[List[str]] = None,
    action_candidates: Optional[List[Dict[str, Any]]] = None,
) -> str:
    overall = float(score_block.get("overall", 0.0) or 0.0)
    primary_issue = _video_summary_primary_issue(issues)
    primary_title = str(primary_issue.get("title") or "动作质量")
    if primary_title in {"动作整体稳定", "动作识别不够明确"}:
        primary_title = "动作完成度"

    if needs_confirmation:
        candidates = []
        for candidate in action_candidates or []:
            if not isinstance(candidate, dict):
                continue
            display_name = str(candidate.get("display_name") or candidate.get("label") or candidate.get("action") or "").strip()
            score = candidate.get("score")
            if display_name:
                if score is None:
                    candidates.append(display_name)
                else:
                    candidates.append(f"{display_name} {float(score):.2f}")
        candidate_text = "、".join([item for item in candidates[:2] if item])
        reason_text = _video_uncertainty_reason_text(list(uncertainty_reasons or []))
        base = "当前动作类型仍待确认，建议补充更清晰角度后再分析。"
        if candidate_text:
            base = f"当前动作类型仍待确认，候选更像 {candidate_text}，建议补充更清晰角度后再分析。"
        if reason_text:
            base = f"{base} 主要不确定原因：{reason_text}。"
        return base

    if overall >= 90.0:
        base = f"本次{action_display_name}得分 {overall:.0f}/100，完成度很高，当前重点是继续稳定{primary_title}。"
    elif overall >= 75.0:
        base = f"本次{action_display_name}得分 {overall:.0f}/100，整体表现良好，仍需优化{primary_title}。"
    elif overall >= 60.0:
        base = f"本次{action_display_name}得分 {overall:.0f}/100，当前主要问题是{primary_title}。"
    elif overall >= 40.0:
        base = f"本次{action_display_name}得分 {overall:.0f}/100，当前主要问题是{primary_title}，建议先把这个环节稳定下来。"
    else:
        base = f"本次{action_display_name}得分 {overall:.0f}/100，当前主要问题是{primary_title}，建议优先重拍或重点纠正。"

    if fallback_used and "保守分析" not in base:
        base = f"当前按推荐模板做保守分析。{base}"
    if float(evidence.get("analysis_confidence", 0.0) or 0.0) < 0.45:
        base += " 当前证据偏少，结论请按保守结果理解。"
    return base


def _video_summary(action_display_name: str, score_block: Dict[str, Any], issues: List[Dict[str, Any]], evidence: Dict[str, float], *, fallback_used: bool) -> str:
    overall = float(score_block.get("overall", 0.0) or 0.0)
    is_sequence = "pass_subscore" in score_block or "receive_subscore" in score_block or "sequence_continuity_score" in score_block
    unsupported_issue = bool(issues and issues[0].get("id") == "unsupported_action_for_current_analyzer")
    needs_confirmation = bool(score_block.get("needs_confirmation", False))
    if unsupported_issue:
        base = f"当前仅接入 short_pass / pass_receive_sequence / receive_control / shot_instep 最小分析器，{action_display_name} 暂未进入正式评分。"
        if len(issues) > 1:
            base += f" 同时还存在{issues[1].get('title', '其他问题')}。"
    elif needs_confirmation:
        base = _rewrite_video_summary(
            action_display_name,
            score_block,
            issues,
            evidence,
            fallback_used=fallback_used,
            needs_confirmation=True,
            uncertainty_reasons=list(score_block.get("uncertainty_reasons") or []),
            action_candidates=list(score_block.get("action_candidates") or []),
        )
    elif is_sequence and not issues:
        pass_score = float(score_block.get("pass_subscore", 0.0) or 0.0)
        receive_score = float(score_block.get("receive_subscore", 0.0) or 0.0)
        continuity_score = float(score_block.get("sequence_continuity_score", 0.0) or 0.0)
        readiness_score = float(score_block.get("next_action_readiness", 0.0) or 0.0)
        base = (
            f"{action_display_name} 序列得分 {overall:.0f}/100，"
            f"传球段 {pass_score:.0f}/100，接球段 {receive_score:.0f}/100，"
            f"衔接 {continuity_score:.0f}/100，接续准备 {readiness_score:.0f}/100。"
        )
    elif is_sequence and issues and issues[0].get("id") == "action_pattern_unclear":
        base = f"动作识别置信度偏低，当前按 {action_display_name} 序列模板做保守分析。"
        if len(issues) > 1:
            base += f"{action_display_name} 序列得分 {overall:.0f}/100，主要问题是{issues[1].get('title', '动作质量')}。"
        else:
            base += f"{action_display_name} 序列得分 {overall:.0f}/100。"
    elif not issues:
        base = f"本次{action_display_name}整体得分 {overall:.0f}/100，当前没有看到特别突出的关键失误。"
    elif issues[0].get("id") == "action_pattern_unclear":
        base = f"动作识别置信度偏低，当前按 {action_display_name} 模板做保守分析。"
        if len(issues) > 1:
            base += f"本次{action_display_name}得分 {overall:.0f}/100，主要问题是{issues[1].get('title', '动作质量')}。"
        else:
            base += f"本次{action_display_name}得分 {overall:.0f}/100。"
    else:
        primary = issues[0]
        base = f"本次{action_display_name}得分 {overall:.0f}/100，主要问题是{primary.get('title', '动作质量')}"
        if len(issues) > 1 and issues[1].get("id") != "action_pattern_unclear":
            base += f"，其次是{issues[1].get('title', '其他问题')}"
        base += "。"
    if _video_summary_needs_rewrite(base, action_display_name, score_block, issues, needs_confirmation=needs_confirmation):
        base = _rewrite_video_summary(
            action_display_name,
            score_block,
            issues,
            evidence,
            fallback_used=fallback_used,
            needs_confirmation=needs_confirmation,
            uncertainty_reasons=list(score_block.get("uncertainty_reasons") or []),
            action_candidates=list(score_block.get("action_candidates") or []),
        )
    elif fallback_used and not unsupported_issue:
        base = f"当前按推荐模板做保守分析。{base}"
        if float(evidence.get("analysis_confidence", 0.0) or 0.0) < 0.45:
            base = f"{base} 当前证据偏少，结论请按保守结果理解。"
    elif float(evidence.get("analysis_confidence", 0.0) or 0.0) < 0.45:
        base = f"{base} 当前证据偏少，结论请按保守结果理解。"
    return base


def _video_result_family(value: Any) -> str:
    lower = str(value or "").strip().lower()
    if not lower:
        return "unknown"
    if "result_inconsistent" in lower:
        return "result_inconsistent"
    if "review_required" in lower or "动作待确认" in lower:
        return "review_required"
    if lower in {"uncertain", "pending_confirmation", "needs_confirmation"} or "待确认" in lower:
        return "uncertain"
    if "pass_receive_sequence" in lower or "sequence" in lower or "传接球" in lower:
        return "pass_receive_sequence"
    if "shot_instep" in lower or "shoot_like" in lower or "shot_like" in lower or "shoot" in lower or "shot" in lower or "射门" in lower:
        return "shot"
    if "receive_control" in lower or "first_touch" in lower or lower == "receive" or "touch" in lower or "停球" in lower or "接球" in lower:
        return "receive"
    if "clearance" in lower or "解围" in lower:
        return "clearance"
    if "long_ball" in lower or "长传" in lower:
        return "long_ball"
    if "short_pass" in lower or lower == "pass" or "pass_like" in lower or "传球" in lower:
        return "pass"
    if "non_kick" in lower or "idle" in lower:
        return "non_kick"
    return "unknown"


def _video_result_family_matches(source_family: str, observed_family: str) -> bool:
    source_family = str(source_family or "unknown")
    observed_family = str(observed_family or "unknown")
    compatibility = {
        "pass": {"pass", "pass_receive_sequence", "long_ball"},
        "pass_receive_sequence": {"pass_receive_sequence", "pass", "receive", "long_ball"},
        "shot": {"shot", "clearance"},
        "receive": {"receive", "pass", "pass_receive_sequence"},
        "clearance": {"clearance", "shot"},
        "long_ball": {"long_ball", "pass", "sequence"},
        "non_kick": {"non_kick", "uncertain", "review_required"},
        "uncertain": {"uncertain", "review_required", "non_kick"},
        "review_required": {"review_required", "uncertain", "non_kick"},
    }
    allowed = compatibility.get(source_family)
    if allowed is None:
        return observed_family != "unknown"
    return observed_family in allowed


def _video_result_summary_issue(summary: str, action_family: str, action_display_name: str) -> str:
    text = " ".join(str(summary or "").split())
    if not text:
        return "summary_missing"

    lower = text.lower()
    if any(phrase in text for phrase in ("当前动作", "最值得继续保持的是当前动作", "继续保持的是当前动作", "当前最值得继续保持")):
        return "summary_self_reference"

    display_name = str(action_display_name or "").strip()
    if action_family in {"pass", "pass_receive_sequence"}:
        if "射门" in text or "shot" in lower or "shoot" in lower:
            return "summary_shot_conflict"
        if display_name and display_name not in text and not any(marker in text for marker in ("传球", "传接球", "长传", "pass", "sequence")):
            return "summary_action_binding_missing"
    elif action_family == "shot":
        if "传球" in text or "传接球" in text or "长传" in text or "pass" in lower or "停球" in text or "接球" in text:
            return "summary_pass_conflict"
        if display_name and display_name not in text and not any(marker in text for marker in ("射门", "shot", "shoot")):
            return "summary_action_binding_missing"
    elif action_family == "receive":
        if "射门" in text or "shot" in lower or "shoot" in lower:
            return "summary_shot_conflict"
        if "传球" in text or "传接球" in text or "pass" in lower:
            return "summary_pass_conflict"
        if display_name and display_name not in text and not any(marker in text for marker in ("停球", "接球", "touch")):
            return "summary_action_binding_missing"
    elif action_family in {"uncertain", "review_required"}:
        if not any(marker in text for marker in ("待确认", "不确定", "候选", "参考")):
            return "summary_uncertain_missing"
    else:
        if display_name and display_name not in text:
            return "summary_action_binding_missing"

    return ""


def _video_result_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    score = dict(payload.get("score") or {})
    return {
        "action_name": str(payload.get("action_name") or ""),
        "action_display_name": str(payload.get("action_display_name") or ""),
        "detected_action": str(payload.get("detected_action") or ""),
        "recommended_template": str(payload.get("recommended_template") or ""),
        "score.overall": _video_coerce_numeric(score.get("overall")),
        "score.level_code": str(score.get("level_code") or ""),
        "score.level_label": str(score.get("level_label") or ""),
        "overall_score": _video_coerce_numeric(payload.get("overall_score", score.get("overall"))),
        "summary": str(payload.get("summary") or ""),
        "needs_confirmation": bool(payload.get("needs_confirmation", False)),
    }


def _video_result_final_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    score = dict(payload.get("score") or {})
    return {
        "final_action_name": str(payload.get("action_name") or ""),
        "final_action_display_name": str(payload.get("action_display_name") or ""),
        "final_detected_action": str(payload.get("detected_action") or ""),
        "final_recommended_template": str(payload.get("recommended_template") or ""),
        "final_overall_score": _video_coerce_numeric(payload.get("overall_score", score.get("overall"))),
        "final_level_code": str(score.get("level_code") or ""),
        "final_level_label": str(score.get("level_label") or ""),
        "final_summary": str(payload.get("summary") or ""),
        "final_status": str(payload.get("status") or ""),
        "final_error_code": str(payload.get("error_code") or ""),
        "anomaly_reason": str(payload.get("anomaly_reason") or ""),
    }


def _video_result_inconsistent_fields(reasons: List[str]) -> List[str]:
    mapping = {
        "overall_score_mismatch": ["overall_score", "score.overall"],
        "score_level_mismatch": ["overall_score", "score.overall", "score.level_code", "score.level_label"],
        "needs_confirmation": ["needs_confirmation", "confidence", "confidence_gap"],
        "low_confidence": ["confidence"],
        "action_name_missing": ["action_name"],
        "detected_action_missing": ["detected_action"],
        "recommended_template_missing": ["recommended_template"],
        "action_display_name_missing": ["action_display_name"],
        "action_family_unknown": ["action_name", "detected_action", "recommended_template", "action_display_name"],
        "action_name_family_unknown": ["action_name", "detected_action", "recommended_template", "action_display_name"],
        "action_family_not_final": ["action_name", "detected_action", "recommended_template", "action_display_name"],
        "detected_action_conflict": ["detected_action"],
        "recommended_template_conflict": ["recommended_template"],
        "action_display_name_conflict": ["action_display_name"],
        "summary_missing": ["summary"],
        "summary_self_reference": ["summary"],
        "summary_shot_conflict": ["summary", "action_name", "action_display_name"],
        "summary_pass_conflict": ["summary", "action_name", "action_display_name"],
        "summary_action_binding_missing": ["summary", "action_name", "action_display_name"],
        "summary_uncertain_missing": ["summary", "action_name", "detected_action"],
        "route_mismatch": ["selected_action", "routed_analyzer", "analysis_routed_by", "action_name", "detected_action"],
    }
    inconsistent_fields: List[str] = []
    for reason in reasons:
        key = reason.split(":", 1)[0]
        inconsistent_fields.extend(mapping.get(key, []))
    return list(dict.fromkeys(inconsistent_fields))


def _video_result_consistency_reasons(payload: Dict[str, Any]) -> List[str]:
    status = str(payload.get("status") or "").lower()
    if status not in {"ok", "provisional"}:
        return []

    reasons: List[str] = []
    manual_routed = str(payload.get("analysis_routed_by") or "").strip().lower() == "user_selected"
    score = dict(payload.get("score") or {})
    overall_score = round(float(payload.get("overall_score", score.get("overall", 0.0)) or 0.0), 1)
    score_overall = round(float(score.get("overall", 0.0) or 0.0), 1)
    if score_overall != overall_score:
        reasons.append(f"overall_score_mismatch:{score_overall:.1f}!={overall_score:.1f}")

    expected_level_code, expected_level_label = score_level_from_overall(overall_score)
    actual_level_code = str(score.get("level_code") or "")
    actual_level_label = str(score.get("level_label") or "")
    if actual_level_code != expected_level_code or actual_level_label != expected_level_label:
        reasons.append(
            "score_level_mismatch:"
            f"{actual_level_code or '<empty>'}/{actual_level_label or '<empty>'}"
            f"!= {expected_level_code}/{expected_level_label}"
        )

    if not manual_routed and (bool(payload.get("needs_confirmation", False)) or bool(score.get("needs_confirmation", False))):
        reasons.append("needs_confirmation")

    confidence = float(payload.get("confidence", score.get("confidence", 0.0)) or 0.0)
    if not manual_routed and confidence < 0.60:
        reasons.append(f"low_confidence:{confidence:.3f}")

    action_name = str(payload.get("action_name") or "").strip()
    detected_action = str(payload.get("detected_action") or "").strip()
    recommended_template = str(payload.get("recommended_template") or "").strip()
    action_display_name = str(payload.get("action_display_name") or "").strip()
    selected_action = str(payload.get("selected_action") or "").strip()
    routed_analyzer = str(payload.get("routed_analyzer") or "").strip()
    summary = str(payload.get("summary") or "")

    if not action_name:
        reasons.append("action_name_missing")
    if not detected_action:
        reasons.append("detected_action_missing")
    if not recommended_template:
        reasons.append("recommended_template_missing")
    if not action_display_name:
        reasons.append("action_display_name_missing")
    if selected_action and routed_analyzer:
        selected_family = _video_main_action_class(selected_action)
        routed_family = _video_main_action_class(routed_analyzer)
        if selected_family not in {"unknown", "review_required"} and routed_family not in {"unknown", "review_required"} and selected_family != routed_family:
            reasons.append(f"route_mismatch:{selected_action}->{routed_analyzer}")

    primary_family = _video_result_family(action_name)
    if primary_family in {"unknown", "result_inconsistent"}:
        fallback_family = next(
            (
                family
                for family in (
                    _video_result_family(recommended_template),
                    _video_result_family(detected_action),
                    _video_result_family(action_display_name),
                )
                if family not in {"unknown", "result_inconsistent"}
            ),
            "unknown",
        )
        if fallback_family == "unknown":
            reasons.append(f"action_family_unknown:{action_name or '<empty>'}")
        else:
            reasons.append(f"action_name_family_unknown:{action_name or '<empty>'}")
            primary_family = fallback_family

    if primary_family in {"uncertain", "non_kick", "unknown", "result_inconsistent"}:
        reasons.append(f"action_family_not_final:{primary_family}")

    detected_family = _video_result_family(detected_action)
    template_family = _video_result_family(recommended_template)
    display_family = _video_result_family(action_display_name)
    if not _video_result_family_matches(primary_family, detected_family):
        reasons.append(f"detected_action_conflict:{detected_action}")
    if not _video_result_family_matches(primary_family, template_family):
        reasons.append(f"recommended_template_conflict:{recommended_template}")
    if not _video_result_family_matches(primary_family, display_family):
        reasons.append(f"action_display_name_conflict:{action_display_name}")

    summary_issue = _video_result_summary_issue(summary, primary_family, action_display_name)
    if summary_issue:
        reasons.append(summary_issue)

    return list(dict.fromkeys(reasons))


def _build_result_inconsistent_payload(
    video_path: Path,
    *,
    analyzer_used: str,
    payload: Dict[str, Any],
    reasons: List[str],
) -> Dict[str, Any]:
    message = "分析结果一致性校验失败，系统已拦截本次异常结果。"
    recommended_template = "result_inconsistent"
    anomaly_payload = _build_generic_error_payload(
        video_path,
        error_code="result_inconsistent",
        message=message,
        analyzer_used=analyzer_used,
        recommended_template=recommended_template,
    )

    analysis_snapshot = _video_result_snapshot(payload)
    final_debug_snapshot = _video_result_final_snapshot(payload)
    anomaly_reason = "；".join(reasons[:4]) if reasons else "result_inconsistent"
    anomaly_payload.update(
        {
            "result_kind": "anomaly",
            "anomaly_reason": anomaly_reason,
            "anomaly_reasons": list(reasons),
            "inconsistent_fields": _video_result_inconsistent_fields(reasons),
            "analysis_snapshot": analysis_snapshot,
            "final_debug_snapshot": final_debug_snapshot,
            "score": {
                "overall": 0.0,
                "technical_execution": 0.0,
                "control_stability": 0.0,
                "action_safety": 0.0,
                "level_code": "pending_confirmation",
                "level_label": "待确认",
                "source": "result_inconsistent_anomaly",
                "measurement_mode": str(payload.get("ball_speed_measurement_type") or "proxy"),
                "action_label": "uncertain",
                "action_display_name": "待确认",
                "needs_confirmation": False,
                "confidence": 0.0,
                "confidence_gap": 0.0,
                "uncertainty_reasons": list(reasons),
            },
            "overall_score": 0.0,
            "summary": message,
            "scoring_state": "result_inconsistent",
            "status": "error",
            "score_ready": False,
            "action_label": "uncertain",
            "action_display_name": "待确认",
            "detected_action": "uncertain",
            "final_detected_action": "uncertain",
            "action_name": recommended_template,
            "resolved_action_name": recommended_template,
            "mapped_rule_key": recommended_template,
            "recommended_template": recommended_template,
            "final_mapped_rule_key": recommended_template,
            "needs_confirmation": False,
            "uncertainty_reasons": list(reasons),
            "fallback_used": True,
            "whether_fallback_template_used": True,
            "warnings": list(dict.fromkeys(list(anomaly_payload.get("warnings") or []) + list(reasons) + ["result_inconsistent"])),
        }
    )
    return anomaly_payload


def _video_debug_print_result_fields(payload: Dict[str, Any]) -> None:
    score = dict(payload.get("score") or {})
    fields = {
        "final_action_name": str(payload.get("action_name") or ""),
        "final_action_display_name": str(payload.get("action_display_name") or ""),
        "final_detected_action": str(payload.get("detected_action") or ""),
        "final_recommended_template": str(payload.get("recommended_template") or ""),
        "final_overall_score": _video_coerce_numeric(payload.get("overall_score", score.get("overall"))),
        "final_level_label": str(score.get("level_label") or ""),
        "final_summary": str(payload.get("summary") or ""),
        "final_routed_analyzer": str(payload.get("routed_analyzer") or payload.get("analyzer_used") or ""),
        "selected_action": str(payload.get("selected_action") or ""),
        "analysis_template": str(payload.get("analysis_template") or ""),
        "analysis_routed_by": str(payload.get("analysis_routed_by") or ""),
        "system_action_suggestion": str(payload.get("system_action_suggestion") or ""),
        "suggested_action": str(payload.get("suggested_action") or ""),
        "suggestion_reason": str(payload.get("suggestion_reason") or ""),
        "fallback_used": bool(payload.get("fallback_used", False)),
        "fallback_reason": str(payload.get("fallback_reason") or ""),
        "action_name": str(payload.get("action_name") or ""),
        "action_display_name": str(payload.get("action_display_name") or ""),
        "detected_action": str(payload.get("detected_action") or ""),
        "recommended_template": str(payload.get("recommended_template") or ""),
        "score.overall": _video_coerce_numeric(score.get("overall")),
        "score.level_code": str(score.get("level_code") or ""),
        "score.level_label": str(score.get("level_label") or ""),
        "overall_score": _video_coerce_numeric(payload.get("overall_score", score.get("overall"))),
        "summary": str(payload.get("summary") or ""),
        "error_code": str(payload.get("error_code") or ""),
        "anomaly_reason": str(payload.get("anomaly_reason") or ""),
        "inconsistent_fields": list(payload.get("inconsistent_fields") or []),
        "analysis_status": str(payload.get("analysis_status") or ""),
        "failure_reason": str(payload.get("failure_reason") or ""),
        "integrity_state": str(payload.get("integrity_state") or ""),
        "video_duration_s": _video_coerce_numeric(payload.get("video_duration_s", payload.get("duration_s"))),
        "frame_count": int(payload.get("frame_count") or 0),
        "sampled_frame_count": int(payload.get("sampled_frame_count") or 0),
        "fast_mode_enabled": bool(payload.get("fast_mode_enabled", False)),
        "long_video_localized": bool(payload.get("long_video_localized", False)),
        "candidate_window_count": int(payload.get("candidate_window_count") or 0),
        "selected_window_index": payload.get("selected_window_index"),
        "selected_window_start_s": _video_coerce_numeric(payload.get("selected_window_start_s")),
        "selected_window_end_s": _video_coerce_numeric(payload.get("selected_window_end_s")),
        "selected_window_duration_s": _video_coerce_numeric(payload.get("selected_window_duration_s")),
        "selected_window": payload.get("selected_window"),
        "candidate_windows": list(payload.get("candidate_windows") or []),
        "warnings": list(payload.get("warnings") or []),
    }
    print(f"KICK_BACKEND_ANALYZER_RESULT_DEBUG = {json.dumps(fields, ensure_ascii=False, sort_keys=True)}", flush=True)
    summary_log = {
        "selected_action": str(payload.get("selected_action") or ""),
        "analysis_routed_by": str(payload.get("analysis_routed_by") or ""),
        "routed_analyzer": str(payload.get("routed_analyzer") or payload.get("analyzer_used") or ""),
        "video_duration": _video_coerce_numeric(payload.get("video_duration_s", payload.get("duration_s"))),
        "candidate_window_count": int(payload.get("candidate_window_count") or 0),
        "selected_window_index": payload.get("selected_window_index"),
        "selected_window": payload.get("selected_window"),
        "failure_reason": str(payload.get("failure_reason") or ""),
        "warnings": list(payload.get("warnings") or []),
    }
    if str(payload.get("analysis_status") or "").lower() == "failed" or summary_log["failure_reason"]:
        print(f"KICK_ANALYSIS_FAILURE = {json.dumps(summary_log, ensure_ascii=False, sort_keys=True)}", flush=True)
    else:
        print(f"KICK_ANALYSIS_RESULT = {json.dumps(summary_log, ensure_ascii=False, sort_keys=True)}", flush=True)


def _video_result_candidate_gap(payload: Dict[str, Any]) -> Optional[float]:
    candidate_scores = dict(payload.get("candidate_scores") or {})
    candidates: List[Tuple[str, float]] = []

    if candidate_scores:
        for candidate_name, score_value in candidate_scores.items():
            main_action = _video_main_action_class(candidate_name)
            if main_action in {"pass", "shot", "receive", "pass_receive_sequence"}:
                try:
                    candidates.append((main_action, round(float(score_value), 3)))
                except Exception:
                    continue
    else:
        for candidate in payload.get("action_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            candidate_name = candidate.get("action") or candidate.get("label") or candidate.get("template") or candidate.get("display_name")
            main_action = _video_main_action_class(candidate_name)
            if main_action not in {"pass", "shot", "receive", "pass_receive_sequence"}:
                continue
            try:
                score_value = round(float(candidate.get("score", 0.0) or 0.0), 3)
            except Exception:
                continue
            candidates.append((main_action, score_value))

    if not candidates:
        return None

    deduped: Dict[str, float] = {}
    for main_action, score_value in candidates:
        deduped[main_action] = max(float(deduped.get(main_action, 0.0)), float(score_value))

    ranked = sorted(deduped.items(), key=lambda item: (-float(item[1]), str(item[0])))
    if len(ranked) < 2:
        return None
    return round(float(ranked[0][1] - ranked[1][1]), 3)


def _video_review_required_reasons(payload: Dict[str, Any]) -> List[str]:
    score = dict(payload.get("score") or {})
    confidence = float(payload.get("confidence", score.get("confidence", 0.0)) or 0.0)
    raw_confidence_gap = payload.get("confidence_gap", score.get("confidence_gap"))
    confidence_gap = None
    if raw_confidence_gap is not None:
        try:
            confidence_gap = round(float(raw_confidence_gap), 3)
        except Exception:
            confidence_gap = None
    main_action = _video_main_action_from_payload(payload)
    uncertainty_reasons = [
        str(reason).strip()
        for reason in (payload.get("uncertainty_reasons") or score.get("uncertainty_reasons") or [])
        if str(reason).strip()
    ]
    if str(payload.get("analysis_routed_by") or "").strip().lower() == "user_selected":
        return []
    candidate_gap = _video_result_candidate_gap(payload)

    reasons: List[str] = []
    if main_action in {"unknown", "review_required"}:
        reasons.append("action_unstable")
    if bool(payload.get("needs_confirmation", False)) or bool(score.get("needs_confirmation", False)):
        reasons.append("needs_confirmation")
    if confidence < 0.60:
        reasons.append("low_confidence")

    serious_reasons = [reason for reason in uncertainty_reasons if reason in {"no_pose", "target_unstable", "ball_unstable", "goal_not_visible", "ambiguous_pass_shot", "short_clip"}]
    reasons.extend(serious_reasons[:2])

    if "kick_stage_uncertain" in uncertainty_reasons and (
        confidence < 0.75
        or (confidence_gap is not None and confidence_gap < 0.20)
        or (candidate_gap is not None and candidate_gap < 0.20)
    ):
        reasons.append("kick_stage_uncertain")

    if bool(payload.get("unsupported_action_for_current_analyzer", False)):
        reasons.append("unsupported_action_for_current_analyzer")

    # Only treat a small gap as a confirmation problem when we are actually
    # choosing between pass and shot. Missing gap information should not force
    # a fallback on otherwise stable receive / sequence results.
    if main_action in {"pass", "shot"} and not bool(payload.get("sequence_upgrade_applied", False)):
        if confidence >= 0.85:
            confidence_gap = None
            candidate_gap = None
        if confidence_gap is not None and confidence_gap < 0.15:
            reasons.append("confidence_gap_low")
        elif candidate_gap is not None and candidate_gap < 0.15:
            reasons.append("confidence_gap_low")

    if len([reason for reason in reasons if reason in {"low_confidence", "confidence_gap_low", "no_pose", "target_unstable", "ball_unstable", "goal_not_visible", "ambiguous_pass_shot", "short_clip", "kick_stage_uncertain"}]) >= 2:
        reasons.append("too_many_uncertainty_reasons")

    return list(dict.fromkeys(reasons))


def _build_review_required_payload(
    video_path: Path,
    *,
    analyzer_used: str,
    payload: Dict[str, Any],
    reasons: List[str],
) -> Dict[str, Any]:
    base_payload = dict(payload)
    score = dict(base_payload.get("score") or {})
    confidence = float(base_payload.get("confidence", score.get("confidence", 0.0)) or 0.0)
    confidence_gap = float(base_payload.get("confidence_gap", score.get("confidence_gap", 0.0)) or 0.0)
    generated_at = str(base_payload.get("generated_at") or _now_iso())
    fallback_reason = _video_uncertainty_reason_text(list(reasons)) or "本次结果先作为参考，建议换更标准机位重拍"
    feedback_messages = [
        "本次结果先作为参考，建议换更标准机位重拍。",
        "请补充更稳定的机位，并确保全身、球和触球瞬间都清晰入镜。",
    ]
    if any(reason in {"goal_not_visible", "ball_unstable", "no_pose", "short_clip", "target_unstable"} for reason in reasons):
        feedback_messages = [
            "本次结果先作为参考，建议换更标准机位重拍。",
            "请补充更稳定的机位，并确保全身、球和触球瞬间都清晰入镜。",
        ]

    review_score = {
        "overall": None,
        "technical_execution": None,
        "control_stability": None,
        "action_safety": None,
        "level_code": "pending_confirmation",
        "level_label": "待确认",
        "source": "review_required_fallback",
        "measurement_mode": str(base_payload.get("ball_speed_measurement_type") or score.get("measurement_mode") or "proxy"),
        "action_label": "review_required",
        "action_display_name": "动作待确认",
        "action_candidates": list(base_payload.get("action_candidates") or []),
        "confidence": round(float(confidence), 3),
        "confidence_gap": round(float(confidence_gap), 3),
        "needs_confirmation": True,
        "uncertainty_reasons": list(reasons),
        "reference_only_overall": _video_coerce_numeric(base_payload.get("overall_score", score.get("overall"))),
    }

    review_payload = {
        "analysis_version": base_payload.get("analysis_version", VIDEO_ANALYSIS_VERSION),
        "analysis_mode": base_payload.get("analysis_mode", VIDEO_ANALYSIS_MODE),
        "analyzer_used": analyzer_used,
        "routed_analyzer": str(base_payload.get("routed_analyzer") or base_payload.get("analyzer_used") or "review_required"),
        "input_video_path": str(video_path),
        "video_path": str(base_payload.get("video_path") or video_path),
        "clip_id": str(base_payload.get("clip_id") or _slugify(video_path.stem)),
        "generated_at": generated_at,
        "duration_s": round(float(base_payload.get("duration_s", 0.0) or 0.0), 3),
        "frame_count": int(base_payload.get("frame_count", 0) or 0),
        "action_label": "review_required",
        "action_name": "review_required",
        "resolved_action_name": "review_required",
        "detected_action": "review_required",
        "final_detected_action": "review_required",
        "selected_action": str(base_payload.get("selected_action") or "review_required"),
        "analysis_template": str(base_payload.get("analysis_template") or "review_required"),
        "analysis_routed_by": str(base_payload.get("analysis_routed_by") or "auto_detected"),
        "suggested_action": str(base_payload.get("suggested_action") or ""),
        "suggestion_reason": str(base_payload.get("suggestion_reason") or fallback_reason),
        "system_action_suggestion": str(base_payload.get("system_action_suggestion") or ""),
        "route_mismatch": bool(base_payload.get("route_mismatch", False)),
        "route_mismatch_message": str(base_payload.get("route_mismatch_message") or ""),
        "mapped_rule_key": "review_required",
        "final_mapped_rule_key": "review_required",
        "recommended_template": "review_required",
        "action_display_name": "动作待确认",
        "action_confidence": round(float(confidence), 3),
        "confidence": round(float(confidence), 3),
        "confidence_gap": round(float(confidence_gap), 3),
        "needs_confirmation": True,
        "uncertainty_reasons": list(reasons),
        "fallback_used": True,
        "fallback_reason": fallback_reason,
        "fallback_reasons": list(reasons),
        "whether_fallback_template_used": True,
        "unsupported_action_for_current_analyzer": False,
        "score_source": str(base_payload.get("score_source") or "proxy_rule_metrics"),
        "ball_speed_measurement_type": str(base_payload.get("ball_speed_measurement_type") or score.get("measurement_mode") or "proxy"),
        "raw_detected_action": str(base_payload.get("raw_detected_action") or base_payload.get("detected_action") or "uncertain"),
        "stage1_action_label": str(base_payload.get("stage1_action_label") or "non_kick"),
        "stage1_confidence": round(float(base_payload.get("stage1_confidence", 0.0) or 0.0), 3),
        "raw_action_candidates": list(base_payload.get("raw_action_candidates") or []),
        "candidate_scores": dict(base_payload.get("candidate_scores") or {}),
        "sequence_upgrade_applied": bool(base_payload.get("sequence_upgrade_applied", False)),
        "sequence_upgrade_reason": str(base_payload.get("sequence_upgrade_reason") or ""),
        "sequence_context": dict(base_payload.get("sequence_context") or {}),
        "score": review_score,
        "overall_score": None,
        "summary": "本次结果先作为参考，建议换更标准机位重拍",
        "issues": [
            {
                "id": "review_required",
                "title": "动作待确认",
                "phase": "setup",
                "time": 0.0,
                "short_hint": "请补充更稳定的机位后再分析",
                "explanation": "本次结果先作为参考，建议换更标准机位重拍。",
                "fix_advice": feedback_messages[1],
                "training_advice": feedback_messages[1],
                "severity": 0.55,
            }
        ],
        "phase_scores": dict(base_payload.get("phase_scores") or {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0}),
        "analysis_confidence": round(float(base_payload.get("analysis_confidence", 0.0) or 0.0), 3),
        "score_ready": False,
        "scoring_state": "needs_confirmation",
        "status": "provisional",
        "primary_metrics": list(base_payload.get("primary_metrics") or []),
        "sub_scores": dict(base_payload.get("sub_scores") or {}),
        "triggered_rules": list(base_payload.get("triggered_rules") or []),
        "fail_reasons": list(base_payload.get("fail_reasons") or []),
        "feedback_messages": feedback_messages[:2],
        "error_timestamps": list(base_payload.get("error_timestamps") or []),
        "quality_status": str(base_payload.get("quality_status") or "limited"),
        "quality_gate": dict(base_payload.get("quality_gate") or {}),
        "best_trial": base_payload.get("best_trial"),
        "worst_trial": base_payload.get("worst_trial"),
        "rule_metrics": dict(base_payload.get("rule_metrics") or {}),
        "warnings": list(dict.fromkeys(list(base_payload.get("warnings") or []) + list(reasons) + ["review_required"])),
        "error_code": "",
        "anomaly_reason": "",
        "inconsistent_fields": [],
        "integrity_state": str(base_payload.get("integrity_state") or ("route_mismatch" if base_payload.get("route_mismatch") else "normal")),
    }
    review_payload["score"]["reference_only_overall"] = review_score["reference_only_overall"]
    review_payload["score"]["score_label"] = "review_required"
    review_payload["score"]["reference_only"] = True
    review_payload["score"]["reference_only_summary"] = review_payload["summary"]
    review_payload["score"]["summary"] = review_payload["summary"]
    review_payload["score"]["action_label"] = "review_required"
    review_payload["score"]["action_display_name"] = "动作待确认"
    review_payload["score"]["error_code"] = ""
    review_payload["score"]["fallback_used"] = True
    review_payload["score"]["fallback_reason"] = fallback_reason
    return review_payload


def _build_formal_payload(
    video_path: Path,
    *,
    analyzer_used: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    base_payload = dict(payload)
    score = dict(base_payload.get("score") or {})
    main_action = _video_main_action_from_payload(base_payload)
    if main_action in {"unknown", "review_required"}:
        return _build_review_required_payload(
            video_path,
            analyzer_used=analyzer_used,
            payload=base_payload,
            reasons=["action_unstable"],
        )

    display_name = _video_main_action_display_name(main_action)
    template = _video_main_action_template(main_action)
    confidence = float(base_payload.get("confidence", score.get("confidence", 0.0)) or 0.0)
    confidence_gap = float(base_payload.get("confidence_gap", score.get("confidence_gap", 0.0)) or 0.0)
    action_candidates = list(base_payload.get("action_candidates") or [])
    if not action_candidates and base_payload.get("raw_action_candidates"):
        action_candidates = [
            {
                "label": _video_main_action_class(candidate.get("action") or candidate.get("label") or candidate.get("template")),
                "action": _video_main_action_class(candidate.get("action") or candidate.get("label") or candidate.get("template")),
                "display_name": _video_main_action_display_name(_video_main_action_class(candidate.get("action") or candidate.get("label") or candidate.get("template"))),
                "score": round(float(candidate.get("score", 0.0) or 0.0), 3),
                "sources": list(candidate.get("sources") or []),
                "template": _video_main_action_template(_video_main_action_class(candidate.get("action") or candidate.get("label") or candidate.get("template"))),
            }
            for candidate in base_payload.get("raw_action_candidates") or []
            if isinstance(candidate, dict)
        ]

    overall = _video_coerce_numeric(base_payload.get("overall_score", score.get("overall")))
    if overall is None:
        overall = 0.0
    level_code, level_label = score_level_from_overall(float(overall))

    score_block = dict(score)
    score_block.update(
        {
            "overall": round(float(overall), 1),
            "level_code": level_code,
            "level_label": level_label,
            "action_label": main_action,
            "action_display_name": display_name,
            "action_candidates": action_candidates,
            "confidence": round(float(confidence), 3),
            "confidence_gap": round(float(confidence_gap), 3),
            "needs_confirmation": False,
            "uncertainty_reasons": list(base_payload.get("uncertainty_reasons") or score.get("uncertainty_reasons") or []),
        }
    )
    if "pass_subscore" in base_payload:
        score_block["pass_subscore"] = round(float(base_payload.get("pass_subscore", 0.0) or 0.0), 1)
    if "receive_subscore" in base_payload:
        score_block["receive_subscore"] = round(float(base_payload.get("receive_subscore", 0.0) or 0.0), 1)
    if "sequence_continuity_score" in base_payload:
        score_block["sequence_continuity_score"] = round(float(base_payload.get("sequence_continuity_score", 0.0) or 0.0), 1)
    if "next_action_readiness" in base_payload:
        score_block["next_action_readiness"] = round(float(base_payload.get("next_action_readiness", 0.0) or 0.0), 1)
    if "technical_execution" in score_block:
        score_block["technical_execution"] = round(float(score_block["technical_execution"] or 0.0), 1)
    if "control_stability" in score_block:
        score_block["control_stability"] = round(float(score_block["control_stability"] or 0.0), 1)
    if "action_safety" in score_block:
        score_block["action_safety"] = round(float(score_block["action_safety"] or 0.0), 1)

    issues = list(base_payload.get("issues") or [])
    evidence = {
        "analysis_confidence": float(base_payload.get("analysis_confidence", 0.0) or 0.0),
    }
    summary = _video_summary(display_name, score_block, issues, evidence, fallback_used=False)

    normalized_payload = dict(base_payload)
    normalized_payload.update(
        {
            "action_name": main_action,
            "action_label": main_action,
            "detected_action": main_action,
            "final_detected_action": main_action,
            "mapped_rule_key": template,
            "recommended_template": template,
            "final_mapped_rule_key": template,
            "resolved_action_name": template,
            "action_display_name": display_name,
            "routed_analyzer": str(base_payload.get("routed_analyzer") or base_payload.get("analyzer_used") or main_action),
            "system_action_suggestion": str(base_payload.get("system_action_suggestion") or ""),
            "route_mismatch": bool(base_payload.get("route_mismatch", False)),
            "route_mismatch_message": str(base_payload.get("route_mismatch_message") or ""),
            "action_confidence": round(float(confidence), 3),
            "confidence": round(float(confidence), 3),
            "confidence_gap": round(float(confidence_gap), 3),
            "needs_confirmation": False,
            "uncertainty_reasons": list(base_payload.get("uncertainty_reasons") or score.get("uncertainty_reasons") or []),
            "fallback_used": False,
            "fallback_reason": "",
            "fallback_reasons": [],
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": bool(base_payload.get("unsupported_action_for_current_analyzer", False)),
            "score_source": str(base_payload.get("score_source") or "proxy_rule_metrics"),
            "ball_speed_measurement_type": str(base_payload.get("ball_speed_measurement_type") or score.get("measurement_mode") or "proxy"),
            "score": score_block,
            "overall_score": round(float(overall), 1),
            "summary": summary,
            "score_ready": bool(base_payload.get("score_ready", True)),
            "scoring_state": str(base_payload.get("scoring_state") or "ready_to_score"),
            "status": str(base_payload.get("status") or "ok"),
            "error_code": "",
            "anomaly_reason": "",
            "inconsistent_fields": [],
            "integrity_state": str(base_payload.get("integrity_state") or ("route_mismatch" if base_payload.get("route_mismatch") else "normal")),
        }
    )
    normalized_payload["score"]["summary"] = summary
    normalized_payload["score"]["action_label"] = main_action
    normalized_payload["score"]["action_display_name"] = display_name
    normalized_payload["score"]["fallback_used"] = False
    normalized_payload["score"]["fallback_reason"] = ""
    normalized_payload["score"]["reference_only"] = False
    normalized_payload["score"]["reference_only_overall"] = round(float(overall), 1)
    normalized_payload["score"]["error_code"] = ""
    return normalized_payload


def _build_generic_error_payload(
    video_path: Path,
    *,
    error_code: str,
    message: str,
    analyzer_used: str = VIDEO_ANALYZER_USED,
    recommended_template: str = VIDEO_FALLBACK_TEMPLATE,
) -> Dict[str, Any]:
    generated_at = _now_iso()
    payload = {
        "analysis_version": VIDEO_ANALYSIS_VERSION,
        "analysis_mode": VIDEO_ANALYSIS_MODE,
        "analyzer_used": analyzer_used,
        "routed_analyzer": recommended_template,
        "error_code": error_code,
        "input_video_path": str(video_path),
        "video_path": str(video_path),
        "clip_id": _slugify(video_path.stem),
        "generated_at": generated_at,
        "duration_s": 0.0,
        "frame_count": 0,
        "detected_action": "uncertain",
        "action_confidence": 0.0,
        "mapped_rule_key": recommended_template,
        "recommended_template": recommended_template,
        "fallback_used": True,
        "whether_fallback_template_used": True,
        "unsupported_action_for_current_analyzer": False,
        "score_source": "proxy_rule_metrics",
        "ball_speed_measurement_type": "proxy",
        "action_name": recommended_template,
        "input_action_name": "uncertain",
        "resolved_action_name": recommended_template,
        "raw_detected_action": "uncertain",
        "raw_action_candidates": [],
        "candidate_scores": {},
        "action_label": "uncertain",
        "action_display_name": "动作待确认",
        "action_candidates": [],
        "confidence": 0.0,
        "confidence_gap": 0.0,
        "needs_confirmation": False,
        "uncertainty_reasons": [error_code],
        "stage1_action_label": "non_kick",
        "stage1_confidence": 0.0,
        "sequence_upgrade_applied": False,
        "sequence_upgrade_reason": "",
        "final_detected_action": "uncertain",
        "final_mapped_rule_key": recommended_template,
        "sequence_context": {},
        "score": {
            "overall": 0.0,
            "technical_execution": 0.0,
            "control_stability": 0.0,
            "action_safety": 0.0,
            "level_code": "needs_strengthen",
            "level_label": "需加强",
            "source": "proxy_rule_metrics",
            "measurement_mode": "proxy",
        },
        "overall_score": 0.0,
        "summary": message,
        "issues": [
            {
                "id": error_code,
                "title": message,
                "phase": "setup",
                "time": 0.0,
                "short_hint": message,
                "explanation": message,
                "fix_advice": message,
                "training_advice": message,
                "severity": 1.0,
            }
        ],
        "phase_scores": {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
        "primary_metrics": [],
        "sub_scores": {},
        "triggered_rules": [
            {
                "id": error_code,
                "metric": error_code,
                "label": message,
                "severity": "fail",
                "reason": message,
                "phase": "setup",
                "time": 0.0,
                "role": "primary",
                "quality_impact": "primary",
            }
        ],
        "fail_reasons": [message],
        "feedback_messages": [message],
        "error_timestamps": [
            {
                "rule_id": error_code,
                "phase": "setup",
                "time": 0.0,
                "severity": "fail",
                "reason": message,
            }
        ],
        "quality_status": "fail",
        "quality_gate": {
            "quality_status": "fail",
            "passed": False,
            "allow_micro_technique_score": False,
            "hide_micro_technique_score": True,
            "should_reshoot": True,
            "reshoot_hint": message,
            "triggered_rules": [
                {
                    "id": error_code,
                    "severity": "fail",
                    "reason": message,
                }
            ],
            "fail_reasons": [message],
            "thresholds": {},
            "observed": {},
        },
        "best_trial": {
            "metric": "overall",
            "label": load_football_rules().get("actions", {}).get(recommended_template, {}).get("display_name", recommended_template),
            "score": 0.0,
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        },
        "worst_trial": {
            "metric": "overall",
            "label": load_football_rules().get("actions", {}).get(recommended_template, {}).get("display_name", recommended_template),
            "score": 0.0,
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        },
        "rule_metrics": {},
        "analysis_confidence": 0.0,
        "score_ready": False,
        "scoring_state": "quality_fail",
        "status": "error",
        "warnings": [error_code],
    }
    return payload


def _video_evidence_limited_feedback(main_action: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    display_name = _video_main_action_display_name(main_action)
    if main_action == "shot":
        issues = [
            {
                "id": "shot_capture_reference",
                "title": "射门证据不足",
                "phase": "contact",
                "time": 0.0,
                "short_hint": "补拍触球前后 1 秒",
                "explanation": "当前视频没有稳定读取到完整射门触球窗口，射门发力链和触球部位先不做强判断。",
                "fix_advice": "重新拍摄时让支撑脚、摆腿、球和球门方向同时入镜，触球前后各保留 1 秒。",
                "training_advice": "先做 3 组 x 8 次定点射门，关注支撑脚站稳、脚背触球和随摆方向，再逐步提高球速。",
                "severity": 0.45,
            }
        ]
        feedback_messages = [
            "本次射门结果先作为参考，请补拍触球前后 1 秒且保持球门方向入镜。",
            "训练先从支撑脚稳定、脚背触球和随摆方向三点做起，每组 8 次，先稳再提速。",
        ]
    elif main_action == "pass_receive_sequence":
        issues = [
            {
                "id": "sequence_capture_reference",
                "title": "传接衔接证据不足",
                "phase": "contact",
                "time": 0.0,
                "short_hint": "补拍传球和接球完整段",
                "explanation": "当前视频没有稳定读取到传球到接球的连续窗口，传接间隔和下一动作准备度先不做强判断。",
                "fix_advice": "重新拍摄时保留传球、球运行、接球第一脚和下一动作准备，全程固定机位。",
                "training_advice": "做 4 组 x 10 次一传一接练习，要求第一脚把球停向下一步处理方向，第二脚在 2 秒内完成传出。",
                "severity": 0.45,
            }
        ]
        feedback_messages = [
            "本次传接球结果先作为参考，请补拍完整传球、接球和下一动作准备。",
            "训练先做一传一接 4 组 x 10 次，重点看第一脚停球方向和第二脚出球节奏。",
        ]
    else:
        issues = [
            {
                "id": "pass_capture_reference",
                "title": "传球证据不足",
                "phase": "contact",
                "time": 0.0,
                "short_hint": "补拍触球前后 1 秒",
                "explanation": "当前视频没有稳定读取到完整传球触球窗口，传球精度和支撑脚位置先不做强判断。",
                "fix_advice": "重新拍摄时让全身、球、支撑脚和出球方向同时入镜，触球前后各保留 1 秒。",
                "training_advice": "先做左右脚各 3 组 x 12 次定点传球，支撑脚脚尖指向目标，触球后身体朝目标方向跟随。",
                "severity": 0.45,
            }
        ]
        feedback_messages = [
            "本次传球结果先作为参考，请补拍全身、球和出球方向都清晰的角度。",
            "训练先做定点传球左右脚各 3 组 x 12 次，重点看支撑脚指向和触球后随动。",
        ]

    issues[0]["action_display_name"] = display_name
    return issues, feedback_messages


def _build_evidence_limited_reference_payload(
    video_path: Path,
    *,
    reason: str,
    message: str,
    selected_action: str,
    route: Any,
    probe: Optional[Dict[str, Any]] = None,
    warnings: Optional[Iterable[str]] = None,
    long_video_localized: bool = False,
    candidate_windows: Optional[List[Dict[str, Any]]] = None,
    selected_window_index: Optional[int] = None,
    selected_window_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    probe = probe or {}
    selected_action_value = _video_selected_action_canonical(selected_action)
    selected_family = _video_main_action_class(selected_action_value)
    if selected_family in {"unknown", "review_required"}:
        selected_family = _video_main_action_class(getattr(route, "selected_action", ""))
    if selected_family in {"unknown", "review_required"}:
        selected_family = "pass"

    display_name = _video_main_action_display_name(selected_family)
    template = _video_main_action_template(selected_family)
    routed_analyzer = str(getattr(route, "routed_analyzer", "") or template)
    analysis_template = str(getattr(route, "analysis_template", "") or template)
    analysis_routed_by = str(getattr(route, "analysis_routed_by", "") or ("user_selected" if selected_action_value else "auto_detected"))
    system_action_suggestion = str(getattr(route, "system_action_suggestion", "") or selected_family)
    route_mismatch = bool(getattr(route, "route_mismatch", False))
    route_mismatch_message = str(getattr(route, "route_mismatch_message", "") or "")
    route_warnings = list(getattr(route, "warnings", []) or [])
    warnings_list = list(dict.fromkeys(route_warnings + [str(item) for item in (warnings or []) if str(item).strip()] + [reason, "evidence_limited_reference"]))
    candidate_windows = list(candidate_windows or [])
    frame_count = int(probe.get("frame_count", 0) or 0)
    duration_s = round(float(probe.get("duration_s", 0.0) or 0.0), 3)
    generated_at = _now_iso()
    issues, feedback_messages = _video_evidence_limited_feedback(selected_family)
    summary = (
        f"{display_name}结果先作为参考：当前视频证据不足，未稳定读取到完整触球窗口。"
        "建议换固定机位重拍，让全身、球和触球前后各 1 秒清晰入镜。"
    )
    if message:
        summary = f"{display_name}结果先作为参考：{message}"

    score_block = {
        "overall": None,
        "technical_execution": None,
        "control_stability": None,
        "action_safety": None,
        "level_code": "reference_only",
        "level_label": "参考项",
        "source": "evidence_limited_reference",
        "measurement_mode": "proxy",
        "action_label": selected_family,
        "action_display_name": display_name,
        "action_candidates": [
            {
                "label": selected_family,
                "action": selected_family,
                "display_name": display_name,
                "score": 1.0,
                "template": template,
                "sources": ["user_selected"],
            }
        ],
        "confidence": 1.0 if analysis_routed_by == "user_selected" else 0.0,
        "confidence_gap": 1.0 if analysis_routed_by == "user_selected" else 0.0,
        "needs_confirmation": False,
        "uncertainty_reasons": warnings_list,
        "reference_only": True,
        "reference_only_summary": summary,
        "summary": summary,
        "fallback_used": True,
        "fallback_reason": reason,
        "error_code": "",
    }

    return {
        "analysis_version": VIDEO_ANALYSIS_VERSION,
        "analysis_mode": VIDEO_ANALYSIS_MODE,
        "analyzer_used": routed_analyzer,
        "routed_analyzer": routed_analyzer,
        "input_video_path": str(video_path),
        "video_path": str(video_path),
        "clip_id": _slugify(video_path.stem),
        "generated_at": generated_at,
        "duration_s": duration_s,
        "frame_count": frame_count,
        "detected_action": selected_family,
        "final_detected_action": selected_family,
        "action_confidence": 1.0 if analysis_routed_by == "user_selected" else 0.0,
        "selected_action": selected_action_value or selected_family,
        "analysis_template": analysis_template,
        "analysis_routed_by": analysis_routed_by,
        "suggested_action": "" if system_action_suggestion == selected_family else system_action_suggestion,
        "suggestion_reason": "系统识别仅作为参考，最终仍按用户选择的动作类型分析。" if system_action_suggestion != selected_family else "",
        "system_action_suggestion": system_action_suggestion,
        "route_mismatch": route_mismatch,
        "route_mismatch_message": route_mismatch_message,
        "action_label": selected_family,
        "action_candidates": score_block["action_candidates"],
        "confidence": score_block["confidence"],
        "confidence_gap": score_block["confidence_gap"],
        "needs_confirmation": False,
        "uncertainty_reasons": warnings_list,
        "stage1_action_label": "kick",
        "stage1_confidence": 1.0 if analysis_routed_by == "user_selected" else 0.0,
        "mapped_rule_key": template,
        "recommended_template": template,
        "fallback_used": True,
        "fallback_reason": reason,
        "fallback_reasons": warnings_list,
        "whether_fallback_template_used": True,
        "evidence_limited_fallback": True,
        "unsupported_action_for_current_analyzer": False,
        "score_source": "evidence_limited_reference",
        "ball_speed_measurement_type": "proxy",
        "action_name": selected_family,
        "input_action_name": selected_family,
        "raw_detected_action": selected_family,
        "resolved_action_name": template,
        "action_display_name": display_name,
        "raw_action_candidates": [],
        "candidate_scores": {selected_family: 1.0},
        "sequence_upgrade_applied": False,
        "sequence_upgrade_reason": "",
        "final_mapped_rule_key": template,
        "sequence_context": {},
        "metric_debug": {},
        "score": score_block,
        "overall_score": None,
        "level_label": "参考项",
        "summary": summary,
        "issues": issues,
        "phase_scores": {"preparation": None, "support": None, "contact": None, "follow_through": None},
        "analysis_confidence": 0.0,
        "score_ready": False,
        "scoring_state": "evidence_limited_reference",
        "status": "provisional",
        "analysis_status": "partial",
        "failure_reason": None,
        "failure_message": None,
        "primary_metrics": [],
        "sub_scores": {},
        "triggered_rules": [],
        "fail_reasons": [],
        "feedback_messages": feedback_messages[:2],
        "error_timestamps": [],
        "quality_status": "limited",
        "quality_gate": {
            "quality_status": "limited",
            "passed": False,
            "allow_micro_technique_score": False,
            "hide_micro_technique_score": True,
            "should_reshoot": True,
            "reshoot_hint": summary,
            "triggered_rules": [],
            "fail_reasons": [],
            "thresholds": {},
            "observed": {},
        },
        "best_trial": None,
        "worst_trial": None,
        "rule_metrics": {},
        "warnings": warnings_list,
        "error_code": "",
        "anomaly_reason": "",
        "inconsistent_fields": [],
        "integrity_state": "normal",
        "long_video_localized": bool(long_video_localized),
        "candidate_window_count": len(candidate_windows),
        "candidate_windows": candidate_windows,
        "selected_window_index": selected_window_index,
        "selected_window_start_s": selected_window_meta.get("start_s") if isinstance(selected_window_meta, dict) else None,
        "selected_window_end_s": selected_window_meta.get("end_s") if isinstance(selected_window_meta, dict) else None,
        "selected_window_duration_s": selected_window_meta.get("duration_s") if isinstance(selected_window_meta, dict) else None,
        "selected_window": selected_window_meta if isinstance(selected_window_meta, dict) else None,
    }


def analyze_video(
    video_path: str | Path,
    *,
    output_path: str | Path | None = None,
    work_dir: str | Path | None = None,
    frame_stride: int = 1,
    calibration_path: str | Path | None = None,
    selected_action: str | None = None,
    analysis_template: str | None = None,
    frame_ranges: Optional[List[Tuple[int, int]]] = None,
    long_video_localized: bool = False,
    candidate_windows: Optional[List[Dict[str, Any]]] = None,
    selected_window_index: Optional[int] = None,
    selected_window_meta: Optional[Dict[str, Any]] = None,
    skip_long_video_limit_check: bool = False,
) -> Dict[str, Any]:
    video_path = Path(video_path)
    analysis_started_at = perf_counter()
    selected_action_value = str(selected_action or "").strip().lower()
    base_route = resolve_analysis_route(
        selected_action_value,
        analysis_template=analysis_template,
        system_action_suggestion="",
        analysis_routed_by="user_selected" if selected_action_value else "request_validation",
    )
    if not video_path.exists():
        payload = _build_generic_error_payload(
            video_path,
            error_code="video_open_failed",
            message="视频路径不存在，无法执行通用视频分析。",
        )
        payload.update(
            {
                "selected_action": selected_action_value,
                "analysis_routed_by": base_route.analysis_routed_by,
                "routed_analyzer": base_route.routed_analyzer,
                "system_action_suggestion": base_route.system_action_suggestion,
            }
        )
        payload = _video_attach_response_metadata(
            payload,
            run_data={
                "warnings": ["video_open_failed"],
                "fast_mode_enabled": False,
                "candidate_windows": [],
                "candidate_window_count": 0,
                "long_video_localized": False,
            },
            probe={"video_opened": False, "warnings": ["video_open_failed"], "duration_s": 0.0, "frame_count": 0},
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
        )
        _video_debug_print_result_fields(payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    analysis_cache_key = _video_cache_key(
        video_path,
        selected_action=selected_action_value,
        analysis_template=analysis_template,
        frame_ranges=frame_ranges,
        long_video_localized=long_video_localized,
        skip_long_video_limit_check=skip_long_video_limit_check,
    )
    cached_payload = _video_cache_get(analysis_cache_key, video_path)
    if cached_payload is not None:
        _video_debug_print_result_fields(cached_payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(cached_payload, ensure_ascii=False, indent=2))
        return cached_payload

    if output_path is None and work_dir is not None:
        output_path = _default_work_dir(video_path, Path(work_dir)) / "video_analysis.json"

    probe = _probe_video_metadata(video_path)
    if not probe.get("video_opened", False):
        payload = _build_generic_error_payload(
            video_path,
            error_code="video_open_failed",
            message="视频无法打开，请检查文件是否损坏或格式是否受支持。",
        )
        payload.update(
            {
                "selected_action": selected_action_value,
                "analysis_routed_by": base_route.analysis_routed_by,
                "routed_analyzer": base_route.routed_analyzer,
                "system_action_suggestion": base_route.system_action_suggestion,
            }
        )
        payload = _video_attach_response_metadata(
            payload,
            run_data={
                "warnings": list(probe.get("warnings") or []),
                "fast_mode_enabled": False,
                "candidate_windows": [],
                "candidate_window_count": 0,
                "long_video_localized": False,
            },
            probe=probe,
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
        )
        _video_debug_print_result_fields(payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    calibration = _load_video_calibration(calibration_path)
    probe_duration_s = float(probe.get("duration_s", 0.0) or 0.0)
    fast_mode_enabled = bool(frame_ranges or long_video_localized or probe_duration_s > VIDEO_LONG_VIDEO_LOCALIZE_THRESHOLD_S)

    if _video_selected_action_canonical(selected_action_value) == "full_match":
        if probe_duration_s > VIDEO_SINGLE_PLAYER_VIDEO_LIMIT_S:
            payload = _build_generic_error_payload(
                video_path,
                error_code="video_too_long",
                message="单一球员长视频分析当前支持 140 分钟以内视频，请先裁剪或分段上传。",
            )
            payload.update(
                {
                    "selected_action": selected_action_value,
                    "analysis_routed_by": base_route.analysis_routed_by,
                    "routed_analyzer": base_route.routed_analyzer,
                    "system_action_suggestion": base_route.system_action_suggestion,
                    "analysis_status": "failed",
                    "failure_reason": "video_too_long",
                    "failure_message": "单一球员长视频分析当前支持 140 分钟以内视频，请先裁剪或分段上传。",
                    "video_duration_s": round(probe_duration_s, 3),
                    "warnings": list(dict.fromkeys(list(probe.get("warnings") or []) + ["video_too_long"])),
                }
            )
            payload = _video_attach_response_metadata(
                payload,
                run_data={
                    "warnings": list(payload.get("warnings") or []),
                    "fast_mode_enabled": False,
                    "candidate_windows": [],
                    "candidate_window_count": 0,
                    "long_video_localized": False,
                },
                probe=probe,
                processing_time_s=round(perf_counter() - analysis_started_at, 3),
            )
            _video_debug_print_result_fields(payload)
            if output_path is not None:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            return payload

        payload = _build_full_match_payload(
            video_path,
            probe=probe,
            selected_action=selected_action_value,
            analysis_template=analysis_template,
            calibration=calibration,
            analysis_started_at=analysis_started_at,
        )
        _video_cache_store(analysis_cache_key, payload)
        _video_debug_print_result_fields(payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    if not skip_long_video_limit_check and probe_duration_s > VIDEO_LONG_VIDEO_LIMIT_S:
        payload = _build_generic_error_payload(
            video_path,
            error_code="video_too_long",
            message=_video_failure_message("video_too_long", video_duration_s=probe_duration_s),
        )
        payload.update(
            {
                "selected_action": selected_action_value,
                "analysis_routed_by": base_route.analysis_routed_by,
                "routed_analyzer": base_route.routed_analyzer,
                "system_action_suggestion": base_route.system_action_suggestion,
                "analysis_status": "failed",
                "failure_reason": "video_too_long",
                "failure_message": _video_failure_message("video_too_long", video_duration_s=probe_duration_s),
                "long_video_localized": False,
                "candidate_window_count": 0,
                "selected_window_index": None,
                "selected_window_start_s": None,
                "selected_window_end_s": None,
                "selected_window_duration_s": None,
                "candidate_windows": [],
                "selected_window": None,
                "warnings": list(dict.fromkeys(list(probe.get("warnings") or []) + ["video_too_long"])),
            }
        )
        payload = _video_attach_response_metadata(
            payload,
            run_data={
                "warnings": list(probe.get("warnings") or []) + ["video_too_long"],
                "fast_mode_enabled": False,
                "candidate_windows": [],
                "candidate_window_count": 0,
                "long_video_localized": False,
            },
            probe=probe,
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
        )
        _video_debug_print_result_fields(payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    if frame_ranges is None and not long_video_localized and probe_duration_s > VIDEO_LONG_VIDEO_LOCALIZE_THRESHOLD_S:
        locator_result = locate_long_video_action_windows(
            video_path,
            selected_action=selected_action_value,
            max_windows=VIDEO_LONG_VIDEO_MAX_CANDIDATE_WINDOWS,
        )
        candidate_windows = expand_locator_windows(
            locator_result.get("candidate_windows") or [],
            duration_s=probe_duration_s,
            fps=float(locator_result.get("fps", probe.get("fps", 30.0)) or probe.get("fps", 30.0) or 30.0),
            pre_buffer_s=VIDEO_LONG_VIDEO_WINDOW_PRE_BUFFER_S,
            post_buffer_s=VIDEO_LONG_VIDEO_WINDOW_POST_BUFFER_S,
            min_duration_s=VIDEO_LONG_VIDEO_WINDOW_MIN_DURATION_S,
            max_duration_s=VIDEO_LONG_VIDEO_WINDOW_MAX_DURATION_S,
            max_windows=VIDEO_LONG_VIDEO_MAX_CANDIDATE_WINDOWS,
        )
        locator_warnings = list(dict.fromkeys(list(probe.get("warnings") or []) + list(locator_result.get("warnings") or [])))
        print(
            "[KICK_LONG_VIDEO_SCAN] "
            + json.dumps(
                {
                    "selected_action": selected_action_value,
                    "analysis_routed_by": base_route.analysis_routed_by,
                    "routed_analyzer": base_route.routed_analyzer,
                    "video_duration": round(float(probe_duration_s), 3),
                    "candidate_window_count": len(candidate_windows),
                    "warnings": locator_warnings,
                    "coarse_confidence": locator_result.get("coarse_confidence"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        print(
            "[KICK_CANDIDATE_WINDOWS] "
            + json.dumps(
                {
                    "selected_action": selected_action_value,
                    "analysis_routed_by": base_route.analysis_routed_by,
                    "routed_analyzer": base_route.routed_analyzer,
                    "candidate_windows": candidate_windows,
                    "suspected_contact_times": locator_result.get("suspected_contact_times", []),
                    "warnings": locator_warnings,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        if not candidate_windows:
            failure_reason = "low_motion_signal" if "low_motion_signal" in locator_warnings else "no_action_window_found"
            payload = _build_evidence_limited_reference_payload(
                video_path,
                reason=failure_reason,
                message=_video_failure_message(
                    failure_reason,
                    video_duration_s=probe_duration_s,
                    selected_action=selected_action_value,
                ),
                selected_action=selected_action_value,
                route=base_route,
                probe=probe,
                warnings=locator_warnings,
                long_video_localized=True,
                candidate_windows=[],
                selected_window_index=None,
                selected_window_meta=None,
            )
            payload.update(
                {
                    "selected_action": selected_action_value,
                    "analysis_routed_by": base_route.analysis_routed_by,
                    "routed_analyzer": base_route.routed_analyzer,
                    "system_action_suggestion": base_route.system_action_suggestion,
                    "analysis_status": "partial",
                    "failure_reason": None,
                    "failure_message": None,
                    "long_video_localized": True,
                    "candidate_window_count": 0,
                    "selected_window_index": None,
                    "selected_window_start_s": None,
                    "selected_window_end_s": None,
                    "selected_window_duration_s": None,
                    "candidate_windows": [],
                    "selected_window": None,
                    "warnings": locator_warnings,
                }
            )
            payload = _video_attach_response_metadata(
                payload,
                run_data={
                    "warnings": locator_warnings,
                    "fast_mode_enabled": True,
                    "candidate_windows": [],
                    "candidate_window_count": 0,
                    "long_video_localized": True,
                },
                probe=probe,
                processing_time_s=round(perf_counter() - analysis_started_at, 3),
                long_video_localized=True,
            )
            _video_cache_store(analysis_cache_key, payload)
            _video_debug_print_result_fields(payload)
            if output_path is not None:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            return payload

        candidate_payloads: List[Dict[str, Any]] = []
        total_candidates = len(candidate_windows)
        for index, window in enumerate(candidate_windows):
            window_frame_ranges = [tuple(window.get("frame_range") or (0, 0))]
            print(
                "[KICK_WINDOW_ANALYSIS] "
                + json.dumps(
                    {
                        "selected_action": selected_action_value,
                        "analysis_routed_by": base_route.analysis_routed_by,
                        "routed_analyzer": base_route.routed_analyzer,
                        "candidate_window_index": index,
                        "candidate_window_count": total_candidates,
                        "selected_window": summarize_window(window, selected=True),
                        "warnings": locator_warnings,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )
            candidate_payload = analyze_video(
                video_path,
                output_path=None,
                work_dir=None,
                frame_stride=max(1, int(frame_stride)),
                calibration_path=calibration_path,
                selected_action=selected_action_value,
                analysis_template=analysis_template,
                frame_ranges=window_frame_ranges,
                long_video_localized=True,
                candidate_windows=candidate_windows,
                selected_window_index=index,
                selected_window_meta=window,
                skip_long_video_limit_check=True,
            )
            candidate_payloads.append(candidate_payload)

        best_payload, ranked_payloads = select_best_analysis_payload(candidate_payloads)
        if best_payload is None:
            best_payload = {}
        best_payload = dict(best_payload)
        best_payload.update(
            {
                "candidate_windows": candidate_windows,
                "candidate_window_count": total_candidates,
                "selected_window_index": best_payload.get("selected_window_index", 0 if candidate_windows else None),
                "selected_window_start_s": best_payload.get("selected_window_start_s", candidate_windows[0].get("start_s") if candidate_windows else None),
                "selected_window_end_s": best_payload.get("selected_window_end_s", candidate_windows[0].get("end_s") if candidate_windows else None),
                "selected_window_duration_s": best_payload.get("selected_window_duration_s", candidate_windows[0].get("duration_s") if candidate_windows else None),
                "selected_window": best_payload.get("selected_window") or (candidate_windows[0] if candidate_windows else None),
                "long_video_localized": True,
                "fast_mode_enabled": True,
                "selected_action": selected_action_value,
                "analysis_routed_by": best_payload.get("analysis_routed_by", base_route.analysis_routed_by),
                "routed_analyzer": best_payload.get("routed_analyzer", base_route.routed_analyzer),
                "system_action_suggestion": best_payload.get("system_action_suggestion", base_route.system_action_suggestion),
            }
        )
        best_payload = _video_attach_response_metadata(
            best_payload,
            run_data={
                "warnings": list(dict.fromkeys(list(locator_warnings) + list(best_payload.get("warnings") or []))),
                "fast_mode_enabled": True,
                "candidate_windows": candidate_windows,
                "candidate_window_count": total_candidates,
                "long_video_localized": True,
                "selected_window": best_payload.get("selected_window"),
                "selected_window_index": best_payload.get("selected_window_index"),
                "selected_window_start_s": best_payload.get("selected_window_start_s"),
                "selected_window_end_s": best_payload.get("selected_window_end_s"),
                "selected_window_duration_s": best_payload.get("selected_window_duration_s"),
            },
            probe=probe,
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
            long_video_localized=True,
        )
        _video_cache_store(analysis_cache_key, best_payload)
        _video_debug_print_result_fields(best_payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(best_payload, ensure_ascii=False, indent=2))
        return best_payload

    print(
        "KICK_BACKEND_PRE_ANALYZER_CONTEXT = "
        + json.dumps(
            {
                "selected_action": selected_action_value,
                "system_action_suggestion": base_route.system_action_suggestion,
                "analysis_routed_by": base_route.analysis_routed_by,
                "routed_analyzer": base_route.routed_analyzer,
                "video_duration": float(probe.get("duration_s", 0.0) or 0.0),
                "frame_count": int(probe.get("frame_count", 0) or 0),
                "sampled_frame_count": 0,
                "failure_reason": base_route.failure_reason if base_route.failure_reason else "",
                "warnings": list(probe.get("warnings") or []),
                "fast_mode_enabled": fast_mode_enabled,
                "long_video_localized": bool(long_video_localized),
                "candidate_window_count": len(candidate_windows or []),
                "selected_window_index": selected_window_index,
                "selected_window": summarize_window(selected_window_meta, selected=True) if isinstance(selected_window_meta, dict) else None,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    process_started_at = perf_counter()
    run_data = _process_video(
        video_path,
        frame_stride=max(1, int(frame_stride)),
        fast_mode_enabled=fast_mode_enabled,
        frame_ranges=frame_ranges,
    )
    if candidate_windows is not None:
        run_data["candidate_windows"] = list(candidate_windows)
        run_data["candidate_window_count"] = len(candidate_windows)
    if selected_window_meta is not None:
        run_data["selected_window"] = dict(selected_window_meta)
        run_data["selected_window_index"] = selected_window_index
        run_data["selected_window_start_s"] = selected_window_meta.get("start_s")
        run_data["selected_window_end_s"] = selected_window_meta.get("end_s")
        run_data["selected_window_duration_s"] = selected_window_meta.get("duration_s")
    run_data["long_video_localized"] = bool(long_video_localized or frame_ranges is not None)
    processing_time_s = round(perf_counter() - process_started_at, 3)
    frame_count_for_log = int(run_data.get("frame_count", 0) or 0)
    sampled_frame_count_for_log = int(run_data.get("sampled_frame_count", 0) or 0)
    fps_for_log = float(run_data.get("fps", 30.0) or 30.0)
    video_duration_for_log = float(run_data.get("video_duration_s") or probe.get("duration_s") or (frame_count_for_log / fps_for_log if frame_count_for_log and fps_for_log > 0.0 else 0.0))
    print(f"KICK_BACKEND_VIDEO_DURATION = {video_duration_for_log:.3f}", flush=True)
    print(f"KICK_BACKEND_FRAME_COUNT = {frame_count_for_log}", flush=True)
    print(f"KICK_BACKEND_SAMPLED_FRAME_COUNT = {sampled_frame_count_for_log}", flush=True)
    print(f"KICK_BACKEND_PROCESSING_TIME = {round(perf_counter() - analysis_started_at, 3):.3f}", flush=True)
    print(f"KICK_BACKEND_FAST_MODE_ENABLED = {fast_mode_enabled}", flush=True)
    print(f"KICK_BACKEND_LONG_VIDEO_LOCALIZED = {bool(run_data.get('long_video_localized', False))}", flush=True)
    if run_data.get("selected_window") is not None:
        print(
            "KICK_BACKEND_SELECTED_WINDOW = "
            + json.dumps(run_data.get("selected_window"), ensure_ascii=False, sort_keys=True),
            flush=True,
        )
    samples = run_data.get("samples") or []
    if not samples:
        empty_warnings = list(dict.fromkeys(run_data.get("warnings", []) + ["analysis_result_empty"]))
        payload = _build_evidence_limited_reference_payload(
            video_path,
            reason="analysis_result_empty",
            message="视频证据不足，当前无法稳定读取可分析帧。",
            selected_action=selected_action_value,
            route=base_route,
            probe=probe,
            warnings=empty_warnings,
            long_video_localized=bool(long_video_localized or frame_ranges is not None),
            candidate_windows=list(candidate_windows or []),
            selected_window_index=selected_window_index,
            selected_window_meta=selected_window_meta,
        )
        payload["analysis_confidence"] = 0.0
        payload["status"] = "provisional"
        payload["analysis_status"] = "partial"
        payload["failure_reason"] = None
        payload["failure_message"] = None
        payload["warnings"] = list(dict.fromkeys(empty_warnings + payload.get("warnings", [])))
        payload = _video_attach_response_metadata(
            payload,
            run_data=run_data,
            probe=probe,
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
        )
        _video_cache_store(analysis_cache_key, payload)
        _video_debug_print_result_fields(payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    metrics, _aggregate_phase_scores, event_times, evidence, issue_times, warnings = _aggregate_metrics(samples)
    detection = _video_detect_action_context(run_data, metrics, evidence)

    rules = load_football_rules()
    route = video_analysis_router_v1(
        detection,
        rules=rules,
        run_data=run_data,
        metrics=metrics,
        evidence=evidence,
        selected_action=selected_action,
        analysis_template=analysis_template,
    )
    raw_detected_action = str(route.get("raw_detected_action", detection.get("detected_action", "uncertain")))
    action_label = str(route.get("action_label", detection.get("action_label", raw_detected_action)) or raw_detected_action or "uncertain")
    action_display_name = str(route.get("action_display_name", detection.get("action_display_name", "")) or "").strip() or (
        "动作待确认" if route.get("needs_confirmation") else _video_action_display_name(action_label or raw_detected_action)
    )
    analysis_routed_by = str(route.get("analysis_routed_by") or "auto_detected")
    manual_routed = analysis_routed_by == "user_selected"
    selected_action_effective = str(route.get("selected_action") or action_label or raw_detected_action or "uncertain")
    analysis_template_effective = str(route.get("analysis_template") or route.get("recommended_template") or "short_pass")
    suggested_action = str(route.get("suggested_action") or "")
    suggestion_reason = str(route.get("suggestion_reason") or "")
    final_detected_action = str(route.get("final_detected_action", route.get("detected_action", raw_detected_action)))
    routed_analyzer = str(route.get("routed_analyzer") or selected_action_effective or final_detected_action or "uncertain")
    action_confidence = float(route.get("action_confidence", detection.get("action_confidence", 0.0)) or 0.0)
    confidence = float(route.get("confidence", detection.get("confidence", action_confidence)) or action_confidence)
    confidence_gap = float(route.get("confidence_gap", detection.get("confidence_gap", 0.0)) or 0.0)
    needs_confirmation = bool(route.get("needs_confirmation", detection.get("needs_confirmation", False)))
    uncertainty_reasons = list(route.get("uncertainty_reasons") or detection.get("uncertainty_reasons") or [])
    action_candidates = list(route.get("action_candidates") or detection.get("action_candidates") or [])
    stage1_action_label = str(route.get("stage1_action_label", detection.get("stage1_action_label", "non_kick")) or "non_kick")
    stage1_confidence = float(route.get("stage1_confidence", detection.get("stage1_confidence", 0.0)) or 0.0)
    mapped_rule_key = str(route.get("final_mapped_rule_key", route.get("mapped_rule_key", "short_pass")))
    recommended_template = str(route.get("recommended_template", mapped_rule_key))
    analyzer_used = str(route.get("analyzer_used", VIDEO_ROUTER_ANALYZER))
    fallback_used = bool(route.get("fallback_used"))
    whether_fallback_template_used = bool(route.get("whether_fallback_template_used"))
    unsupported_action_for_current_analyzer = bool(route.get("unsupported_action_for_current_analyzer"))
    raw_action_candidates = list(route.get("raw_action_candidates") or [])
    candidate_scores = dict(route.get("candidate_scores") or {})
    sequence_upgrade_applied = bool(route.get("sequence_upgrade_applied"))
    sequence_upgrade_reason = str(route.get("sequence_upgrade_reason", ""))
    sequence_context = dict(route.get("sequence_context") or {})

    print(
        "[KICK_ANALYZER_ROUTE] "
        + json.dumps(
            {
                "selected_action": selected_action_effective,
                "system_action_suggestion": str(route.get("system_action_suggestion") or ""),
                "analysis_routed_by": analysis_routed_by,
                "routed_analyzer": routed_analyzer,
                "video_duration": round(float(video_duration_for_log), 3),
                "frame_count": frame_count_for_log,
                "sampled_frame_count": sampled_frame_count_for_log,
                "failure_reason": str(route.get("failure_reason") or ""),
                "warnings": list(dict.fromkeys(list(run_data.get("warnings") or []) + list(route.get("warnings") or []))),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )

    calibrated_scale = float((calibration or {}).get("scale_m_per_px", 0.0) or 0.0)
    calibrated = calibration is not None and calibrated_scale > 0.0
    score_source = "calibrated_rule_metrics" if calibrated else "proxy_rule_metrics"
    ball_speed_measurement_type = "calibrated" if calibrated else "proxy"
    metric_debug: Dict[str, Any] = {}

    quality_result = evaluate_global_quality_gate(
        run_data=run_data,
        metrics=metrics,
        rules=rules,
        action_name=mapped_rule_key,
    )

    generated_at = _now_iso()
    duration_s = round(float(run_data.get("frame_count", 0) or 0) / float(run_data.get("fps", 30.0) or 30.0), 3) if run_data.get("frame_count") else 0.0
    clip_id = _slugify(video_path.stem)
    video_resolved = str(video_path.resolve())
    analysis_confidence = round(float(evidence.get("analysis_confidence", 0.0) or 0.0), 3)

    def _finalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        payload["warnings"] = list(dict.fromkeys(list(run_data.get("warnings", [])) + list(warnings) + list(payload.get("warnings", []))))
        status = str(payload.get("status") or "").lower()
        final_payload = payload
        if status in {"ok", "provisional"}:
            fallback_reasons = _video_review_required_reasons(payload)
            if fallback_reasons:
                final_payload = _build_review_required_payload(
                    video_path,
                    analyzer_used=analyzer_used,
                    payload=payload,
                    reasons=fallback_reasons,
                )
            else:
                final_payload = _build_formal_payload(
                    video_path,
                    analyzer_used=analyzer_used,
                    payload=payload,
                )
                formal_reasons = _video_result_consistency_reasons(final_payload)
                if formal_reasons:
                    if any(reason.startswith("route_mismatch") for reason in formal_reasons):
                        final_payload = _build_result_inconsistent_payload(
                            video_path,
                            analyzer_used=analyzer_used,
                            payload=final_payload,
                            reasons=formal_reasons,
                        )
                    else:
                        final_payload = _build_review_required_payload(
                            video_path,
                            analyzer_used=analyzer_used,
                            payload=final_payload,
                            reasons=formal_reasons,
                        )
        final_payload = _video_attach_response_metadata(
            final_payload,
            run_data=run_data,
            probe=probe,
            processing_time_s=round(perf_counter() - analysis_started_at, 3),
        )
        _video_cache_store(analysis_cache_key, final_payload)
        _video_debug_print_result_fields(final_payload)
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2))
        return final_payload

    if unsupported_action_for_current_analyzer:
        unsupported_message = (
            f"当前仅接入 short_pass / pass_receive_sequence / receive_control / shot_instep 最小分析器，{mapped_rule_key} 暂未进入正式评分。"
        )
        payload = _build_generic_error_payload(
            video_path,
            error_code="unsupported_action_for_current_analyzer",
            message=unsupported_message,
            analyzer_used=analyzer_used,
            recommended_template=recommended_template,
        )
        issues: List[Dict[str, Any]] = [_unsupported_action_issue(raw_detected_action, mapped_rule_key, action_confidence)]
        if quality_result.get("quality_status") == "fail" or quality_result.get("should_reshoot"):
            issues.append(
                {
                    "id": "capture_quality_low",
                    "title": "视频证据不足",
                    "phase": "setup",
                    "time": 0.0,
                    "short_hint": "请补拍更清晰的视频",
                    "explanation": str(quality_result.get("reshoot_hint") or "当前视频证据不足，建议重新录制。"),
                    "fix_advice": str(quality_result.get("reshoot_hint") or "请重新录制更清晰、更稳定的视频。"),
                    "training_advice": "先保证全身、球和关键触球瞬间都入镜，再进行专项分析。",
                    "severity": 1.0,
                }
            )
        score_block = {
            "overall": 0.0,
            "technical_execution": 0.0,
            "control_stability": 0.0,
            "action_safety": 0.0,
            "level_code": "unsupported",
            "level_label": "暂未支持",
            "source": "unsupported_action_no_score",
            "measurement_mode": ball_speed_measurement_type,
            "action_label": action_label,
            "action_display_name": action_display_name,
            "action_candidates": action_candidates,
            "confidence": round(float(confidence), 3),
            "confidence_gap": round(float(confidence_gap), 3),
            "needs_confirmation": needs_confirmation,
            "uncertainty_reasons": uncertainty_reasons,
        }
        summary = _video_summary(action_display_name, score_block, issues, evidence, fallback_used=fallback_used)
        payload.update(
            {
                "analysis_version": VIDEO_ANALYSIS_VERSION,
                "analysis_mode": VIDEO_ANALYSIS_MODE,
                "analyzer_used": analyzer_used,
                "routed_analyzer": routed_analyzer,
                "input_video_path": str(video_path),
                "video_path": video_resolved,
                "clip_id": clip_id,
                "generated_at": generated_at,
                "duration_s": duration_s,
                "frame_count": int(run_data.get("frame_count", 0) or 0),
                "detected_action": final_detected_action,
                "action_confidence": round(float(action_confidence), 3),
                "selected_action": selected_action_effective,
                "analysis_template": analysis_template_effective,
                "analysis_routed_by": analysis_routed_by,
                "suggested_action": suggested_action,
                "suggestion_reason": suggestion_reason,
                "system_action_suggestion": str(route.get("system_action_suggestion") or ""),
                "route_mismatch": bool(route.get("route_mismatch", False)),
                "route_mismatch_message": str(route.get("route_mismatch_message") or ""),
                "mapped_rule_key": mapped_rule_key,
                "recommended_template": recommended_template,
                "fallback_used": fallback_used,
                "whether_fallback_template_used": whether_fallback_template_used,
                "unsupported_action_for_current_analyzer": True,
                "score_source": "unsupported_action_no_score",
                "ball_speed_measurement_type": ball_speed_measurement_type,
                "action_name": mapped_rule_key,
                "input_action_name": raw_detected_action,
                "raw_detected_action": raw_detected_action,
                "action_label": action_label,
                "action_candidates": action_candidates,
                "confidence": round(float(confidence), 3),
                "confidence_gap": round(float(confidence_gap), 3),
                "needs_confirmation": needs_confirmation,
                "uncertainty_reasons": uncertainty_reasons,
                "stage1_action_label": stage1_action_label,
                "stage1_confidence": round(float(stage1_confidence), 3),
                "resolved_action_name": mapped_rule_key,
                "action_display_name": action_display_name,
                "raw_action_candidates": raw_action_candidates,
                "candidate_scores": candidate_scores,
                "sequence_upgrade_applied": sequence_upgrade_applied,
                "sequence_upgrade_reason": sequence_upgrade_reason,
                "final_detected_action": final_detected_action,
                "final_mapped_rule_key": mapped_rule_key,
                "sequence_context": sequence_context,
                "metric_debug": metric_debug,
                "score": score_block,
                "overall_score": round(float(score_block.get("overall", 0.0) or 0.0), 1),
                "summary": summary,
                "issues": issues,
                "phase_scores": {
                    "preparation": 0.0,
                    "support": 0.0,
                    "contact": 0.0,
                    "follow_through": 0.0,
                },
                "analysis_confidence": analysis_confidence,
                "score_ready": False,
                "scoring_state": "unsupported_action",
                "status": "unsupported",
                "primary_metrics": [],
                "sub_scores": {},
                "triggered_rules": list(payload.get("triggered_rules") or []) + list(quality_result.get("triggered_rules") or []),
                "fail_reasons": list(
                    dict.fromkeys(
                        list(payload.get("fail_reasons") or [])
                        + list(quality_result.get("fail_reasons") or [])
                    )
                ),
                "feedback_messages": list(
                    dict.fromkeys(
                        list(payload.get("feedback_messages") or [])
                        + [unsupported_message]
                    )
                ),
                "error_timestamps": list(payload.get("error_timestamps") or []),
                "quality_status": quality_result.get("quality_status", "pass"),
                "quality_gate": quality_result,
                "best_trial": payload.get("best_trial"),
                "worst_trial": payload.get("worst_trial"),
                "rule_metrics": {},
            }
        )
        return _finalize_payload(payload)

    rule_metrics = _video_rule_metrics(mapped_rule_key, metrics, run_data, event_times, calibration)
    rule_metrics["ball_speed_measurement_type"] = rule_metrics.get("ball_speed_measurement_type", ball_speed_measurement_type)
    score_result = score_action(
        mapped_rule_key,
        rule_metrics,
        rules,
        audience="beginner",
        quality_result=quality_result,
        analysis_context={
            "rule_metrics": rule_metrics,
            "legacy_metrics": metrics,
            "run_data": run_data,
            "event_times": event_times,
            "issue_times": issue_times,
        },
    )
    metric_results = list(score_result.get("metric_results") or [])
    rule_metrics_output = dict(rule_metrics)
    rule_metrics_output.pop("metric_debug", None)

    metric_debug = dict(rule_metrics.get("metric_debug") or {})
    if mapped_rule_key == "pass_receive_sequence":
        receive_metric = next(
            (
                dict(item)
                for item in metric_results
                if isinstance(item, dict) and str(item.get("metric")) == "receive_control_zone_success_rate"
            ),
            {},
        )
        metric_debug["receive_control_zone_success_rate_band_logic"] = {
            "raw_value": receive_metric.get("raw_value"),
            "score": receive_metric.get("score"),
            "band": receive_metric.get("band"),
            "direction": receive_metric.get("direction", "higher_is_better"),
            "thresholds": receive_metric.get("thresholds"),
            "logic": [
                {"if": "raw_value >= excellent", "band": "excellent"},
                {"if": "raw_value >= good", "band": "good"},
                {"if": "raw_value >= needs_work", "band": "needs_work"},
                {"otherwise": "poor"},
            ],
        }

    uncertainty_trigger: List[Dict[str, Any]] = []
    if fallback_used or (not manual_routed and action_confidence < VIDEO_ACTION_CONFIDENCE_THRESHOLD):
        uncertainty_trigger.append(
            {
                "id": "action_pattern_unclear",
                "metric": "action_pattern_unclear",
                "label": "动作识别不够明确",
                "severity": "warn",
                "reason": f"当前动作识别置信度偏低（{action_confidence:.2f}），系统已使用推荐模板进行保守分析。",
                "phase": "setup",
                "time": 0.0,
                "role": "diagnostic_only",
                "quality_impact": "diagnostic_only",
            }
        )

    combined_triggers = _merge_triggered_rules(
        quality_result.get("triggered_rules") or [],
        score_result.get("triggered_rules") or [],
        uncertainty_trigger,
    )
    score_result_for_feedback = dict(score_result)
    score_result_for_feedback["triggered_rules"] = combined_triggers
    score_result_for_feedback["action_candidates"] = action_candidates
    score_result_for_feedback["needs_confirmation"] = needs_confirmation
    score_result_for_feedback["uncertainty_reasons"] = uncertainty_reasons
    feedback_result = build_feedback_messages(
        action_name=mapped_rule_key,
        rules=rules,
        score_result=score_result_for_feedback,
        quality_result=quality_result,
        analysis_context={
            "rule_metrics": rule_metrics,
            "legacy_metrics": metrics,
            "run_data": run_data,
            "needs_confirmation": needs_confirmation,
            "action_candidates": action_candidates,
            "uncertainty_reasons": uncertainty_reasons,
        },
    )
    timestamp_result = locate_error_timestamps(
        action_name=mapped_rule_key,
        triggered_rules=combined_triggers,
        rule_times=issue_times,
        event_times=event_times,
    )

    primary_metrics = [
        metric
        for metric in metric_results
        if isinstance(metric, dict) and metric.get("role") != "diagnostic_only"
    ]
    if not primary_metrics:
        primary_metrics = [
            {
                "metric": "analysis",
                "label": "Analysis",
                "raw_value": None,
                "score": None,
                "band": "missing",
                "role": "outcome",
                "source_class": "product_default",
                "use_as": "main_score",
                "diagnostic_only": False,
                "matched_key": None,
            }
        ]
    is_sequence_template = mapped_rule_key == "pass_receive_sequence"

    if is_sequence_template:
        pass_subscore = _video_group_score(metric_results, {"pass_endpoint_error_m", "pass_execution_time_s"})
        receive_subscore = _video_group_score(
            metric_results,
            {
                "receive_control_zone_success_rate",
                "receive_stabilization_time_s",
                "receive_corrective_touch_count",
            },
        )
        sequence_continuity_score = _video_metric_score(metric_results, "sequence_continuity_score")
        next_action_readiness = _video_metric_score(metric_results, "next_action_readiness")
        provisional_score = float(score_result.get("provisional_score") or score_result.get("overall_score") or 0.0)
        confidence_adjusted_score = float(score_result.get("confidence_adjusted_score") or score_result.get("overall_score") or 0.0)
        overall_score = confidence_adjusted_score
        level = _score_level_from_overall(overall_score)
        score_block = {
            "overall": round(float(overall_score), 1),
            "provisional_score": round(float(provisional_score), 1),
            "confidence_adjusted_score": round(float(confidence_adjusted_score), 1),
            "confidence_penalty_ratio": round(float(score_result.get("confidence_penalty_ratio") or 0.0), 3),
            "pass_subscore": round(float(pass_subscore), 1),
            "receive_subscore": round(float(receive_subscore), 1),
            "sequence_continuity_score": round(float(sequence_continuity_score), 1),
            "next_action_readiness": round(float(next_action_readiness), 1),
            **level,
            "source": score_source,
            "measurement_mode": ball_speed_measurement_type,
            "action_label": action_label,
            "action_display_name": action_display_name,
            "action_candidates": action_candidates,
            "confidence": round(float(confidence), 3),
            "confidence_gap": round(float(confidence_gap), 3),
            "needs_confirmation": needs_confirmation,
            "uncertainty_reasons": uncertainty_reasons,
        }
        phase_scores = {
            "preparation": round(float(min(100.0, max(0.0, pass_subscore * 0.82))), 1),
            "support": round(float(pass_subscore), 1),
            "contact": round(float(receive_subscore), 1),
            "follow_through": round(float(sequence_continuity_score), 1),
        }
    else:
        provisional_score = float(score_result.get("provisional_score") or score_result.get("overall_score") or 0.0)
        confidence_adjusted_score = float(score_result.get("confidence_adjusted_score") or score_result.get("overall_score") or 0.0)
        overall_score = confidence_adjusted_score
        technique_score = float(score_result.get("technique_score") or score_result.get("primary_score") or overall_score)
        control_score = float(score_result.get("outcome_score") or score_result.get("primary_score") or overall_score)
        safety_score = _proxy_action_safety(metrics, quality_result)
        level = _score_level_from_overall(overall_score)
        score_block = {
            "overall": round(float(overall_score), 1),
            "provisional_score": round(float(provisional_score), 1),
            "confidence_adjusted_score": round(float(confidence_adjusted_score), 1),
            "confidence_penalty_ratio": round(float(score_result.get("confidence_penalty_ratio") or 0.0), 3),
            "technical_execution": round(float(technique_score), 1),
            "control_stability": round(float(control_score), 1),
            "action_safety": round(float(safety_score), 1),
            **level,
            "source": score_source,
            "measurement_mode": ball_speed_measurement_type,
            "action_label": action_label,
            "action_display_name": action_display_name,
            "action_candidates": action_candidates,
            "confidence": round(float(confidence), 3),
            "confidence_gap": round(float(confidence_gap), 3),
            "needs_confirmation": needs_confirmation,
            "uncertainty_reasons": uncertainty_reasons,
        }
        phase_scores = {
            "preparation": round(float(min(100.0, max(0.0, control_score * 0.82))), 1),
            "support": round(float(control_score), 1),
            "contact": round(float(technique_score), 1),
            "follow_through": round(float(safety_score), 1),
        }

    issues = []
    if quality_result.get("quality_status") == "fail" or quality_result.get("should_reshoot"):
        issues.append(
            {
                "id": "capture_quality_low",
                "title": "视频证据不足",
                "phase": "setup",
                "time": 0.0,
                "short_hint": "请补拍更清晰的视频",
                "explanation": str(quality_result.get("reshoot_hint") or "当前视频证据不足，建议重新录制。"),
                "fix_advice": str(quality_result.get("reshoot_hint") or "请重新录制更清晰、更稳定的视频。"),
                "training_advice": "先保证全身、球和关键触球瞬间都入镜，再进行专项分析。",
                "severity": 1.0,
            }
        )
    if fallback_used and not issues:
        issues.append(_uncertainty_issue(action_confidence, mapped_rule_key))
    for rule in combined_triggers[:3]:
        if quality_result.get("quality_status") == "fail" and issues:
            break
        if rule.get("id") == "action_pattern_unclear" and fallback_used:
            continue
        issues.append(
            _video_issue_from_rule(
                rule,
                mapped_rule_key=mapped_rule_key,
                event_times=event_times,
                fallback_hint=str(feedback_result.get("feedback_messages", [""])[0] if feedback_result.get("feedback_messages") else ""),
            )
        )
    if not issues:
        issues.append(
            {
                "id": "stable_action",
                "title": "动作整体稳定",
                "phase": "follow_through",
                "time": float(event_times.get("sequence_complete", event_times.get("follow_through", 0.0))),
                "short_hint": "保持当前节奏，先稳住再提速",
                "explanation": "当前动作结构整体稳定，没有看到特别突出的关键失误。",
                "fix_advice": "继续保持支撑、躯干和摆腿的协同节奏。",
                "training_advice": "用同一视频节奏重复练习，保持动作结构稳定。",
                "severity": 0.12,
            }
        )

    summary = _video_summary(
        str(score_result.get("action_display_name") or action_display_name),
        score_block,
        issues,
        evidence,
        fallback_used=fallback_used,
    )
    if quality_result.get("should_reshoot"):
        summary = str(quality_result.get("reshoot_hint") or summary)

    score_ready = bool(samples) and str(quality_result.get("quality_status", "pass")) == "pass"
    if score_ready and not fallback_used and (manual_routed or action_confidence >= VIDEO_ACTION_CONFIDENCE_THRESHOLD):
        status = "ok"
    elif score_ready:
        status = "provisional"
    else:
        status = "provisional"

    payload = {
        "analysis_version": VIDEO_ANALYSIS_VERSION,
        "analysis_mode": VIDEO_ANALYSIS_MODE,
        "analyzer_used": analyzer_used,
        "routed_analyzer": routed_analyzer,
        "input_video_path": str(video_path),
        "video_path": video_resolved,
        "clip_id": clip_id,
        "generated_at": generated_at,
        "duration_s": duration_s,
        "frame_count": int(run_data.get("frame_count", 0) or 0),
        "detected_action": final_detected_action,
        "action_confidence": round(float(action_confidence), 3),
        "selected_action": selected_action_effective,
        "analysis_template": analysis_template_effective,
        "analysis_routed_by": analysis_routed_by,
        "suggested_action": suggested_action,
        "suggestion_reason": suggestion_reason,
        "system_action_suggestion": str(route.get("system_action_suggestion") or ""),
        "route_mismatch": bool(route.get("route_mismatch", False)),
        "route_mismatch_message": str(route.get("route_mismatch_message") or ""),
        "action_label": action_label,
        "action_candidates": action_candidates,
        "confidence": round(float(confidence), 3),
        "confidence_gap": round(float(confidence_gap), 3),
        "needs_confirmation": needs_confirmation,
        "uncertainty_reasons": uncertainty_reasons,
        "stage1_action_label": stage1_action_label,
        "stage1_confidence": round(float(stage1_confidence), 3),
        "mapped_rule_key": mapped_rule_key,
        "recommended_template": recommended_template,
        "fallback_used": fallback_used,
        "whether_fallback_template_used": whether_fallback_template_used,
        "unsupported_action_for_current_analyzer": unsupported_action_for_current_analyzer,
        "score_source": score_source,
        "ball_speed_measurement_type": ball_speed_measurement_type,
        "action_name": mapped_rule_key,
        "input_action_name": raw_detected_action,
        "raw_detected_action": raw_detected_action,
        "resolved_action_name": mapped_rule_key,
        "action_display_name": action_display_name,
        "raw_action_candidates": raw_action_candidates,
        "candidate_scores": candidate_scores,
        "sequence_upgrade_applied": sequence_upgrade_applied,
        "sequence_upgrade_reason": sequence_upgrade_reason,
        "final_detected_action": final_detected_action,
        "final_mapped_rule_key": mapped_rule_key,
        "sequence_context": sequence_context,
        "metric_debug": metric_debug,
        "score": score_block,
        "overall_score": round(float(score_block.get("overall", 0.0) or 0.0), 1),
        **(
            {
                "pass_subscore": round(float(pass_subscore), 1),
                "receive_subscore": round(float(receive_subscore), 1),
                "sequence_continuity_score": round(float(sequence_continuity_score), 1),
                "next_action_readiness": round(float(next_action_readiness), 1),
            }
            if is_sequence_template
            else {}
        ),
        "summary": summary,
        "issues": issues,
        "phase_scores": phase_scores,
        "analysis_confidence": analysis_confidence,
        "score_ready": score_ready,
        "scoring_state": "ready_to_score" if score_ready else ("quality_fail" if quality_result.get("quality_status") == "fail" else "insufficient_evidence"),
        "status": status,
        "primary_metrics": primary_metrics,
        "sub_scores": score_result.get("sub_scores", {}),
        "triggered_rules": combined_triggers,
        "fail_reasons": list(dict.fromkeys((feedback_result.get("fail_reasons") or []) + list(quality_result.get("fail_reasons") or []))),
        "feedback_messages": feedback_result.get("feedback_messages", []),
        "error_timestamps": timestamp_result.get("error_timestamps", []),
        "quality_status": quality_result.get("quality_status", "pass"),
        "quality_gate": quality_result,
        "best_trial": score_result.get("best_trial"),
        "worst_trial": score_result.get("worst_trial"),
        "rule_metrics": rule_metrics_output,
        "warnings": list(dict.fromkeys(run_data.get("warnings", []) + warnings)),
    }

    return _finalize_payload(payload)
