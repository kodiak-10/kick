from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class FootballKinematics:
    left_foot_speed_px: float
    right_foot_speed_px: float
    support_side: str
    swing_side: str
    support_speed_ratio: float
    swing_speed_ratio: float
    support_ball_ratio: float
    swing_ball_ratio: float
    ball_speed_ratio: float
    motion_ratio: float
    contact: bool
    contact_side: str


@dataclass(frozen=True)
class FootballSequenceSnapshot:
    phase: str
    phase_confidence: float
    phase_locked: bool
    sequence_active: bool
    sequence_ready: bool
    action_label: str
    support_side: str
    swing_side: str
    events: Dict[str, bool]
    metrics: Dict[str, float]


def fresh_sequence_state() -> Dict[str, object]:
    return {
        "phase": "set",
        "candidate_phase": "set",
        "candidate_frames": 0,
        "contact_seen": False,
        "sequence_active": False,
        "action_started_at": 0.0,
        "last_contact_time": 0.0,
        "last_complete_time": 0.0,
        "support_side": "none",
        "swing_side": "none",
    }


def compute_football_kinematics(
    points: Dict[str, Tuple[float, float]],
    prev_points: Optional[Dict[str, Tuple[float, float]]],
    ball: Optional[Dict[str, float]],
    prev_ball: Optional[Dict[str, float]],
    contact: Dict[str, object],
    body_span_px: float,
    move_ratio: float,
) -> FootballKinematics:
    span = max(1.0, float(body_span_px))
    if prev_points is None:
        left_speed = 0.0
        right_speed = 0.0
    else:
        left_dx = points["left_ankle"][0] - prev_points["left_ankle"][0]
        left_dy = points["left_ankle"][1] - prev_points["left_ankle"][1]
        right_dx = points["right_ankle"][0] - prev_points["right_ankle"][0]
        right_dy = points["right_ankle"][1] - prev_points["right_ankle"][1]
        left_speed = float((left_dx * left_dx + left_dy * left_dy) ** 0.5)
        right_speed = float((right_dx * right_dx + right_dy * right_dy) ** 0.5)

    swing_side = "right" if right_speed >= left_speed else "left"
    support_side = "left" if swing_side == "right" else "right"
    swing_speed = right_speed if swing_side == "right" else left_speed
    support_speed = left_speed if support_side == "left" else right_speed

    support_ball_ratio = 0.28
    swing_ball_ratio = 0.16
    if ball is not None:
        sx, sy = points[f"{support_side}_ankle"]
        wx, wy = points[f"{swing_side}_ankle"]
        support_ball_ratio = float((((sx - float(ball["x"])) ** 2 + (sy - float(ball["y"])) ** 2) ** 0.5) / span)
        swing_ball_ratio = float((((wx - float(ball["x"])) ** 2 + (wy - float(ball["y"])) ** 2) ** 0.5) / span)

    ball_speed_ratio = 0.0
    if ball is not None and prev_ball is not None:
        bdx = float(ball["x"]) - float(prev_ball["x"])
        bdy = float(ball["y"]) - float(prev_ball["y"])
        ball_speed_ratio = float(((bdx * bdx + bdy * bdy) ** 0.5) / span)

    return FootballKinematics(
        left_foot_speed_px=left_speed,
        right_foot_speed_px=right_speed,
        support_side=support_side,
        swing_side=swing_side,
        support_speed_ratio=float(support_speed / span),
        swing_speed_ratio=float(swing_speed / span),
        support_ball_ratio=support_ball_ratio,
        swing_ball_ratio=swing_ball_ratio,
        ball_speed_ratio=ball_speed_ratio,
        motion_ratio=float(move_ratio),
        contact=bool(contact.get("contact", False)),
        contact_side=str(contact.get("side", "none")),
    )


