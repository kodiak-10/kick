from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _mean(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(v) for v in values if v is not None]
    return float(sum(items) / len(items)) if items else float(default)


def _min(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(v) for v in values if v is not None]
    return float(min(items)) if items else float(default)


def _max(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(v) for v in values if v is not None]
    return float(max(items)) if items else float(default)


def _band_score(value: float, ideal_low: float, ideal_high: float, worst_low: float, worst_high: float) -> float:
    value = float(value)
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        if value <= worst_low:
            return 0.0
        return _clamp((value - worst_low) / max(1e-6, ideal_low - worst_low))
    if value >= worst_high:
        return 0.0
    return _clamp((worst_high - value) / max(1e-6, worst_high - ideal_high))


def _sequence_lookup(run_data: Dict[str, Any]) -> Dict[str, Any]:
    sequence_snapshot = dict(run_data.get("sequence_snapshot") or {})
    sequence_label = str(run_data.get("sequence_action_label") or sequence_snapshot.get("action_label") or "soccer_idle")
    return {
        "sequence_label": sequence_label,
        "sequence_confidence": float(sequence_snapshot.get("phase_confidence", 0.0) or 0.0),
        "sequence_active": bool(sequence_snapshot.get("sequence_active")),
        "sequence_ready": bool(sequence_snapshot.get("sequence_ready")),
        "phase_locked": bool(sequence_snapshot.get("phase_locked")),
        "events": dict(sequence_snapshot.get("events") or {}),
    }


def _collect_windows(samples: Sequence[Dict[str, Any]], fps: float) -> Dict[str, Any]:
    total = len(samples)
    contact_indices = [idx for idx, sample in enumerate(samples) if bool((sample.get("events") or {}).get("contact", False))]
    support_indices = [idx for idx, sample in enumerate(samples) if bool((sample.get("events") or {}).get("support_plant", False))]
    follow_indices = [idx for idx, sample in enumerate(samples) if bool((sample.get("events") or {}).get("follow_through_complete", False))]
    complete_indices = [idx for idx, sample in enumerate(samples) if bool((sample.get("events") or {}).get("sequence_complete", False))]

    peak_ball_idx = max(range(total), key=lambda idx: float(samples[idx].get("ball_speed_ratio", 0.0) or 0.0), default=None)
    if peak_ball_idx is not None and float(samples[peak_ball_idx].get("ball_speed_ratio", 0.0) or 0.0) <= 0.0:
        peak_ball_idx = None

    if contact_indices:
        center_idx = contact_indices[0]
    elif peak_ball_idx is not None:
        center_idx = peak_ball_idx
    elif support_indices:
        center_idx = support_indices[0]
    else:
        center_idx = total // 2 if total else 0

    window_frames = max(30, int(round(max(1.0, fps) * 1.5)))
    pre_start = max(0, center_idx - window_frames)
    post_end = min(total - 1, center_idx + window_frames) if total else 0
    focus_indices = list(range(pre_start, post_end + 1)) if total else []
    pre_indices = list(range(pre_start, center_idx + 1)) if total else []
    post_indices = list(range(center_idx, post_end + 1)) if total else []

    return {
        "contact_indices": contact_indices,
        "support_indices": support_indices,
        "follow_indices": follow_indices,
        "complete_indices": complete_indices,
        "peak_ball_idx": peak_ball_idx,
        "center_idx": center_idx,
        "window_frames": window_frames,
        "focus_indices": focus_indices,
        "pre_indices": pre_indices,
        "post_indices": post_indices,
    }


def _sample_times(samples: Sequence[Dict[str, Any]], indices: Sequence[int]) -> List[float]:
    return [float(samples[idx].get("time", 0.0)) for idx in indices if 0 <= idx < len(samples)]


def _frame_timespan(samples: Sequence[Dict[str, Any]], indices: Sequence[int]) -> float:
    times = _sample_times(samples, indices)
    if len(times) < 2:
        return 0.0
    return max(0.0, times[-1] - times[0])


