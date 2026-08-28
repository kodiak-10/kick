from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass(frozen=True)
class TemporalActionPrediction:
    label: str
    confidence: float
    source: str
    features: Dict[str, float]


def fresh_temporal_classifier_state(window: int = 24) -> Dict[str, object]:
    return {
        "buffer": deque(maxlen=window),
        "label_hist": deque(maxlen=6),
    }


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _majority(labels: Deque[str], default: str = "soccer_idle") -> str:
    if not labels:
        return default
    counts: Dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def update_temporal_classifier(state: Dict[str, object], sequence_snapshot, kin, now_t: float) -> TemporalActionPrediction:
    buffer = state["buffer"]
    if not sequence_snapshot.sequence_active and sequence_snapshot.phase == "set":
        buffer.clear()
        state["label_hist"].clear()
        return TemporalActionPrediction("soccer_idle", 0.20, "temporal", {"evidence": 0.0})

    buffer.append(
        {
            "t": float(now_t),
            "phase": sequence_snapshot.phase,
            "contact": 1.0 if kin.contact else 0.0,
            "ball_speed_ratio": float(kin.ball_speed_ratio),
            "swing_speed_ratio": float(kin.swing_speed_ratio),
            "support_speed_ratio": float(kin.support_speed_ratio),
            "support_ball_ratio": float(kin.support_ball_ratio),
            "swing_ball_ratio": float(kin.swing_ball_ratio),
            "phase_confidence": float(sequence_snapshot.phase_confidence),
        }
    )
    if len(buffer) < 4:
        return TemporalActionPrediction(sequence_snapshot.action_label, 0.28, "temporal_bootstrap", {"evidence": float(len(buffer)) / 4.0})

    recent = list(buffer)
    contact_count = sum(item["contact"] for item in recent)
    peak_ball_release = max(item["ball_speed_ratio"] for item in recent)
    peak_swing = max(item["swing_speed_ratio"] for item in recent)
    mean_phase_conf = sum(item["phase_confidence"] for item in recent) / len(recent)
    min_support_dist = min(item["support_ball_ratio"] for item in recent)
    min_swing_dist = min(item["swing_ball_ratio"] for item in recent)
    close_control_ratio = sum(1.0 for item in recent if item["ball_speed_ratio"] < 0.08) / len(recent)

    pass_score = _clamp(
        0.24 * _clamp((peak_ball_release - 0.05) / 0.14)
        + 0.24 * _clamp((peak_swing - 0.04) / 0.08)
        + 0.22 * _clamp(1.0 - abs(min_support_dist - 0.24) / 0.18)
        + 0.14 * _clamp(contact_count)
        + 0.12 * mean_phase_conf
    )
    shoot_score = _clamp(
        0.40 * _clamp((peak_ball_release - 0.10) / 0.22)
        + 0.30 * _clamp((peak_swing - 0.06) / 0.09)
        + 0.18 * _clamp(contact_count)
        + 0.10 * _clamp(1.0 - min_support_dist / 0.42)
        + 0.10 * mean_phase_conf
    )
    if peak_ball_release > 0.20:
        pass_score *= 0.88
        shoot_score = _clamp(shoot_score + 0.08)
    first_touch_score = _clamp(
        0.30 * _clamp(contact_count)
        + 0.24 * close_control_ratio
        + 0.22 * _clamp(1.0 - peak_ball_release / 0.16)
        + 0.14 * _clamp(1.0 - min_swing_dist / 0.24)
        + 0.10 * mean_phase_conf
    )

    scores = {
        "pass_like": pass_score,
        "shoot_like": shoot_score,
        "first_touch_like": first_touch_score,
    }
    top = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    label, best = top[0]
    second = top[1][1]
    evidence = _clamp(0.55 * mean_phase_conf + 0.45 * min(1.0, len(recent) / 12.0))
    confidence = _clamp(0.58 * best + 0.22 * (best - second + 0.2) + 0.20 * evidence)
    if best < 0.42:
        label = sequence_snapshot.action_label
        confidence = max(0.24, confidence * 0.72)

    state["label_hist"].append(label)
    stable_label = _majority(state["label_hist"], label)
    if stable_label != label:
        confidence *= 0.92

    return TemporalActionPrediction(
        label=stable_label,
        confidence=confidence,
        source="temporal",
        features={
            "contact_count": float(contact_count),
            "peak_ball_release": float(peak_ball_release),
            "peak_swing_speed": float(peak_swing),
            "mean_phase_confidence": float(mean_phase_conf),
            "support_ball_ratio_min": float(min_support_dist),
            "swing_ball_ratio_min": float(min_swing_dist),
            "pass_score": float(pass_score),
            "shoot_score": float(shoot_score),
            "first_touch_score": float(first_touch_score),
        },
    )
