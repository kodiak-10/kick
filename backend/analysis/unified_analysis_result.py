from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def normalize_failure_reason(reason: Any) -> str:
    text = str(reason or "").strip().lower()
    if not text:
        return ""
    aliases = {
        "video_too_long": "video_too_long",
        "analysis_timeout": "analysis_timeout",
        "unsupported_action": "unsupported_action",
        "route_mismatch": "route_mismatch",
        "video_open_failed": "video_open_failed",
        "mediapipe_pose_init_failed": "mediapipe_pose_init_failed",
        "mediapipe_pose_runtime_failed": "mediapipe_pose_runtime_failed",
        "pose_evidence_low": "pose_evidence_low",
        "ball_evidence_low": "ball_evidence_low",
        "contact_not_detected": "contact_not_detected",
        "analysis_result_empty": "analysis_result_empty",
        "no_action_window_found": "no_action_window_found",
        "low_motion_signal": "low_motion_signal",
        "unknown_error": "unknown_error",
    }
    return aliases.get(text, text)


def summarize_window(window: Dict[str, Any], *, selected: bool = False) -> Dict[str, Any]:
    summary = {
        "index": int(window.get("index", 0) or 0),
        "start_s": round(float(window.get("start_s", 0.0) or 0.0), 3),
        "end_s": round(float(window.get("end_s", 0.0) or 0.0), 3),
        "duration_s": round(float(window.get("duration_s", max(0.0, float(window.get("end_s", 0.0) or 0.0) - float(window.get("start_s", 0.0) or 0.0))) or 0.0), 3),
        "contact_time_s": window.get("contact_time_s"),
        "peak_time_s": window.get("peak_time_s"),
        "score": round(float(window.get("score", 0.0) or 0.0), 3),
        "confidence": round(float(window.get("confidence", 0.0) or 0.0), 3),
        "source": str(window.get("source") or "locator"),
        "reason": str(window.get("reason") or ""),
        "selected": bool(selected),
    }
    debug = window.get("debug")
    if isinstance(debug, dict) and debug:
        summary["debug"] = dict(debug)
    return summary


def build_debug_context(
    *,
    selected_action: str = "",
    system_action_suggestion: str = "",
    analysis_routed_by: str = "",
    routed_analyzer: str = "",
    video_duration: float = 0.0,
    frame_count: int = 0,
    sampled_frame_count: int = 0,
    candidate_windows: Optional[Sequence[Dict[str, Any]]] = None,
    selected_window: Optional[Dict[str, Any]] = None,
    warnings: Optional[Iterable[str]] = None,
    fast_mode_enabled: bool = False,
    long_video_localized: bool = False,
    candidate_window_count: Optional[int] = None,
    selected_window_index: Optional[int] = None,
    selected_window_start_s: Optional[float] = None,
    selected_window_end_s: Optional[float] = None,
    selected_window_duration_s: Optional[float] = None,
    processing_time: float = 0.0,
    failure_reason: str = "",
    failure_message: str = "",
    route_mismatch_message: str = "",
) -> Dict[str, Any]:
    candidate_windows = list(candidate_windows or [])
    warnings_list = list(dict.fromkeys(str(item) for item in (warnings or []) if str(item).strip()))
    selected_window_summary = summarize_window(selected_window, selected=True) if isinstance(selected_window, dict) else None
    if candidate_window_count is None:
        candidate_window_count = len(candidate_windows)

    debug_context = {
        "selected_action": selected_action,
        "system_action_suggestion": system_action_suggestion,
        "analysis_routed_by": analysis_routed_by,
        "routed_analyzer": routed_analyzer,
        "video_duration": round(float(video_duration), 3),
        "frame_count": int(frame_count),
        "sampled_frame_count": int(sampled_frame_count),
        "candidate_window_count": int(candidate_window_count),
        "candidate_windows": [summarize_window(window, selected=False) for window in candidate_windows],
        "selected_window": selected_window_summary,
        "selected_window_index": selected_window_index,
        "selected_window_start_s": round(float(selected_window_start_s), 3) if selected_window_start_s is not None else None,
        "selected_window_end_s": round(float(selected_window_end_s), 3) if selected_window_end_s is not None else None,
        "selected_window_duration_s": round(float(selected_window_duration_s), 3) if selected_window_duration_s is not None else None,
        "fast_mode_enabled": bool(fast_mode_enabled),
        "long_video_localized": bool(long_video_localized),
        "processing_time": round(float(processing_time), 3),
        "failure_reason": failure_reason,
        "failure_message": failure_message,
        "route_mismatch_message": route_mismatch_message,
        "warnings": warnings_list,
    }
    return debug_context


def analysis_sort_key(payload: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    status = str(payload.get("analysis_status") or payload.get("status") or "").lower()
    integrity_state = str(payload.get("integrity_state") or "").lower()
    failure_reason = normalize_failure_reason(payload.get("failure_reason"))
    analysis_confidence = float(payload.get("analysis_confidence", 0.0) or 0.0)
    overall_score = payload.get("overall_score")
    if overall_score is None:
        score = payload.get("score") or {}
        overall_score = score.get("overall") or 0.0
    overall_score = float(overall_score or 0.0)
    warnings = list(payload.get("warnings") or [])
    selected_window_duration = float(payload.get("selected_window_duration_s") or 0.0)

    status_score = 1.0 if status == "success" else (0.75 if status == "partial" else 0.0)
    integrity_score = 0.0 if integrity_state == "anomaly" else 1.0
    failure_score = 0.0 if failure_reason else 1.0
    window_score = _clamp(selected_window_duration / 6.0)
    warning_penalty = max(0.0, 1.0 - 0.05 * len(warnings))

    return (
        round(status_score, 3),
        round(integrity_score, 3),
        round(failure_score, 3),
        round(float(analysis_confidence), 3),
        round(float(overall_score), 3),
        round(float(window_score * warning_penalty), 3),
    )


def select_best_analysis_payload(payloads: Sequence[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    ranked = sorted(
        (dict(payload) for payload in payloads if isinstance(payload, dict)),
        key=analysis_sort_key,
        reverse=True,
    )
    if not ranked:
        return None, []
    return ranked[0], ranked