def _ball_track(samples: Sequence[Dict[str, Any]], indices: Sequence[int]) -> Dict[str, Any]:
    track_samples = [samples[idx] for idx in indices if 0 <= idx < len(samples) and bool(samples[idx].get("ball_present", False))]
    if not track_samples:
        return {
            "start": None,
            "end": None,
            "delta_x": 0.0,
            "delta_y": 0.0,
            "path_length": 0.0,
            "path_speed": 0.0,
            "horizontal_bias": 0.0,
            "goalward_bias": 0.0,
            "ball_speed_peak": 0.0,
            "ball_speed_mean": 0.0,
            "ball_track_count": 0,
        }

    start = track_samples[0]
    end = track_samples[-1]
    start_x = float(start.get("ball_x", 0.0) or 0.0)
    start_y = float(start.get("ball_y", 0.0) or 0.0)
    end_x = float(end.get("ball_x", start_x) or start_x)
    end_y = float(end.get("ball_y", start_y) or start_y)
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    path_length = 0.0
    prev_x = start_x
    prev_y = start_y
    for sample in track_samples[1:]:
        x = float(sample.get("ball_x", prev_x) or prev_x)
        y = float(sample.get("ball_y", prev_y) or prev_y)
        path_length += sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
        prev_x = x
        prev_y = y

    ball_speeds = [float(sample.get("ball_speed_ratio", 0.0) or 0.0) for sample in track_samples]
    span_px = max(1.0, float(max(float(sample.get("body_span", 1.0) or 1.0) for sample in track_samples)))
    path_speed = path_length / max(1.0, float(len(track_samples)))
    horizontal_bias = abs(delta_x) / max(1e-6, abs(delta_y))
    goalward_bias = _clamp(max(0.0, -delta_y) / max(1e-6, abs(delta_x) + abs(delta_y)))

    return {
        "start": start,
        "end": end,
        "delta_x": float(delta_x),
        "delta_y": float(delta_y),
        "path_length": float(path_length),
        "path_speed": float(path_speed / span_px),
        "horizontal_bias": float(horizontal_bias),
        "goalward_bias": float(goalward_bias),
        "ball_speed_peak": float(max(ball_speeds) if ball_speeds else 0.0),
        "ball_speed_mean": float(_mean(ball_speeds, default=0.0)),
        "ball_track_count": int(len(track_samples)),
    }


def _goal_visible_from_samples(samples: Sequence[Dict[str, Any]]) -> bool:
    return any(bool(sample.get("goal_visible", False)) for sample in samples)


def _confidence_reasons(
    *,
    confidence: float,
    confidence_gap: float,
    goal_visible: bool,
    pose_frames: int,
    ball_frames: int,
    total_frames: int,
    duration_s: float,
    stage1_label: str,
    top_label: str,
    second_label: str,
    pass_score: float,
    shot_score: float,
) -> List[str]:
    reasons: List[str] = []
    if pose_frames < max(4, int(total_frames * 0.18)):
        reasons.append("no_pose")
    if ball_frames < max(2, int(total_frames * 0.08)):
        reasons.append("ball_unstable")
    if duration_s < 1.5 or total_frames < 45:
        reasons.append("short_clip")
    if not goal_visible and top_label in {"shot", "clearance"}:
        reasons.append("goal_not_visible")
    if confidence < 0.60:
        reasons.append("low_confidence")
    if confidence_gap < 0.15 and {top_label, second_label} <= {"pass", "shot"}:
        reasons.append("ambiguous_pass_shot")
    elif confidence_gap < 0.15:
        reasons.append("ambiguous_action")
    if stage1_label != "kick" and confidence < 0.80:
        reasons.append("kick_stage_uncertain")
    if abs(pass_score - shot_score) < 0.12:
        reasons.append("ambiguous_pass_shot")
    return reasons


def _display_name(action_label: str) -> str:
    return {
        "kick": "踢球动作",
        "non_kick": "非踢球",
        "pass": "传球",
        "shot": "射门",
        "first_touch": "停球",
        "clearance": "解围",
        "long_ball": "长传",
        "uncertain": "动作待确认",
        "pending_confirmation": "动作待确认",
    }.get(action_label, action_label or "动作待确认")


def _template_for_label(action_label: str, ball_speed_peak: float = 0.0) -> str:
    if action_label == "pass":
        return "short_pass"
    if action_label == "shot":
        return "shot_instep"
    if action_label == "first_touch":
        return "receive_control"
    if action_label == "clearance":
        return "shot_instep" if ball_speed_peak >= 0.18 else "short_pass"
    if action_label == "long_ball":
        return "short_pass"
    if action_label == "non_kick":
        return "short_pass"
    return "short_pass"


