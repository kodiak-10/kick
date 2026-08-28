from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


_RULE_PHASE_MAP = {
    "video_quality_fail": "setup",
    "video_quality_degraded": "setup",
    "pose_presence_low": "setup",
    "visible_frame_ratio_low": "setup",
    "pose_visibility_low": "setup",
    "ball_track_missing_ratio_high": "setup",
    "ball_not_detected": "setup",
    "kick_event_not_detected": "contact",
    "support_foot_too_far": "support",
    "support_foot_too_close": "support",
    "upper_body_back_lean": "contact",
    "follow_through_incomplete": "follow_through",
    "stable_action": "follow_through",
}


def _safe_time(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def locate_error_timestamps(
    *,
    action_name: str,
    triggered_rules: Iterable[Dict[str, Any]] | Iterable[str],
    rule_times: Optional[Dict[str, float]] = None,
    event_times: Optional[Dict[str, float]] = None,
    default_time: float = 0.0,
    trial_scores: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rule_times = rule_times or {}
    event_times = event_times or {}
    error_timestamps: List[Dict[str, Any]] = []

    for item in triggered_rules:
        if isinstance(item, str):
            rule_id = item
            severity = "info"
            reason = ""
        else:
            rule_id = str(item.get("id", "unknown_rule"))
            severity = str(item.get("severity", "info"))
            reason = str(item.get("reason", ""))

        timestamp = rule_times.get(rule_id)
        if timestamp is None:
            if rule_id in {"upper_body_back_lean"}:
                timestamp = event_times.get("contact", default_time)
            elif rule_id in {"follow_through_incomplete", "stable_action"}:
                timestamp = event_times.get("follow_through", event_times.get("contact", default_time))
            elif rule_id in {"support_foot_too_far", "support_foot_too_close"}:
                timestamp = event_times.get("support", default_time)
            else:
                timestamp = event_times.get("contact", default_time)

        error_timestamps.append(
            {
                "rule_id": rule_id,
                "phase": _RULE_PHASE_MAP.get(rule_id, "contact" if action_name else "setup"),
                "time": round(_safe_time(timestamp, default_time), 3),
                "severity": severity,
                "reason": reason,
            }
        )

    error_timestamps.sort(key=lambda item: (item["time"], item["rule_id"]))

    best_trial = None
    worst_trial = None
    if trial_scores:
        ordered = [item for item in trial_scores if isinstance(item, dict) and "score" in item]
        if ordered:
            ordered.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
            best_trial = dict(ordered[0])
            worst_trial = dict(ordered[-1])

    return {
        "error_timestamps": error_timestamps,
        "best_trial": best_trial,
        "worst_trial": worst_trial,
    }