def _candidate_phase(kin: FootballKinematics, state: Dict[str, object], now_t: float) -> Tuple[str, float]:
    recently_contacted = float(now_t) - float(state.get("last_contact_time", 0.0)) < 0.45

    if kin.contact:
        return "contact", 0.96
    if recently_contacted and kin.ball_speed_ratio > 0.08:
        return "follow_through", min(0.98, 0.58 + 1.15 * kin.ball_speed_ratio)
    if (
        kin.support_ball_ratio >= 0.08
        and kin.support_ball_ratio <= 0.42
        and kin.support_speed_ratio <= 0.030
        and kin.swing_speed_ratio >= 0.040
    ):
        return "support", min(0.95, 0.46 + 4.8 * kin.swing_speed_ratio)
    if kin.swing_speed_ratio >= 0.032 and (kin.swing_ball_ratio <= 0.38 or kin.motion_ratio >= 0.020):
        return "approach", min(0.90, 0.36 + 5.5 * kin.swing_speed_ratio)
    if recently_contacted:
        return "recovery", 0.72
    if kin.motion_ratio >= 0.014:
        return "preparation", min(0.82, 0.32 + 8.0 * kin.motion_ratio)
    return "set", 0.62


def _action_label_from_kinematics(kin: FootballKinematics, state: Dict[str, object]) -> str:
    if kin.ball_speed_ratio >= 0.19 or kin.swing_speed_ratio >= 0.11:
        return "shoot_like"
    if kin.contact or kin.ball_speed_ratio >= 0.05 or bool(state.get("contact_seen", False)):
        return "pass_like"
    return "soccer_idle"


def update_football_sequence(state: Dict[str, object], kin: FootballKinematics, now_t: float) -> FootballSequenceSnapshot:
    prev_phase = str(state.get("phase", "set"))
    candidate, candidate_conf = _candidate_phase(kin, state, now_t)

    if candidate == state.get("candidate_phase"):
        state["candidate_frames"] = int(state.get("candidate_frames", 0)) + 1
    else:
        state["candidate_phase"] = candidate
        state["candidate_frames"] = 1

    switch_threshold = 1 if candidate_conf >= 0.90 else 2
    phase = prev_phase
    if int(state["candidate_frames"]) >= switch_threshold:
        phase = candidate
        state["phase"] = phase

    phase_locked = int(state.get("candidate_frames", 0)) >= 2 or candidate_conf >= 0.90
    events = {
        "support_plant": False,
        "contact": False,
        "follow_through_complete": False,
        "sequence_complete": False,
    }

    if phase in {"approach", "support", "contact", "follow_through", "recovery"} and not bool(state.get("sequence_active", False)):
        state["sequence_active"] = True
        state["action_started_at"] = float(now_t)

    if phase == "support" and prev_phase != "support":
        events["support_plant"] = True

    if kin.contact and (float(now_t) - float(state.get("last_contact_time", 0.0))) > 0.18:
        events["contact"] = True
        state["contact_seen"] = True
        state["last_contact_time"] = float(now_t)

    if prev_phase == "follow_through" and phase in {"recovery", "set"} and bool(state.get("contact_seen", False)):
        events["follow_through_complete"] = True

    if bool(state.get("contact_seen", False)):
        if phase in {"recovery", "set"} and (float(now_t) - float(state.get("last_contact_time", 0.0))) > 0.16:
            events["sequence_complete"] = True
            state["sequence_active"] = False
            state["contact_seen"] = False
            state["last_complete_time"] = float(now_t)
            state["action_started_at"] = 0.0

    action_label = _action_label_from_kinematics(kin, state)
    state["support_side"] = kin.support_side
    state["swing_side"] = kin.swing_side

    sequence_ready = bool(state.get("sequence_active", False)) and phase_locked and phase in {
        "support",
        "contact",
        "follow_through",
        "recovery",
    }

    metrics = {
        "support_speed_ratio": kin.support_speed_ratio,
        "swing_speed_ratio": kin.swing_speed_ratio,
        "support_ball_ratio": kin.support_ball_ratio,
        "swing_ball_ratio": kin.swing_ball_ratio,
        "ball_speed_ratio": kin.ball_speed_ratio,
        "motion_ratio": kin.motion_ratio,
    }
    return FootballSequenceSnapshot(
        phase=phase,
        phase_confidence=float(candidate_conf),
        phase_locked=phase_locked,
        sequence_active=bool(state.get("sequence_active", False)),
        sequence_ready=sequence_ready,
        action_label=action_label,
        support_side=kin.support_side,
        swing_side=kin.swing_side,
        events=events,
        metrics=metrics,
    )