def _legacy_action_alias(action_label: str) -> str:
    return {
        "pass": "pass_like",
        "shot": "shoot_like",
        "first_touch": "first_touch_like",
        "clearance": "shoot_like",
        "long_ball": "pass_like",
        "non_kick": "soccer_idle",
        "uncertain": "uncertain",
        "pending_confirmation": "uncertain",
    }.get(action_label, action_label or "uncertain")


def _route_template(label: str, ball_speed_peak: float, goal_visible: bool) -> str:
    if label == "shot":
        return "shot_instep"
    if label == "pass":
        return "short_pass"
    if label == "first_touch":
        return "receive_control"
    if label == "clearance":
        return "shot_instep" if ball_speed_peak >= 0.18 or not goal_visible else "short_pass"
    if label == "long_ball":
        return "short_pass"
    if label == "non_kick":
        return "short_pass"
    return "short_pass"


def _candidate_entry(label: str, score: float, sources: List[str], *, ball_speed_peak: float, goal_visible: bool) -> Dict[str, Any]:
    template = _template_for_label(label, ball_speed_peak=ball_speed_peak)
    return {
        "label": label,
        "action": label,
        "display_name": _display_name(label),
        "score": round(float(_clamp(score)), 3),
        "sources": list(sources),
        "template": template,
        "route_template": _route_template(label, ball_speed_peak, goal_visible),
    }


