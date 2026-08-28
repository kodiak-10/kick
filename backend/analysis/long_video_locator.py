from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None

from analysis.ball_tracking import BallTracker, detect_ball, estimate_contact
from analysis.football_sequence import compute_football_kinematics, fresh_sequence_state, update_football_sequence
from analysis.video_windowing import build_window_from_contact, normalize_candidate_windows


_POSE_INDEX = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


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


def _to_xy(landmark, w: int, h: int) -> Tuple[float, float]:
    return float(landmark.x * w), float(landmark.y * h)


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


def _body_span(points: Dict[str, Tuple[float, float]]) -> float:
    return max(
        abs(points["left_shoulder"][1] - points["left_ankle"][1]),
        abs(points["right_shoulder"][1] - points["right_ankle"][1]),
        1.0,
    )


def _pose_metrics(points: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    shoulder_mid_x = (points["left_shoulder"][0] + points["right_shoulder"][0]) * 0.5
    hip_mid_x = (points["left_hip"][0] + points["right_hip"][0]) * 0.5
    shoulder_w = abs(points["left_shoulder"][0] - points["right_shoulder"][0]) + 1e-6
    balance = abs(shoulder_mid_x - hip_mid_x) / shoulder_w

    left_knee_dx = points["left_ankle"][0] - points["left_knee"][0]
    left_knee_dy = points["left_ankle"][1] - points["left_knee"][1]
    right_knee_dx = points["right_ankle"][0] - points["right_knee"][0]
    right_knee_dy = points["right_ankle"][1] - points["right_knee"][1]
    symmetry = abs((left_knee_dx * left_knee_dx + left_knee_dy * left_knee_dy) ** 0.5 - (right_knee_dx * right_knee_dx + right_knee_dy * right_knee_dy) ** 0.5)
    trunk_lean_deg = abs(float(np.degrees(np.arctan2(abs(shoulder_mid_x - hip_mid_x), max(1e-6, abs(points["left_shoulder"][1] - points["right_shoulder"][1]))))))

    return {
        "balance": float(balance),
        "symmetry": float(symmetry),
        "trunk_lean_deg": float(trunk_lean_deg),
    }


@dataclass(frozen=True)
class LongVideoLocatorResult:
    video_opened: bool
    fps: float
    frame_count: int
    duration_s: float
    sampled_frame_count: int
    target_sample_fps: float
    sample_stride: int
    candidate_windows: List[Dict[str, Any]]
    suspected_contact_times: List[float]
    coarse_confidence: float
    coarse_debug: Dict[str, Any]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_opened": self.video_opened,
            "fps": round(float(self.fps), 3),
            "frame_count": int(self.frame_count),
            "duration_s": round(float(self.duration_s), 3),
            "sampled_frame_count": int(self.sampled_frame_count),
            "target_sample_fps": round(float(self.target_sample_fps), 3),
            "sample_stride": int(self.sample_stride),
            "candidate_windows": list(self.candidate_windows),
            "suspected_contact_times": [round(float(value), 3) for value in self.suspected_contact_times],
            "coarse_confidence": round(float(self.coarse_confidence), 3),
            "coarse_debug": dict(self.coarse_debug),
            "warnings": list(self.warnings),
        }


def locate_long_video_action_windows(
    video_path: str | Path,
    *,
    selected_action: str | None = None,
    max_windows: int = 3,
) -> Dict[str, Any]:
    video_path = Path(video_path)
    warnings: List[str] = []
    if cv2 is None or mp is None:
        return LongVideoLocatorResult(
            video_opened=False,
            fps=30.0,
            frame_count=0,
            duration_s=0.0,
            sampled_frame_count=0,
            target_sample_fps=0.0,
            sample_stride=1,
            candidate_windows=[],
            suspected_contact_times=[],
            coarse_confidence=0.0,
            coarse_debug={"error": "opencv_or_mediapipe_unavailable"},
            warnings=["opencv_or_mediapipe_unavailable"],
        ).to_dict()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return LongVideoLocatorResult(
            video_opened=False,
            fps=30.0,
            frame_count=0,
            duration_s=0.0,
            sampled_frame_count=0,
            target_sample_fps=0.0,
            sample_stride=1,
            candidate_windows=[],
            suspected_contact_times=[],
            coarse_confidence=0.0,
            coarse_debug={"error": "video_open_failed"},
            warnings=["video_open_failed"],
        ).to_dict()

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0.0:
            fps = 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_s = float(frame_count) / fps if frame_count > 0 else 0.0

        if duration_s <= 0.0:
            warnings.append("video_duration_unavailable")

        target_sample_fps = 8.0 if duration_s <= 18.0 else 6.0
        sample_stride = max(1, int(round(fps / max(1.0, target_sample_fps))))

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
                    min_detection_confidence=0.45,
                    min_tracking_confidence=0.45,
                )
                if attempt != pose_init_attempts[0]:
                    pose_init_warnings.append("mediapipe_pose_fallback:" + json.dumps(attempt, ensure_ascii=False))
                break
            except Exception as exc:
                pose_init_warnings.append(f"mediapipe_pose_init_failed:{type(exc).__name__}:{json.dumps(attempt, ensure_ascii=False)}")

        if pose is None:
            warnings.extend(pose_init_warnings or ["mediapipe_pose_init_failed"])
            return LongVideoLocatorResult(
                video_opened=True,
                fps=fps,
                frame_count=frame_count,
                duration_s=duration_s,
                sampled_frame_count=0,
                target_sample_fps=target_sample_fps,
                sample_stride=sample_stride,
                candidate_windows=[],
                suspected_contact_times=[],
                coarse_confidence=0.0,
                coarse_debug={"pose_init_warnings": pose_init_warnings},
                warnings=warnings,
            ).to_dict()

        ball_tracker = BallTracker(max_misses=5)
        sequence_state = fresh_sequence_state()
        prev_points: Optional[Dict[str, Tuple[float, float]]] = None
        prev_raw_points: Optional[Dict[str, Tuple[float, float]]] = None
        prev_ball: Optional[Dict[str, float]] = None
        move_hist = deque(maxlen=8)

        samples: List[Dict[str, Any]] = []
        contact_times: List[float] = []
        motion_scores: List[float] = []
        ball_presence_scores: List[float] = []
        interaction_scores: List[float] = []
        sequence_scores: List[float] = []
        center_shift_scores: List[float] = []
        frame_indices: List[int] = []
        low_motion_frames = 0
        ball_visible_frames = 0
        contact_frames = 0
        active_frames = 0

        frame_idx = 0
        sampled_frame_count = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                if frame_idx % sample_stride != 0:
                    frame_idx += 1
                    continue

                sampled_frame_count += 1
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
                if result.pose_landmarks:
                    landmarks = result.pose_landmarks.landmark
                    raw_points, vis_avg = _extract_points(landmarks, w, h)
                    if prev_raw_points is not None:
                        diffs = [
                            abs(raw_points[key][0] - prev_raw_points[key][0]) + abs(raw_points[key][1] - prev_raw_points[key][1])
                            for key in raw_points.keys()
                            if key in prev_raw_points
                        ]
                        if diffs:
                            move_hist.append(sum(diffs) / len(diffs))
                    prev_raw_points = raw_points

                if raw_points is None:
                    current_points = None
                elif prev_points is None:
                    current_points = raw_points
                else:
                    blended = {
                        key: (
                            prev_points[key][0] * 0.68 + raw_points[key][0] * 0.32,
                            prev_points[key][1] * 0.68 + raw_points[key][1] * 0.32,
                        )
                        for key in raw_points.keys()
                        if key in prev_points
                    }
                    current_points = blended if len(blended) >= 6 else raw_points
                if current_points is None:
                    samples.append(
                        {
                            "index": frame_idx,
                            "time": now_t,
                            "phase": "set",
                            "phase_confidence": 0.0,
                            "sequence_active": False,
                            "sequence_ready": False,
                            "support_ball_ratio": 0.28,
                            "swing_ball_ratio": 0.16,
                            "ball_speed_ratio": 0.0,
                            "balance": 0.0,
                            "trunk_lean_deg": 0.0,
                            "symmetry": 0.0,
                            "stability": 0.0,
                            "visibility": vis_avg,
                            "move_score": 0.0,
                            "body_span": 1.0,
                            "contact": False,
                            "ball_present": False,
                            "ball_x": None,
                            "ball_y": None,
                            "ball_vx": 0.0,
                            "ball_vy": 0.0,
                            "ball_radius": None,
                            "ball_confidence": 0.0,
                            "events": {"support_plant": False, "contact": False, "follow_through_complete": False, "sequence_complete": False},
                            "coarse_score": 0.0,
                        }
                    )
                    frame_idx += 1
                    continue

                body_span = _body_span(current_points)
                move_score = float(sum(move_hist) / len(move_hist)) if move_hist else 0.0
                lower_body_motion_score = _clamp(move_score / max(1.0, 0.10 * body_span))
                stability = _clamp(1.0 - move_score / max(18.0, 0.11 * body_span))
                pose_metrics = _pose_metrics(current_points)

                ankles = {"left_ankle": current_points["left_ankle"], "right_ankle": current_points["right_ankle"]}
                ball_candidate = None
                if frame_idx % (sample_stride * 2) == 0 or ball_tracker.state is None or float(ball_tracker.state.get("confidence", 0.0)) < 0.42:
                    ball_candidate = detect_ball(frame, ankles=ankles, last_ball=prev_ball)
                tracked_ball = ball_tracker.update(ball_candidate, body_span_px=body_span)
                if tracked_ball is not None:
                    ball_visible_frames += 1

                contact = estimate_contact(tracked_ball, ankles, body_span) if tracked_ball is not None else {"side": "none", "distance_px": None, "contact": False}
                if contact.get("contact"):
                    contact_frames += 1
                    contact_times.append(now_t)

                previous_ball = prev_ball
                kin = compute_football_kinematics(
                    current_points,
                    prev_points,
                    tracked_ball,
                    previous_ball,
                    contact,
                    body_span,
                    move_score / max(1.0, body_span),
                )
                seq = update_football_sequence(sequence_state, kin, now_t)
                if seq.sequence_active:
                    active_frames += 1

                if kin.ball_speed_ratio >= 0.10:
                    contact_times.append(now_t)

                ball_presence = 1.0 if tracked_ball is not None else 0.0
                if ball_presence == 0.0:
                    low_motion_frames += 1

                foot_ball_interaction = 0.0
                if tracked_ball is not None:
                    distances = []
                    for ankle in ankles.values():
                        dx = float(tracked_ball["x"]) - float(ankle[0])
                        dy = float(tracked_ball["y"]) - float(ankle[1])
                        distances.append((dx * dx + dy * dy) ** 0.5)
                    if distances:
                        foot_ball_interaction = _clamp(1.0 - min(distances) / max(40.0, 3.2 * float(tracked_ball.get("radius", 14.0))))

                sequence_activity = _clamp(
                    0.42 * float(seq.phase_confidence)
                    + 0.30 * (1.0 if seq.sequence_active else 0.0)
                    + 0.18 * (1.0 if contact.get("contact") else 0.0)
                    + 0.10 * _clamp(float(kin.ball_speed_ratio) * 3.0)
                )
                center_shift = _clamp(abs(float(pose_metrics["balance"])) / 0.22)
                contact_signal = 1.0 if contact.get("contact") else _clamp(float(kin.ball_speed_ratio) * 4.0)
                coarse_score = _clamp(
                    0.30 * lower_body_motion_score
                    + 0.22 * ball_presence
                    + 0.22 * foot_ball_interaction
                    + 0.16 * sequence_activity
                    + 0.10 * max(center_shift, contact_signal)
                )

                if contact.get("contact") or kin.ball_speed_ratio >= 0.12:
                    contact_times.append(now_t)

                frame_indices.append(frame_idx)
                motion_scores.append(float(lower_body_motion_score))
                ball_presence_scores.append(float(ball_presence))
                interaction_scores.append(float(foot_ball_interaction))
                sequence_scores.append(float(sequence_activity))
                center_shift_scores.append(float(center_shift))

                samples.append(
                    {
                        "index": frame_idx,
                        "time": now_t,
                        "phase": seq.phase,
                        "phase_confidence": float(seq.phase_confidence),
                        "sequence_active": bool(seq.sequence_active),
                        "sequence_ready": bool(seq.sequence_ready),
                        "support_ball_ratio": float(seq.metrics.get("support_ball_ratio", 0.28)),
                        "swing_ball_ratio": float(seq.metrics.get("swing_ball_ratio", 0.16)),
                        "ball_speed_ratio": float(seq.metrics.get("ball_speed_ratio", 0.0)),
                        "balance": float(pose_metrics["balance"]),
                        "trunk_lean_deg": float(pose_metrics["trunk_lean_deg"]),
                        "symmetry": float(pose_metrics["symmetry"]),
                        "stability": float(stability),
                        "visibility": float(vis_avg),
                        "move_score": float(move_score),
                        "body_span": float(body_span),
                        "contact": bool(contact.get("contact")),
                        "ball_present": tracked_ball is not None,
                        "ball_x": float(tracked_ball["x"]) if tracked_ball is not None else None,
                        "ball_y": float(tracked_ball["y"]) if tracked_ball is not None else None,
                        "ball_vx": float(tracked_ball.get("vx", 0.0)) if tracked_ball is not None else 0.0,
                        "ball_vy": float(tracked_ball.get("vy", 0.0)) if tracked_ball is not None else 0.0,
                        "ball_radius": float(tracked_ball.get("radius", 0.0)) if tracked_ball is not None else None,
                        "ball_confidence": float(tracked_ball.get("confidence", 0.0)) if tracked_ball is not None else 0.0,
                        "events": dict(seq.events),
                        "coarse_score": float(coarse_score),
                        "lower_body_motion_score": float(lower_body_motion_score),
                        "ball_presence_score": float(ball_presence),
                        "foot_ball_interaction_score": float(foot_ball_interaction),
                        "sequence_activity_score": float(sequence_activity),
                        "center_shift_score": float(center_shift),
                        "contact_signal_score": float(contact_signal),
                    }
                )

                prev_points = current_points
                if tracked_ball is not None:
                    prev_ball = tracked_ball

                frame_idx += 1
        finally:
            pose.close()

        if not samples:
            warnings.append("no_samples")

        if pose_init_warnings:
            warnings.extend(pose_init_warnings)

        if sampled_frame_count <= 0:
            warnings.append("sampled_frame_count_zero")

        if sum(motion_scores) <= 0.01:
            warnings.append("low_motion_signal")

        if not contact_times:
            if ball_visible_frames <= 0:
                warnings.append("ball_evidence_low")
            if low_motion_frames >= max(2, sampled_frame_count // 2):
                warnings.append("low_motion_signal")

        raw_candidates: List[Dict[str, Any]] = []
        if samples:
            coarse_window_size_s = min(2.5, max(1.4, duration_s * 0.12))
            half_window = coarse_window_size_s * 0.5
            for idx, sample in enumerate(samples):
                center_time = float(sample.get("time", 0.0))
                window_samples = [
                    other
                    for other in samples
                    if abs(float(other.get("time", 0.0)) - center_time) <= half_window
                ]
                if not window_samples:
                    continue

                window_score = float(np.mean([float(item.get("coarse_score", 0.0) or 0.0) for item in window_samples]))
                contact_density = float(np.mean([1.0 if item.get("contact") else 0.0 for item in window_samples]))
                ball_density = float(np.mean([1.0 if item.get("ball_present") else 0.0 for item in window_samples]))
                sequence_density = float(np.mean([float(item.get("sequence_activity_score", 0.0) or 0.0) for item in window_samples]))
                motion_density = float(np.mean([float(item.get("lower_body_motion_score", 0.0) or 0.0) for item in window_samples]))
                interaction_density = float(np.mean([float(item.get("foot_ball_interaction_score", 0.0) or 0.0) for item in window_samples]))
                peak_contact = next((item for item in window_samples if item.get("contact")), None)
                peak_ball = max(window_samples, key=lambda item: float(item.get("ball_speed_ratio", 0.0) or 0.0), default=None)
                suspected_contact = None
                if peak_contact is not None:
                    suspected_contact = float(peak_contact.get("time", center_time))
                elif peak_ball is not None and float(peak_ball.get("ball_speed_ratio", 0.0) or 0.0) > 0.08:
                    suspected_contact = float(peak_ball.get("time", center_time))
                elif window_score >= 0.18 and ball_density > 0.15:
                    suspected_contact = center_time

                coarse_confidence = _clamp(
                    0.34 * window_score
                    + 0.20 * contact_density
                    + 0.16 * ball_density
                    + 0.16 * sequence_density
                    + 0.14 * max(motion_density, interaction_density)
                )
                if suspected_contact is None and coarse_confidence < 0.18:
                    continue

                start_s, end_s = build_window_from_contact(
                    suspected_contact if suspected_contact is not None else center_time,
                    duration_s=duration_s,
                    peak_time_s=center_time,
                    pre_buffer_s=0.9,
                    post_buffer_s=1.1,
                    min_duration_s=1.4,
                    max_duration_s=2.8,
                )
                raw_candidates.append(
                    {
                        "start_s": start_s,
                        "end_s": end_s,
                        "contact_time_s": suspected_contact,
                        "peak_time_s": center_time,
                        "score": round(float(window_score), 3),
                        "confidence": round(float(coarse_confidence), 3),
                        "source": "coarse_locator",
                        "reason": "selected_by_motion_ball_sequence",
                        "debug": {
                            "contact_density": round(float(contact_density), 3),
                            "ball_density": round(float(ball_density), 3),
                            "sequence_density": round(float(sequence_density), 3),
                            "motion_density": round(float(motion_density), 3),
                            "interaction_density": round(float(interaction_density), 3),
                            "frame_index": int(sample.get("index", idx)),
                        },
                    }
                )

        normalized = normalize_candidate_windows(raw_candidates, duration_s=duration_s, max_windows=max_windows)
        candidate_windows = [
            {
                "index": index,
                "start_s": round(float(window.start_s), 3),
                "end_s": round(float(window.end_s), 3),
                "duration_s": round(float(window.duration_s), 3),
                "contact_time_s": round(float(window.contact_time_s), 3) if window.contact_time_s is not None else None,
                "peak_time_s": round(float(window.peak_time_s), 3) if window.peak_time_s is not None else None,
                "score": round(float(window.score), 3),
                "confidence": round(float(window.confidence), 3),
                "source": window.source,
                "reason": window.reason,
                "debug": dict(window.debug),
            }
            for index, window in enumerate(normalized)
        ]

        if not candidate_windows:
            if low_motion_frames >= max(3, sampled_frame_count // 2):
                warnings.append("low_motion_signal")
            elif ball_visible_frames <= 0:
                warnings.append("ball_evidence_low")
            else:
                warnings.append("no_action_window_found")

        top_scores = sorted((float(item.get("score", 0.0) or 0.0) for item in candidate_windows), reverse=True)
        score_gap = top_scores[0] - top_scores[1] if len(top_scores) >= 2 else top_scores[0] if top_scores else 0.0
        contact_density = float(contact_frames) / max(1.0, float(sampled_frame_count))
        evidence_density = _clamp(
            0.40 * float(ball_visible_frames) / max(1.0, float(sampled_frame_count))
            + 0.35 * float(sum(1 for score in motion_scores if score > 0.18)) / max(1.0, float(sampled_frame_count))
            + 0.25 * contact_density
        )
        coarse_confidence = _clamp(
            0.42 * (top_scores[0] if top_scores else 0.0)
            + 0.25 * score_gap
            + 0.20 * evidence_density
            + 0.13 * _clamp(float(len(contact_times)) / max(1.0, float(sampled_frame_count) * 0.18))
        )

        coarse_debug = {
            "selected_action": str(selected_action or ""),
            "video_duration": round(float(duration_s), 3),
            "frame_count": int(frame_count),
            "sampled_frame_count": int(sampled_frame_count),
            "target_sample_fps": round(float(target_sample_fps), 3),
            "sample_stride": int(sample_stride),
            "contact_density": round(float(contact_density), 3),
            "evidence_density": round(float(evidence_density), 3),
            "motion_scores": [round(float(value), 3) for value in motion_scores[:20]],
            "ball_presence_scores": [round(float(value), 3) for value in ball_presence_scores[:20]],
            "interaction_scores": [round(float(value), 3) for value in interaction_scores[:20]],
            "sequence_scores": [round(float(value), 3) for value in sequence_scores[:20]],
            "center_shift_scores": [round(float(value), 3) for value in center_shift_scores[:20]],
            "candidate_windows": list(candidate_windows),
            "suspected_contact_times": sorted({round(float(value), 3) for value in contact_times}),
            "warnings": list(dict.fromkeys(warnings)),
        }

        return LongVideoLocatorResult(
            video_opened=True,
            fps=fps,
            frame_count=frame_count,
            duration_s=duration_s,
            sampled_frame_count=sampled_frame_count,
            target_sample_fps=target_sample_fps,
            sample_stride=sample_stride,
            candidate_windows=candidate_windows,
            suspected_contact_times=sorted({round(float(value), 3) for value in contact_times}),
            coarse_confidence=coarse_confidence,
            coarse_debug=coarse_debug,
            warnings=list(dict.fromkeys(warnings)),
        ).to_dict()
    finally:
        cap.release()