def build_video_action_decision(run_data: Dict[str, Any], metrics: Dict[str, float], evidence: Dict[str, float]) -> Dict[str, Any]:
    samples = list(run_data.get("samples") or [])
    fps = float(run_data.get("fps", 30.0) or 30.0)
    total_frames = len(samples)
    duration_s = float(run_data.get("frame_count", total_frames) or 0.0) / fps if fps > 0.0 else 0.0
    window = _collect_windows(samples, fps)
    sequence = _sequence_lookup(run_data)
    goal_visible = _goal_visible_from_samples(samples)

    pose_frames = int(evidence.get("pose_frames", 0) or 0)
    ball_frames = int(evidence.get("ball_frames", 0) or 0)
    analysis_confidence = float(evidence.get("analysis_confidence", 0.0) or 0.0)

    contact_indices = window["contact_indices"]
    support_indices = window["support_indices"]
    focus_indices = window["focus_indices"]
    pre_indices = window["pre_indices"]
    post_indices = window["post_indices"]
    center_idx = int(window["center_idx"])

    focus_samples = [samples[idx] for idx in focus_indices if 0 <= idx < total_frames]
    pre_samples = [samples[idx] for idx in pre_indices if 0 <= idx < total_frames]
    post_samples = [samples[idx] for idx in post_indices if 0 <= idx < total_frames]
    support_samples = [samples[idx] for idx in support_indices if 0 <= idx < total_frames]

    ball_track = _ball_track(samples, focus_indices)
    ball_speed_peak = max(
        ball_track["ball_speed_peak"],
        _max((float(sample.get("ball_speed_ratio", 0.0) or 0.0) for sample in focus_samples), default=0.0),
    )
    ball_speed_mean = _mean((float(sample.get("ball_speed_ratio", 0.0) or 0.0) for sample in focus_samples), default=0.0)
    support_min = _min((float(sample.get("support_ball_ratio", 0.28) or 0.28) for sample in focus_samples), default=float(metrics.get("support_ball_ratio", 0.28)))
    swing_peak = _max((float(sample.get("swing_ball_ratio", 0.16) or 0.16) for sample in focus_samples), default=float(metrics.get("swing_ball_ratio", 0.16)))
    support_speed = _mean((float(sample.get("support_speed_ratio", metrics.get("support_speed_ratio", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("support_speed_ratio", 0.0)))
    swing_speed = _mean((float(sample.get("swing_speed_ratio", metrics.get("swing_speed_ratio", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("swing_speed_ratio", 0.0)))
    phase_confidence = _mean((float(sample.get("phase_confidence", 0.0) or 0.0) for sample in focus_samples), default=float(metrics.get("sequence_confidence", 0.0)))
    visibility = _mean((float(sample.get("visibility", 0.0) or 0.0) for sample in focus_samples), default=float(metrics.get("visibility", 0.0)))
    stability = _mean((float(sample.get("stability", metrics.get("stability", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("stability", 0.0)))
    move_ratio = _mean((float(sample.get("move_ratio", metrics.get("move_ratio", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("move_ratio", 0.0)))
    trunk_lean = _max((float(sample.get("trunk_lean_deg", metrics.get("trunk_lean_deg", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("trunk_lean_deg", 0.0)))
    balance = _max((float(sample.get("balance", metrics.get("balance", 0.0)) or 0.0) for sample in focus_samples), default=float(metrics.get("balance", 0.0)))
    sequence_ready_ratio = _mean((1.0 if bool(sample.get("sequence_ready", False)) else 0.0 for sample in focus_samples), default=0.0)
    contact_evidence = 1.0 if contact_indices else _clamp(ball_speed_peak * 2.4 + swing_peak * 1.6)
    ball_presence = _clamp(ball_frames / max(1.0, float(total_frames)))
    motion_evidence = _clamp(0.40 * ball_speed_peak + 0.30 * swing_peak + 0.18 * sequence["sequence_confidence"] + 0.12 * ball_presence)

    stage1_kick_score = _clamp(
        0.32 * contact_evidence
        + 0.26 * motion_evidence
        + 0.18 * _clamp(max(swing_speed, move_ratio * 2.0))
        + 0.14 * ball_presence
        + 0.10 * _clamp(sequence["sequence_confidence"])
    )
    stage1_label = "kick" if stage1_kick_score >= 0.45 else "non_kick"
    stage1_confidence = stage1_kick_score if stage1_label == "kick" else 1.0 - stage1_kick_score

    direction_span = max(1.0, float(metrics.get("body_span_px", 1.0) or 1.0))
    direction_score = _clamp(ball_track["path_speed"] / 0.22)
    lateral_bias = _clamp(ball_track["horizontal_bias"] / 2.4)
    goalward_bias = _clamp(ball_track["goalward_bias"])
    support_balance = _clamp(1.0 - abs(support_min - 0.24) / 0.20)
    support_offset = _clamp(1.0 - abs(float(metrics.get("support_ball_ratio", support_min)) - 0.24) / 0.20)
    ball_speed_score = _clamp((ball_speed_peak - 0.05) / 0.26)
    shot_speed_score = _clamp((ball_speed_peak - 0.11) / 0.22)
    pass_speed_score = _clamp(1.0 - abs(ball_speed_peak - 0.13) / 0.11)
    first_touch_speed_score = _clamp(1.0 - ball_speed_peak / 0.16)
    clear_speed_score = _clamp((ball_speed_peak - 0.14) / 0.20)
    long_ball_speed_score = _clamp((ball_speed_peak - 0.09) / 0.18)
    control_stability = _clamp(0.40 * stability + 0.25 * sequence_ready_ratio + 0.20 * visibility + 0.15 * ball_presence)
    open_body_score = _clamp(1.0 - abs(balance) / 0.22)
    swing_score = _clamp((swing_peak - 0.03) / 0.16)
    follow_through_score = _clamp(0.50 * swing_score + 0.25 * motion_evidence + 0.25 * _clamp((phase_confidence + sequence["sequence_confidence"]) * 0.5))

    temporal_prediction = dict(run_data.get("temporal_best_prediction") or {})
    temporal_features = dict(temporal_prediction.get("features") or {})
    temporal_pass = float(temporal_features.get("pass_score", 0.0) or 0.0)
    temporal_shot = float(temporal_features.get("shoot_score", 0.0) or 0.0)
    temporal_first_touch = float(temporal_features.get("first_touch_score", 0.0) or 0.0)
    temporal_label = str(temporal_prediction.get("label") or "").strip()
    temporal_confidence = float(temporal_prediction.get("confidence", 0.0) or 0.0)

    kick_bonus = _clamp(stage1_kick_score - 0.45)
    pass_score = _clamp(
        0.20 * pass_speed_score
        + 0.18 * lateral_bias
        + 0.16 * support_balance
        + 0.12 * (1.0 - goalward_bias)
        + 0.10 * (1.0 - _clamp(ball_speed_peak / 0.24))
        + 0.10 * control_stability
        + 0.08 * open_body_score
        + 0.06 * temporal_pass
        + 0.05 * _clamp(1.0 - shot_speed_score)
    )
    shot_score = _clamp(
        0.24 * shot_speed_score
        + 0.20 * swing_score
        + 0.18 * goalward_bias
        + 0.12 * (1.0 if goal_visible else 0.10)
        + 0.10 * support_offset
        + 0.08 * open_body_score
        + 0.06 * temporal_shot
        + 0.02 * ball_speed_score
    )
    if goal_visible:
        shot_score = _clamp(shot_score + 0.08)
    if not goal_visible:
        shot_score = _clamp(shot_score - 0.04)
    if ball_speed_peak < 0.10:
        shot_score = _clamp(shot_score - 0.12)
    if ball_speed_peak > 0.24:
        pass_score = _clamp(pass_score - 0.10)
    if abs(ball_track["delta_y"]) < abs(ball_track["delta_x"]) * 0.55:
        pass_score = _clamp(pass_score + 0.06)
    if goalward_bias < 0.25:
        shot_score = _clamp(shot_score - 0.08)

    first_touch_score = _clamp(
        0.24 * contact_evidence
        + 0.18 * first_touch_speed_score
        + 0.18 * control_stability
        + 0.14 * _clamp(1.0 - swing_score)
        + 0.12 * _clamp(1.0 - ball_speed_peak / 0.16)
        + 0.08 * temporal_first_touch
        + 0.06 * sequence_ready_ratio
    )
    if ball_speed_peak > 0.12:
        first_touch_score = _clamp(first_touch_score - 0.08)

    clearance_score = _clamp(
        0.22 * clear_speed_score
        + 0.18 * swing_score
        + 0.14 * _clamp(1.0 - goal_visible)
        + 0.14 * _clamp(1.0 - goalward_bias)
        + 0.12 * open_body_score
        + 0.10 * control_stability
        + 0.06 * temporal_shot
        + 0.04 * ball_speed_score
    )
    if goal_visible:
        clearance_score = _clamp(clearance_score - 0.08)

    long_ball_score = _clamp(
        0.22 * long_ball_speed_score
        + 0.16 * lateral_bias
        + 0.14 * support_balance
        + 0.14 * _clamp(1.0 - goal_visible)
        + 0.12 * control_stability
        + 0.10 * temporal_pass
        + 0.08 * direction_score
        + 0.04 * kick_bonus
    )
    if ball_speed_peak > 0.22 and goal_visible:
        long_ball_score = _clamp(long_ball_score - 0.08)

    if stage1_label == "non_kick":
        non_kick_score = _clamp(0.82 + 0.10 * (1.0 - stage1_kick_score))
        kick_score = _clamp(1.0 - non_kick_score)
    else:
        non_kick_score = _clamp(1.0 - stage1_kick_score)
        kick_score = _clamp(stage1_kick_score)

    semantic_raw = {
        "pass": pass_score,
        "shot": shot_score,
        "first_touch": first_touch_score,
        "clearance": clearance_score,
        "long_ball": long_ball_score,
    }
    if stage1_label == "non_kick":
        semantic_raw["non_kick"] = non_kick_score

    ordered_candidates = sorted(semantic_raw.items(), key=lambda item: (-float(item[1]), str(item[0])))
    top_label, top_score = ordered_candidates[0]
    second_label, second_score = ordered_candidates[1] if len(ordered_candidates) > 1 else ("", 0.0)
    confidence = _clamp(float(top_score))
    confidence_gap = _clamp(float(top_score) - float(second_score))

    needs_confirmation = confidence < 0.60 or confidence_gap < 0.15
    if stage1_label == "kick" and top_label == "non_kick":
        needs_confirmation = True
    if top_label in {"pass", "shot"} and confidence_gap < 0.20:
        needs_confirmation = True

    uncertainty_reasons = _confidence_reasons(
        confidence=confidence,
        confidence_gap=confidence_gap,
        goal_visible=goal_visible,
        pose_frames=pose_frames,
        ball_frames=ball_frames,
        total_frames=total_frames,
        duration_s=duration_s,
        stage1_label=stage1_label,
        top_label=top_label,
        second_label=second_label,
        pass_score=pass_score,
        shot_score=shot_score,
    )

    candidate_scores = {
        "non_kick": round(float(non_kick_score), 3),
        "kick": round(float(kick_score), 3),
        "pass": round(float(pass_score), 3),
        "shot": round(float(shot_score), 3),
        "first_touch": round(float(first_touch_score), 3),
        "clearance": round(float(clearance_score), 3),
        "long_ball": round(float(long_ball_score), 3),
        "pass_like": round(float(pass_score), 3),
        "shoot_like": round(float(shot_score), 3),
        "shot_like": round(float(shot_score), 3),
        "first_touch_like": round(float(first_touch_score), 3),
    }

    display_candidates = [_candidate_entry(label, score, [f"stage2.{label}"], ball_speed_peak=ball_speed_peak, goal_visible=goal_visible) for label, score in ordered_candidates if score > 0.0]
    if not display_candidates:
        display_candidates = [_candidate_entry("non_kick", 1.0, ["fallback"], ball_speed_peak=ball_speed_peak, goal_visible=goal_visible)]

    semantic_action_label = "uncertain" if needs_confirmation else top_label
    if semantic_action_label not in {"pass", "shot", "first_touch", "clearance", "long_ball", "non_kick"}:
        semantic_action_label = "uncertain"

    if semantic_action_label == "uncertain":
        action_display_name = "动作待确认"
    else:
        action_display_name = _display_name(semantic_action_label)

    if semantic_action_label == "uncertain":
        recommended_template = _route_template(top_label if top_label in semantic_raw else "pass", ball_speed_peak, goal_visible)
    else:
        recommended_template = _route_template(semantic_action_label, ball_speed_peak, goal_visible)

    if top_label == "shot" and not goal_visible and confidence < 0.75:
        recommended_template = "short_pass"

    detected_action = semantic_action_label
    final_detected_action = semantic_action_label
    raw_detected_action = _legacy_action_alias(top_label if not needs_confirmation else semantic_action_label)

    return {
        "stage1_action_label": stage1_label,
        "stage1_confidence": round(float(stage1_confidence), 3),
        "action_label": semantic_action_label,
        "action_display_name": action_display_name,
        "action_candidates": display_candidates,
        "confidence": round(float(confidence), 3),
        "confidence_gap": round(float(confidence_gap), 3),
        "needs_confirmation": bool(needs_confirmation),
        "uncertainty_reasons": list(dict.fromkeys(uncertainty_reasons)),
        "goal_visible": bool(goal_visible),
        "kick_score": round(float(kick_score), 3),
        "non_kick_score": round(float(non_kick_score), 3),
        "pass_score": round(float(pass_score), 3),
        "shot_score": round(float(shot_score), 3),
        "first_touch_score": round(float(first_touch_score), 3),
        "clearance_score": round(float(clearance_score), 3),
        "long_ball_score": round(float(long_ball_score), 3),
        "candidate_scores": candidate_scores,
        "raw_action_candidates": [
            {
                "action": item["label"],
                "score": item["score"],
                "sources": list(item["sources"]),
            }
            for item in display_candidates
        ],
        "raw_detected_action": raw_detected_action,
        "detected_action": detected_action,
        "final_detected_action": final_detected_action,
        "mapped_rule_key": recommended_template,
        "final_mapped_rule_key": recommended_template,
        "recommended_template": recommended_template,
        "analyzer_used": {
            "short_pass": "short_pass_analyzer_v1",
            "shot_instep": "shot_instep_analyzer_v1",
            "receive_control": "receive_control_analyzer_v1",
        }.get(recommended_template, "video_analysis_router_v1"),
        "whether_fallback_template_used": bool(needs_confirmation or semantic_action_label == "uncertain"),
        "fallback_used": bool(needs_confirmation or semantic_action_label == "uncertain"),
        "detection_source": "rule_based_temporal_kick_v2",
        "sequence_context": {
            **sequence,
            "goal_visible": bool(goal_visible),
            "window_frames": window["window_frames"],
            "center_idx": center_idx,
            "ball_track": ball_track,
        },
    }
