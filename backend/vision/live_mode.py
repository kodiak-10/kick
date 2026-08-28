import argparse
import json
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import platform
import threading
from types import SimpleNamespace

import cv2
import mediapipe as mp
import numpy as np

# Allow running this file directly from an IDE without requiring `python -m ...`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.ball_tracking import BallTracker, detect_ball, draw_ball, estimate_contact
from analysis.biomech_rules import analyze_biomech
from analysis.calibration import load_calibration
from analysis.football_sequence import compute_football_kinematics, fresh_sequence_state, update_football_sequence
from analysis.football_scoring import get_template_catalog, get_template_meta, score_football_action
from analysis.score_levels import score_level_from_overall
from analysis.shot_analysis import analyze_video
from analysis.runtime_profile import RuntimeProfiler
from analysis.reliability import evaluate_reliability
from analysis.target_tracking import compute_subject_signature, update_target_lock
from analysis.temporal_classifier import fresh_temporal_classifier_state, update_temporal_classifier
from feedback_engine import build_feedback_messages
from quality_gate import evaluate_global_quality_gate
from rules_loader import load_football_rules, resolve_action_name
from frontend.summary_card import render_card
from scoring_engine import score_action
from timestamp_error_locator import locate_error_timestamps


mp_pose = mp.solutions.pose
CAPTURE_WIDTH = 960
CAPTURE_HEIGHT = 540
INFER_MAX_WIDTH = 768
BALL_DETECT_INTERVAL = 2
ANALYSIS_INTERVAL_S = 1.0 / 18.0
SESSION_EXPORT_DIR = Path("reports") / "sessions"
RESULT_MIN_HOLD_S = 6.0
LIVE_RULE_SOURCE = "kick_ai_football_thresholds_v1.json"
LIVE_CAPTURE_MODE = "live_capture_mode"
OFFLINE_ANALYSIS_MODE = "offline_analysis_mode"
_LIVE_TEMPLATE_TO_RULE = {
    "passing_stability": "short_pass",
    "shooting_quality": "shot_instep",
    "first_touch_control": "receive_control",
}
_LIVE_IDLE_LABELS = {"ready", "soccer_idle", "target_locking", "target_lost", "full_body_required", "no_pose", "stable_motion"}


def _clamp(value, lo=0.0, hi=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = float(lo)
    return max(float(lo), min(float(hi), value))


class LatestFrameReader:
    def __init__(self, cap, loop_on_eof=False):
        self.cap = cap
        self.loop_on_eof = loop_on_eof
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.latest_frame = None
        self.latest_ts = 0.0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def _run(self):
        while not self.stop_event.is_set():
            ok, frame = self.cap.read()
            if not ok or frame is None:
                if self.loop_on_eof:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.002)
                    continue
                time.sleep(0.004)
                continue
            with self.lock:
                self.latest_frame = frame
                self.latest_ts = time.time()

    def read(self):
        with self.lock:
            if self.latest_frame is None:
                return None, 0.0
            return self.latest_frame.copy(), self.latest_ts

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=0.4)
        self.cap.release()


def _majority_label(labels, default="stable_motion"):
    if not labels:
        return default
    counts = {}
    for v in labels:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]


def _analysis_interval_for(flow_stage, phase_hint):
    if flow_stage in {"preview", "home"}:
        return 1.0 / 10.0
    if flow_stage == "ready_to_record":
        return 1.0 / 12.0
    if flow_stage == "recording":
        return 1.0 / 15.0
    if flow_stage == "processing":
        return 1.0 / 8.0
    if flow_stage in {"review", "result"}:
        return 1.0 / 6.0
    if flow_stage == "setup":
        return 1.0 / 12.0
    if phase_hint in {"contact", "follow_through"}:
        return 1.0 / 22.0
    if phase_hint in {"support", "approach", "recovery"}:
        return 1.0 / 18.0
    return ANALYSIS_INTERVAL_S


def _ball_detect_stride_for(phase_hint, last_ball):
    if last_ball is None:
        return 1
    conf = float(last_ball.get("confidence", 0.0))
    source = str(last_ball.get("source", "lost"))
    if source != "detected" or conf < 0.42:
        return 1
    if phase_hint in {"support", "contact", "follow_through"}:
        return 1
    if phase_hint in {"approach", "recovery"}:
        return 2
    return 3


def _is_active_label(label):
    return label not in {"ready", "soccer_idle", "target_locking", "target_lost", "full_body_required", "no_pose"}


def _update_event_card(event_card, summary, now_t):
    label = summary.get("label", "ready")
    issue = summary.get("issue", "stable_motion")
    severity = float(summary.get("severity", 0.0))
    confidence = float(summary.get("confidence", 0.0))
    is_event = (
        (_is_active_label(label) and confidence >= 0.42)
        or issue not in {"stable_motion", "capture_quality_low"}
        or severity >= 0.38
    )
    if is_event:
        return {
            "title": "Latest Event / 最近事件",
            "label": label,
            "issue": issue,
            "phase": summary.get("phase", "set"),
            "cue": summary.get("suggestion", "-"),
            "risk_score": float(summary.get("risk_score", severity)),
            "technique_score": float(summary.get("technique_score", 0.0)),
            "expires_at": float(now_t) + 1.5,
        }
    if event_card and float(event_card.get("expires_at", 0.0)) > float(now_t):
        return event_card
    return None


def _update_display_state(display_state, summary, metrics, now_t):
    numeric_keys = {
        "confidence",
        "severity",
        "technique_score",
        "control_score",
        "risk_score",
    }
    metric_numeric_keys = {
        "knee_l",
        "knee_r",
        "hip_l",
        "hip_r",
        "symmetry",
        "balance",
        "depth",
        "trunk_lean_deg",
        "valgus_ratio",
        "visibility",
        "stability",
        "move_ratio",
        "ball_confidence",
        "ball_contact",
        "target_lock_score",
        "target_switch_risk",
        "pixel_scale_cm",
        "ball_distance_m",
        "stance_width_m",
        "technique_score",
        "control_score",
        "risk_score",
    }
    if display_state is None:
        return {
            "summary": dict(summary),
            "metrics": dict(metrics),
            "freeze_until": float(now_t),
        }

    shown = dict(display_state["summary"])
    shown_metrics = dict(display_state["metrics"])
    freeze_until = float(display_state.get("freeze_until", 0.0))
    hold_window_s = 0.90

    raw_active = _is_active_label(summary.get("label", "ready")) or summary.get("issue") not in {"stable_motion", "capture_quality_low"}
    if raw_active:
        freeze_until = max(freeze_until, float(now_t) + hold_window_s)

    keep_categories = now_t < freeze_until and not raw_active
    for key, value in summary.items():
        if keep_categories and key not in numeric_keys and key != "raw":
            continue
        if key in numeric_keys:
            prev_val = float(shown.get(key, value))
            shown[key] = prev_val * 0.84 + float(value) * 0.16
        else:
            shown[key] = value

    if keep_categories:
        shown["raw"] = summary.get("raw", shown.get("raw", ""))
    for key, value in metrics.items():
        if isinstance(value, (int, float)) and key in metric_numeric_keys:
            prev_val = float(shown_metrics.get(key, value))
            shown_metrics[key] = prev_val * 0.82 + float(value) * 0.18
        else:
            shown_metrics[key] = value

    return {
        "summary": shown,
        "metrics": shown_metrics,
        "freeze_until": freeze_until,
    }


def _fresh_session_stats():
    return {
        "frames": 0,
        "frame_count": 0,
        "valid_pose_frames": 0,
        "ball_frames": 0,
        "event_count": 0,
        "main_score_sum": 0.0,
        "technical_sum": 0.0,
        "control_quality_sum": 0.0,
        "safety_quality_sum": 0.0,
        "severity_sum": 0.0,
        "max_severity": 0.0,
        "technique_sum": 0.0,
        "control_sum": 0.0,
        "risk_sum": 0.0,
        "overall_score_sum": 0.0,
        "outcome_score_sum": 0.0,
        "technique_score_sum": 0.0,
        "score_frames": 0,
        "ready_to_score_count": 0,
        "insufficient_evidence_count": 0,
        "quality_fail_count": 0,
        "issue_counts": {},
        "action_counts": {},
    }


def _fresh_live_scoring_state():
    return {
        "detected_action": "soccer_idle",
        "mapped_rule_key": "short_pass",
        "score_source": LIVE_RULE_SOURCE,
        "scoring_state": "insufficient_evidence",
        "scoring_state_message": "",
        "quality_status": "pass",
        "quality_gate_pass": False,
        "quality_result": None,
        "score_result": None,
        "feedback_result": None,
        "primary_metrics": [],
        "triggered_rules": [],
        "fail_reasons": [],
        "feedback_messages": [],
        "error_timestamps": [],
        "best_trial": None,
        "worst_trial": None,
        "rule_metrics": {},
        "analysis_confidence": 0.0,
        "summary_text": "",
        "core_problem": "",
        "next_step_advice": "",
        "quality_hint": "",
        "display_overall_score": None,
        "display_outcome_score": None,
        "display_technique_score": None,
        "display_level_label": "",
        "display_score_ready": False,
    }


def _fresh_runtime_state(football_rules=None):
    return {
        "workflow_mode": LIVE_CAPTURE_MODE,
        "analysis_mode": LIVE_CAPTURE_MODE,
        "flow_stage": "preview",
        "capture_stage": "preview",
        "selected_template": "passing_stability",
        "session_goal": "Passing Stability / 传球稳定性",
        "task_target": 1,
        "task_completed": 0,
        "raw_last_points": None,
        "last_points": None,
        "move_hist": deque(maxlen=20),
        "severity_hist": deque(maxlen=160),
        "fps_hist": deque(maxlen=30),
        "action_hist": deque(maxlen=14),
        "issue_hist": deque(maxlen=20),
        "ball_hist": deque(maxlen=12),
        "squat_reps": 0,
        "pushup_reps": 0,
        "squat_stage": "",
        "pushup_stage": "",
        "last_rep_time": 0.0,
        "last_event_ts": 0.0,
        "last_counted_event_ts": 0.0,
        "black_count": 0,
        "active_frames": 0,
        "severity_ema": 0.0,
        "conf_ema": 0.0,
        "last_ball": None,
        "lock_state": None,
        "sequence_state": fresh_sequence_state(),
        "temporal_state": fresh_temporal_classifier_state(),
        "ball_tracker": BallTracker(max_misses=6),
        "display_state": None,
        "last_render_payload": None,
        "event_card": None,
        "session_started": False,
        "session_start_time": None,
        "session_stats": _fresh_session_stats(),
        "football_rules": football_rules or load_football_rules(),
        "latest_scoring": _fresh_live_scoring_state(),
        "recording_writer": None,
        "recording_video_path": None,
        "recording_started_at": None,
        "recording_ended_at": None,
        "recording_frame_count": 0,
        "recording_motion_started": False,
        "recording_motion_peak": 0.0,
        "recording_idle_frames": 0,
        "recording_stop_reason": "",
        "recording_hint": "",
        "processing_hint": "",
        "analysis_job_running": False,
        "analysis_job_done": False,
        "analysis_job_error": "",
        "analysis_cancel_requested": False,
        "analysis_output_path": None,
        "offline_analysis_result": None,
        "post_session_summary": None,
        "result_min_until": 0.0,
        "result_notice": "",
        "result_notice_until": 0.0,
        "last_session_path": None,
        "analysis_frame_idx": 0,
    }


def _score_level_label(score: float) -> str:
    return score_level_from_overall(score)[1]


def _capture_stage_to_ui_stage(stage: str) -> str:
    stage = str(stage or "preview")
    if stage in {"preview", "home"}:
        return "home"
    if stage in {"ready_to_record", "recording", "processing", "setup"}:
        return "setup"
    if stage in {"review", "result"}:
        return "session_end"
    return "active"


def _analysis_primary_metrics_from_result(result: dict) -> list[dict]:
    sub_scores = dict(result.get("sub_scores") or {})
    rule_metrics = dict(result.get("rule_metrics") or {})
    preferred_order = [
        "max_ball_speed_mps",
        "target_zone_hit",
        "shot_consistency_cv_pct",
        "support_foot_lateral_offset_cm",
        "support_foot_ap_offset_cm",
        "trunk_lean_deg_at_impact_proxy",
        "endpoint_error_m",
        "execution_time_s",
        "penalty_events",
        "control_zone_success_rate",
        "stabilization_time_s",
        "corrective_touch_count",
        "lateral_offset_m",
        "completion_time_s",
        "cone_hit_count",
        "out_of_lane_count",
        "control_loss_count",
        "drop_count",
    ]
    metric_items: list[dict] = []
    seen = set()

    def _append_metric(metric_name: str, info: dict | None):
        seen.add(metric_name)
        info = dict(info or {})
        raw_value = info.get("raw_value", rule_metrics.get(metric_name))
        metric_items.append(
            {
                "metric": metric_name,
                "label": info.get("label", metric_name),
                "raw_value": raw_value,
                "score": info.get("score"),
                "band": info.get("band", "missing"),
                "role": info.get("role", "outcome"),
                "source_class": info.get("source_class"),
                "use_as": info.get("use_as"),
                "diagnostic_only": bool(info.get("diagnostic_only", False)),
                "matched_key": info.get("matched_key", metric_name),
            }
        )

    for metric_name in preferred_order:
        if metric_name in sub_scores:
            _append_metric(metric_name, sub_scores.get(metric_name))

    for metric_name, info in sub_scores.items():
        if metric_name in seen:
            continue
        _append_metric(metric_name, info)

    if not metric_items:
        for metric_name in preferred_order:
            if metric_name in rule_metrics:
                _append_metric(metric_name, {"raw_value": rule_metrics.get(metric_name), "label": metric_name, "band": "missing"})

    return metric_items


def _build_offline_review_summary(state, analysis_result, now_t):
    analysis_result = dict(analysis_result or {})
    quality_gate = dict(analysis_result.get("quality_gate") or {})
    quality_status = str(analysis_result.get("quality_status") or quality_gate.get("quality_status") or "pass")
    quality_gate_pass = bool(quality_gate.get("passed", quality_status == "pass"))
    analysis_confidence = float(analysis_result.get("analysis_confidence", 0.0) or 0.0)
    status = str(analysis_result.get("status", "ok"))
    score_block = dict(analysis_result.get("score") or {})
    scoring_state = str(analysis_result.get("scoring_state") or "")
    if not scoring_state:
        if quality_status == "fail" or quality_gate.get("should_reshoot"):
            scoring_state = "quality_fail"
        elif status != "ok" or analysis_confidence < 0.35:
            scoring_state = "insufficient_evidence"
        else:
            scoring_state = "ready_to_score"

    overall_score = float(analysis_result.get("overall_score", score_block.get("overall", 0.0)) or 0.0)
    is_sequence_result = bool(
        analysis_result.get("mapped_rule_key") == "pass_receive_sequence"
        or "pass_subscore" in analysis_result
        or "pass_subscore" in score_block
    )
    pass_subscore = float(analysis_result.get("pass_subscore", score_block.get("pass_subscore", 0.0)) or 0.0) if is_sequence_result else None
    receive_subscore = float(analysis_result.get("receive_subscore", score_block.get("receive_subscore", 0.0)) or 0.0) if is_sequence_result else None
    sequence_continuity_score = float(
        analysis_result.get("sequence_continuity_score", score_block.get("sequence_continuity_score", 0.0)) or 0.0
    ) if is_sequence_result else None
    next_action_readiness = float(
        analysis_result.get("next_action_readiness", score_block.get("next_action_readiness", 0.0)) or 0.0
    ) if is_sequence_result else None
    outcome_score = analysis_result.get("outcome_score", score_block.get("control_stability"))
    technique_score = analysis_result.get("technique_score", score_block.get("technical_execution"))
    if is_sequence_result:
        if outcome_score is None:
            outcome_score = receive_subscore
        if technique_score is None:
            technique_score = pass_subscore
    if scoring_state != "ready_to_score":
        overall_score_display = 0.0
        outcome_score_display = 0.0
        technique_score_display = None
    else:
        overall_score_display = overall_score
        outcome_score_display = float(outcome_score or 0.0)
        technique_score_display = float(technique_score) if technique_score is not None else None

    primary_metrics = list(analysis_result.get("primary_metrics") or [])
    if not primary_metrics:
        primary_metrics = _analysis_primary_metrics_from_result(analysis_result)
    triggered_rules = list(analysis_result.get("triggered_rules") or [])
    fail_reasons = list(analysis_result.get("fail_reasons") or [])
    feedback_messages = list(analysis_result.get("feedback_messages") or [])
    error_timestamps = list(analysis_result.get("error_timestamps") or [])
    best_trial = analysis_result.get("best_trial")
    worst_trial = analysis_result.get("worst_trial")

    score_result = {
        "action_name": analysis_result.get("action_name", analysis_result.get("resolved_action_name", analysis_result.get("mapped_rule_key", "short_pass"))),
        "input_action_name": analysis_result.get("input_action_name", analysis_result.get("detected_action", analysis_result.get("action_name", "uncertain"))),
        "resolved_action_name": analysis_result.get("resolved_action_name", analysis_result.get("mapped_rule_key", analysis_result.get("action_name", "short_pass"))),
        "action_display_name": analysis_result.get("action_display_name", "短传"),
        "overall_score": overall_score_display,
        "outcome_score": outcome_score_display,
        "technique_score": technique_score_display,
        "primary_score": float(analysis_result.get("primary_score", overall_score_display) or overall_score_display),
        "pass_subscore": pass_subscore,
        "receive_subscore": receive_subscore,
        "sequence_continuity_score": sequence_continuity_score,
        "next_action_readiness": next_action_readiness,
        "sub_scores": analysis_result.get("sub_scores", {}),
        "best_trial": best_trial,
        "worst_trial": worst_trial,
        "metric_results": primary_metrics,
    }

    if quality_status == "fail":
        status_message = str(quality_gate.get("reshoot_hint") or analysis_result.get("summary") or "视频质量不足，请重拍后再分析。")
    elif scoring_state == "insufficient_evidence":
        status_message = str(analysis_result.get("summary") or "当前证据不足，暂不输出正式评分。")
    else:
        status_message = str(analysis_result.get("summary") or "录制完成，已生成离线分析结果。")

    core_problem = status_message
    issues = list(analysis_result.get("issues") or [])
    if issues:
        first_issue = issues[0]
        core_problem = str(first_issue.get("explanation") or first_issue.get("title") or core_problem)
        next_step = str(first_issue.get("fix_advice") or first_issue.get("training_advice") or status_message)
    else:
        next_step = str(quality_gate.get("reshoot_hint") or analysis_result.get("summary") or "请继续录制更完整的动作片段。")

    clip_name = str(Path(analysis_result.get("video_path") or state.get("recording_video_path") or "recorded_session.mp4").name)
    result_path = analysis_result.get("analysis_output_path") or state.get("analysis_output_path")
    summary = {
        "title": "Session Summary / 本次检测总结",
        "action": analysis_result.get("resolved_action_name", analysis_result.get("action_name", "shot_instep")),
        "action_name": analysis_result.get("resolved_action_name", analysis_result.get("action_name", "shot_instep")),
        "action_label": analysis_result.get("action_display_name", "射门"),
        "detected_action": analysis_result.get("input_action_name", analysis_result.get("action_name", "shot_instep")),
        "mapped_rule_key": analysis_result.get("resolved_action_name", analysis_result.get("action_name", "shot_instep")),
        "score_source": LIVE_RULE_SOURCE,
        "scoring_state": scoring_state,
        "scoring_state_message": status_message,
        "quality_status": quality_status,
        "quality_gate_pass": quality_gate_pass,
        "primary_metrics": primary_metrics,
        "triggered_rules": triggered_rules,
        "fail_reasons": fail_reasons,
        "feedback_messages": feedback_messages,
        "error_timestamps": error_timestamps,
        "best_trial": best_trial,
        "worst_trial": worst_trial,
        "quality_result": quality_gate,
        "score_result": score_result,
        "score_ready": scoring_state == "ready_to_score",
        "level_label": score_block.get("level_label", "") if scoring_state == "ready_to_score" else "",
        "avg_main_score": overall_score_display,
        "avg_outcome_score": outcome_score_display,
        "avg_technique_score": technique_score_display if technique_score_display is not None else 0.0,
        "avg_severity": 0.0,
        "avg_technique": 0.0,
        "avg_control": 0.0,
        "avg_risk": 0.0,
        "issue": str(issues[0].get("id") if issues else "stable_motion"),
        "phase": str(issues[0].get("phase") if issues else "contact"),
        "template_label": get_template_meta(state.get("selected_template", "passing_stability"))["label"],
        "score_name": score_block.get("level_label", "Overall Score / 综合评分"),
        "goal": state.get("session_goal", "Training Session / 训练会话"),
        "completed": 1 if scoring_state == "ready_to_score" else 0,
        "target": 1,
        "events": int(state.get("session_stats", {}).get("event_count", 0) or 0),
        "avg_technical_score": float(score_block.get("technical_execution", 0.0)) if scoring_state == "ready_to_score" else 0.0,
        "avg_control_quality_score": float(score_block.get("control_stability", 0.0)) if scoring_state == "ready_to_score" else 0.0,
        "avg_safety_score": float(score_block.get("action_safety", 0.0)) if scoring_state == "ready_to_score" and quality_gate_pass else 0.0,
        "max_severity": 0.0,
        "frames": int(analysis_result.get("frame_count", 0) or 0),
        "frame_count": int(analysis_result.get("frame_count", 0) or 0),
        "valid_pose_frames": int(analysis_result.get("frame_count", 0) or 0),
        "ball_frames": int(analysis_result.get("frame_count", 0) or 0),
        "coach_summary": status_message,
        "issue_title": "Optimization Point / 可优化点" if scoring_state == "ready_to_score" else "Core Problem / 核心问题",
        "core_problem": core_problem,
        "suggestion": next_step,
        "positive_feedback": "录制完成，已生成离线分析结果。 / Recording complete, offline analysis is ready.",
        "status_message": status_message,
        "observations": quality_gate.get("observed", {}),
        "mode_name": f"{OFFLINE_ANALYSIS_MODE} / 离线分析模式",
        "analysis_mode": OFFLINE_ANALYSIS_MODE,
        "capture_stage": "review",
        "ui_stage": "session_end",
        "clip_name": clip_name,
        "saved_path": str(result_path) if result_path else state.get("last_session_path"),
        "recorded_video_path": analysis_result.get("video_path") or state.get("recording_video_path"),
        "generated_at": analysis_result.get("generated_at"),
        "analysis_confidence": analysis_confidence,
    }
    return summary


def _reset_capture_session(state, keep_last_session=True):
    saved_path = state.get("last_session_path") if keep_last_session else None
    writer = state.get("recording_writer")
    if writer is not None:
        try:
            writer.release()
        except Exception:
            pass
    state["workflow_mode"] = LIVE_CAPTURE_MODE
    state["analysis_mode"] = LIVE_CAPTURE_MODE
    state["flow_stage"] = "preview"
    state["capture_stage"] = "preview"
    state["session_started"] = False
    state["session_start_time"] = None
    state["session_stats"] = _fresh_session_stats()
    state["raw_last_points"] = None
    state["last_points"] = None
    state["move_hist"].clear()
    state["severity_hist"].clear()
    state["fps_hist"].clear()
    state["action_hist"].clear()
    state["issue_hist"].clear()
    state["ball_hist"].clear()
    state["squat_reps"] = 0
    state["pushup_reps"] = 0
    state["squat_stage"] = ""
    state["pushup_stage"] = ""
    state["last_rep_time"] = 0.0
    state["last_event_ts"] = 0.0
    state["last_counted_event_ts"] = 0.0
    state["black_count"] = 0
    state["active_frames"] = 0
    state["severity_ema"] = 0.0
    state["conf_ema"] = 0.0
    state["last_ball"] = None
    state["lock_state"] = None
    state["sequence_state"] = fresh_sequence_state()
    state["temporal_state"] = fresh_temporal_classifier_state()
    state["ball_tracker"] = BallTracker(max_misses=6)
    state["display_state"] = None
    state["last_render_payload"] = None
    state["event_card"] = None
    state["latest_scoring"] = _fresh_live_scoring_state()
    state["recording_writer"] = None
    state["recording_video_path"] = None
    state["recording_started_at"] = None
    state["recording_ended_at"] = None
    state["recording_frame_count"] = 0
    state["recording_motion_started"] = False
    state["recording_motion_peak"] = 0.0
    state["recording_idle_frames"] = 0
    state["recording_stop_reason"] = ""
    state["recording_hint"] = ""
    state["processing_hint"] = ""
    state["analysis_job_running"] = False
    state["analysis_job_done"] = False
    state["analysis_job_error"] = ""
    state["analysis_cancel_requested"] = False
    state["analysis_output_path"] = None
    state["analysis_thread"] = None
    state["offline_analysis_result"] = None
    state["post_session_summary"] = None
    state["result_min_until"] = 0.0
    state["result_notice"] = ""
    state["result_notice_until"] = 0.0
    state["task_target"] = 1
    state["task_completed"] = 0
    if keep_last_session:
        state["last_session_path"] = saved_path
    else:
        state["last_session_path"] = None


def _enter_review_stage(state, session_summary, now_t):
    if session_summary is None:
        return
    state["session_started"] = False
    state["analysis_mode"] = OFFLINE_ANALYSIS_MODE
    state["flow_stage"] = "review"
    state["capture_stage"] = "review"
    state["post_session_summary"] = session_summary
    state["result_min_until"] = float(now_t) + RESULT_MIN_HOLD_S
    state["result_notice"] = ""
    state["result_notice_until"] = 0.0
    state["display_state"] = None
    state["event_card"] = None
    state["active_frames"] = 0
    state["severity_ema"] = 0.0
    state["analysis_job_running"] = False
    state["analysis_job_done"] = True
    state["analysis_cancel_requested"] = False


def _open_recording_writer(state, frame_shape, fps_value, now_t):
    if frame_shape is None or len(frame_shape) < 2:
        return None
    h, w = int(frame_shape[0]), int(frame_shape[1])
    if h <= 0 or w <= 0:
        return None
    SESSION_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = SESSION_EXPORT_DIR / f"capture_{stamp}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, max(20.0, float(fps_value or 30.0)), (w, h))
    if not writer.isOpened():
        return None
    state["recording_writer"] = writer
    state["recording_video_path"] = str(out_path)
    state["recording_started_at"] = float(now_t)
    state["recording_ended_at"] = None
    state["recording_frame_count"] = 0
    state["recording_motion_started"] = False
    state["recording_motion_peak"] = 0.0
    state["recording_idle_frames"] = 0
    state["recording_stop_reason"] = ""
    state["recording_hint"] = "按 SPACE 结束录制后会自动离线分析。"
    state["processing_hint"] = ""
    state["analysis_job_running"] = False
    state["analysis_job_done"] = False
    state["analysis_job_error"] = ""
    state["analysis_cancel_requested"] = False
    state["analysis_output_path"] = None
    state["offline_analysis_result"] = None
    state["session_started"] = True
    state["session_start_time"] = float(now_t)
    state["task_target"] = 1
    state["task_completed"] = 0
    state["analysis_mode"] = LIVE_CAPTURE_MODE
    state["flow_stage"] = "recording"
    state["capture_stage"] = "recording"
    return out_path


def _stop_recording_writer(state, now_t, reason="manual"):
    writer = state.get("recording_writer")
    if writer is not None:
        try:
            writer.release()
        except Exception:
            pass
    state["recording_writer"] = None
    state["recording_ended_at"] = float(now_t)
    state["recording_stop_reason"] = str(reason)
    state["session_started"] = False
    return state.get("recording_video_path")


def _append_recording_frame(state, frame):
    writer = state.get("recording_writer")
    if writer is None or frame is None:
        return False
    try:
        writer.write(frame)
        state["recording_frame_count"] = int(state.get("recording_frame_count", 0) or 0) + 1
        return True
    except Exception:
        return False


def _offline_analysis_worker(state, video_path, output_path):
    try:
        result = analyze_video(video_path, output_path=output_path)
        if state.get("analysis_cancel_requested"):
            return
        state["offline_analysis_result"] = result
        state["analysis_job_error"] = ""
    except Exception as exc:
        if state.get("analysis_cancel_requested"):
            return
        state["offline_analysis_result"] = {
            "status": "error",
            "quality_status": "fail",
            "quality_gate": {
                "quality_status": "fail",
                "passed": False,
                "should_reshoot": True,
                "reshoot_hint": "离线分析失败，请重新录制后再试。",
                "observed": {},
            },
            "summary": "离线分析失败，请重新录制后再试。",
            "analysis_version": "video_engine_v1",
            "analysis_mode": "analyze_video",
            "analyzer_used": "generic_video_analyzer_v1",
            "input_video_path": str(video_path),
            "video_path": str(video_path),
            "detected_action": "uncertain",
            "action_confidence": 0.0,
            "mapped_rule_key": "short_pass",
            "recommended_template": "short_pass",
            "fallback_used": True,
            "whether_fallback_template_used": True,
            "unsupported_action_for_current_analyzer": False,
            "score_source": "proxy_rule_metrics",
            "ball_speed_measurement_type": "proxy",
            "action_name": "short_pass",
            "input_action_name": "uncertain",
            "resolved_action_name": "short_pass",
            "action_display_name": "短传",
            "score": {
                "overall": 0.0,
                "technical_execution": 0.0,
                "control_stability": 0.0,
                "action_safety": 0.0,
                "level_code": "needs_strengthening",
                "level_label": "Needs Strengthening / 需加强",
                "source": "proxy_rule_metrics",
                "measurement_mode": "proxy",
            },
            "primary_metrics": [],
            "sub_scores": {},
            "phase_scores": {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            "triggered_rules": [],
            "fail_reasons": [str(exc)],
            "feedback_messages": [str(exc)],
            "error_timestamps": [],
            "best_trial": None,
            "worst_trial": None,
            "rule_metrics": {},
            "analysis_confidence": 0.0,
        }
        state["analysis_job_error"] = str(exc)
    finally:
        state["analysis_job_running"] = False
        state["analysis_job_done"] = True


def _launch_offline_analysis(state, video_path, now_t):
    if not video_path:
        return None
    session_path = Path(video_path)
    if not session_path.exists():
        return None
    SESSION_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = session_path.with_suffix(".json")
    state["analysis_output_path"] = str(output_path)
    state["analysis_mode"] = OFFLINE_ANALYSIS_MODE
    state["flow_stage"] = "processing"
    state["capture_stage"] = "processing"
    state["processing_hint"] = "录制完成，正在离线分析..."
    state["analysis_job_running"] = True
    state["analysis_job_done"] = False
    state["analysis_job_error"] = ""
    state["analysis_cancel_requested"] = False
    worker = threading.Thread(
        target=_offline_analysis_worker,
        args=(state, str(session_path), str(output_path)),
        daemon=True,
    )
    state["analysis_thread"] = worker
    worker.start()
    return output_path


def _maybe_auto_stop_recording(state, move_ratio, subject_ready, now_t):
    if state.get("flow_stage") != "recording":
        return False
    started_at = float(state.get("recording_started_at") or 0.0)
    elapsed = max(0.0, float(now_t) - started_at) if started_at > 0.0 else 0.0
    if elapsed < 1.4:
        return False
    if subject_ready and move_ratio > 0.020:
        state["recording_motion_started"] = True
        state["recording_motion_peak"] = max(float(state.get("recording_motion_peak", 0.0) or 0.0), float(move_ratio))
        state["recording_idle_frames"] = 0
        return False
    if state.get("recording_motion_started"):
        if move_ratio < 0.010:
            state["recording_idle_frames"] = int(state.get("recording_idle_frames", 0) or 0) + 1
        else:
            state["recording_idle_frames"] = 0
        if state["recording_idle_frames"] >= 10:
            return True
    return False

def _template_to_rule_key(template_code: str) -> str:
    return _LIVE_TEMPLATE_TO_RULE.get(str(template_code), "short_pass")


def _is_idle_action_label(label: str) -> bool:
    return str(label) in _LIVE_IDLE_LABELS


def _resolve_live_rule_key(detected_action: str, selected_template: str, rules) -> tuple[str, str]:
    template_rule = _template_to_rule_key(selected_template)
    candidates = []
    if detected_action:
        candidates.append(str(detected_action))
    if template_rule not in candidates:
        candidates.append(template_rule)
    if selected_template and selected_template not in candidates:
        candidates.append(str(selected_template))

    for candidate in candidates:
        if not candidate or _is_idle_action_label(candidate):
            continue
        try:
            return resolve_action_name(candidate, rules), candidate
        except Exception:
            continue

    try:
        return resolve_action_name(template_rule, rules), detected_action or template_rule
    except Exception:
        return template_rule, detected_action or template_rule


def _sequence_elapsed_s(state, now_t: float) -> float:
    seq_state = state.get("sequence_state") or {}
    started_at = float(seq_state.get("action_started_at", 0.0) or 0.0)
    if started_at <= 0.0:
        started_at = float(state.get("session_start_time", 0.0) or 0.0)
    if started_at <= 0.0:
        return 0.0
    return max(0.0, float(now_t) - started_at)


def _build_live_rule_metrics(mapped_rule_key, metrics, sequence_snapshot, contact, ball, calibration, now_t, state, fps_value):
    body_span_px = float(metrics.get("body_span_px", 1.0) or 1.0)
    stability = float(metrics.get("stability", 0.0) or 0.0)
    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28) or 0.28)
    swing_ball_ratio = float(metrics.get("swing_ball_ratio", 0.16) or 0.16)
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.0) or 0.0)
    target_lock_score = float(metrics.get("target_lock_score", 0.0) or 0.0)
    target_switch_risk = float(metrics.get("target_switch_risk", 0.0) or 0.0)
    sequence_confidence = float(metrics.get("phase_confidence", 0.0) or 0.0)
    visibility = float(metrics.get("visibility", 0.0) or 0.0)
    scale_m_per_px = float((calibration or {}).get("scale_m_per_px", 0.0) or 0.0)
    if scale_m_per_px <= 0.0:
        scale_m_per_px = 0.02

    elapsed_s = _sequence_elapsed_s(state, now_t)
    contact_flag = bool(contact and contact.get("contact"))
    ball_detected = bool(ball and ball.get("source") == "detected")

    if mapped_rule_key == "shot_instep":
        max_ball_speed_mps = max(0.0, ball_speed_ratio * max(24.0, float(fps_value or 30.0) * 2.0))
        if contact_flag and target_lock_score >= 0.7 and ball_speed_ratio >= 0.18:
            target_zone_hit = 3.0
        elif contact_flag and (ball_speed_ratio >= 0.10 or target_lock_score >= 0.5):
            target_zone_hit = 2.0
        elif contact_flag:
            target_zone_hit = 1.0
        else:
            target_zone_hit = 0.0
        consistency_cv_pct = max(0.0, 100.0 * (1.0 - _clamp(0.62 * stability + 0.38 * sequence_confidence)))
        return {
            "max_ball_speed_mps": round(float(max_ball_speed_mps), 3),
            "target_zone_hit": float(target_zone_hit),
            "shot_consistency_cv_pct": round(float(consistency_cv_pct), 2),
            "support_foot_lateral_offset_cm": round(float(support_ball_ratio * body_span_px * scale_m_per_px * 100.0), 2),
            "support_foot_ap_offset_cm": round(float((support_ball_ratio - 0.20) * body_span_px * scale_m_per_px * 100.0), 2),
            "trunk_lean_deg_at_impact_proxy": round(float(metrics.get("trunk_lean_deg", 0.0) or 0.0), 2),
        }

    if mapped_rule_key == "short_pass":
        endpoint_error_m = max(0.0, min(1.8, support_ball_ratio * 1.6 + (0.20 if not contact_flag else 0.0)))
        execution_time_s = max(0.0, elapsed_s)
        penalty_events = 0
        penalty_events += 1 if not contact_flag else 0
        penalty_events += 1 if target_switch_risk > 0.45 else 0
        penalty_events += 1 if stability < 0.58 else 0
        return {
            "endpoint_error_m": round(float(endpoint_error_m), 3),
            "execution_time_s": round(float(execution_time_s), 3),
            "penalty_events": float(penalty_events),
            "plant_foot_orientation_deg": round(float(12.0 + target_switch_risk * 24.0), 2),
            "body_open_angle_deg_before_pass": round(float(18.0 + visibility * 35.0), 2),
        }

    if mapped_rule_key == "receive_control":
        control_zone_success_rate = _clamp(0.46 * (1.0 if contact_flag else 0.0) + 0.28 * target_lock_score + 0.26 * stability)
        stabilization_time_s = max(0.0, elapsed_s)
        corrective_touch_count = float(max(0, int(round((1.0 - control_zone_success_rate) * 3.0))))
        lateral_offset_m = max(0.0, min(1.2, support_ball_ratio * body_span_px * scale_m_per_px))
        return {
            "control_zone_success_rate": round(float(control_zone_success_rate), 3),
            "stabilization_time_s": round(float(stabilization_time_s), 3),
            "corrective_touch_count": corrective_touch_count,
            "lateral_offset_m": round(float(lateral_offset_m), 3),
            "body_open_angle_deg": round(float(16.0 + visibility * 32.0), 2),
            "recenter_time_s": round(float(max(0.0, elapsed_s * 0.65)), 3),
        }

    if mapped_rule_key == "dribble_change_direction":
        completion_time_s = max(0.0, elapsed_s)
        cone_hit_count = float(max(0, int(round(target_switch_risk * 2.0))))
        out_of_lane_count = float(max(0, int(round((1.0 - stability) * 2.0))))
        control_loss_count = float(max(0, int(round((1.0 - float(metrics.get("ball_confidence", 0.0) or 0.0)) * 2.0))))
        return {
            "completion_time_s": round(float(completion_time_s), 3),
            "cone_hit_count": cone_hit_count,
            "out_of_lane_count": out_of_lane_count,
            "control_loss_count": control_loss_count,
            "mean_touches_per_meter": round(float(max(0.0, 1.0 + stability * 2.4)), 3),
            "max_ball_body_separation_m": round(float(max(0.0, support_ball_ratio * body_span_px * scale_m_per_px)), 3),
        }

    if mapped_rule_key == "juggling":
        dominant = max(0, int(round(float(state.get("task_completed", 0) or 0))))
        freestyle = max(0, dominant - 1)
        drop_count = float(max(0, int(round((1.0 - stability) * 3.0 + (0 if ball_detected else 1)))))
        return {
            "consecutive_touches_dominant_foot": float(dominant),
            "consecutive_touches_freestyle": float(freestyle),
            "drop_count": drop_count,
            "non_dominant_foot_juggling": float(max(0, dominant - 2)),
            "complex_sequence_juggling": float(max(0, dominant - 3)),
        }

    return {
        "endpoint_error_m": round(float(support_ball_ratio * 1.6), 3),
        "execution_time_s": round(float(elapsed_s), 3),
        "penalty_events": float(0 if contact_flag else 1),
    }


def _quality_gate_input(state, metrics, now_t):
    stats = state.get("session_stats", {})
    fps_hist = list(state.get("fps_hist") or [])
    avg_fps = float(sum(fps_hist) / len(fps_hist)) if fps_hist else 0.0
    return {
        "frame_count": int(stats.get("frame_count", 0) or 0),
        "valid_pose_frames": int(stats.get("valid_pose_frames", 0) or 0),
        "ball_frames": int(stats.get("ball_frames", 0) or 0),
        "fps": avg_fps,
    }


def _score_state_message(scoring_state, quality_result, reliability, detected_action):
    if scoring_state == "quality_fail":
        return str(quality_result.get("reshoot_hint") or "视频质量不足，请重拍后再分析。")
    if scoring_state == "insufficient_evidence":
        if not reliability.should_score:
            return str(reliability.user_message or "Primary target is not stable yet, so scoring is intentionally withheld.")
        return "Primary target is not stable yet, so scoring is intentionally withheld. / 当前主目标尚未稳定锁定，因此系统不会给出专项评分。"
    return ""


def _build_soccer_live_payload(context):
    state = context["state"]
    now_t = float(context["now_t"])
    calibration = context["calibration"]
    lm = context.get("lm")
    selected_template = context["selected_template"]
    mode_name = context["mode_name"]
    sequence_snapshot = context["sequence_snapshot"]
    temporal_prediction = context["temporal_prediction"]
    reliability = context["reliability"]
    contact = context["contact"]
    ball = context["ball"]
    vis_avg = float(context["vis_avg"])
    target_locked = bool(context["target_locked"])
    lock_score = float(context["lock_score"])
    target_status = str(context["target_status"])
    support_side = str(context["support_side"])
    swing_side = str(context["swing_side"])
    support_ball_ratio = float(context["support_ball_ratio"])
    swing_ball_ratio = float(context["swing_ball_ratio"])
    ball_speed_ratio = float(context["ball_speed_ratio"])
    balance = float(context["balance"])
    trunk_lean_deg = float(context["trunk_lean_deg"])
    symmetry = float(context["symmetry"])
    valgus_ratio = float(context["valgus_ratio"])
    body_span = float(context["body_span"])
    move_ratio = float(context["move_ratio"])
    full_body = bool(context["full_body"])
    subject_ready = bool(context["subject_ready"])
    phase = str(context["phase"])
    ball_confidence = float(context["ball_confidence"])
    brightness = float(context["brightness"])
    body_fill_ratio = float(context["body_fill_ratio"])
    rules = state.get("football_rules") or load_football_rules()
    fps_value = float(sum(state["fps_hist"]) / len(state["fps_hist"])) if state.get("fps_hist") else 0.0

    detected_action = str(
        temporal_prediction.label
        if temporal_prediction is not None
        else (sequence_snapshot.action_label if sequence_snapshot is not None else "soccer_idle")
    )
    mapped_rule_key, detected_action_source = _resolve_live_rule_key(detected_action, selected_template, rules)
    rule_metrics = {
        "visibility": vis_avg,
        "body_span_px": body_span,
        "support_ball_ratio": support_ball_ratio,
        "swing_ball_ratio": swing_ball_ratio,
        "ball_speed_ratio": ball_speed_ratio,
        "phase_confidence": sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0,
        "ball_confidence": ball_confidence,
        "target_lock_score": lock_score,
        "target_switch_risk": float(state.get("lock_state", {}).get("switch_risk", 0.0)),
        "stability": float(context["stability"]),
        "trunk_lean_deg": trunk_lean_deg,
        "balance": balance,
        "symmetry": symmetry,
        "valgus_ratio": valgus_ratio,
    }

    quality_result = evaluate_global_quality_gate(
        run_data=_quality_gate_input(state, rule_metrics, now_t),
        metrics={"visibility": vis_avg},
        rules=rules,
        action_name=mapped_rule_key,
    )
    analysis_active = bool(state.get("session_started") and state.get("active_frames", 0) >= 6 and target_locked)
    evidence_ready = bool(
        analysis_active
        and subject_ready
        and sequence_snapshot is not None
        and sequence_snapshot.sequence_ready
        and reliability.should_score
        and detected_action not in _LIVE_IDLE_LABELS
    )
    scoring_state = "quality_fail" if not quality_result.get("passed", False) else ("ready_to_score" if evidence_ready else "insufficient_evidence")

    score_result = score_action(
        mapped_rule_key,
        rule_metrics,
        rules,
        audience="beginner",
        quality_result=quality_result,
        analysis_context={"rule_metrics": rule_metrics, "legacy_metrics": rule_metrics},
    )
    if context.get("profiler") is not None:
        context["profiler"].record("score_compute", 0.0, state.get("flow_stage", "active"), phase)

    feedback_result = build_feedback_messages(
        action_name=mapped_rule_key,
        rules=rules,
        score_result=score_result,
        quality_result=quality_result,
        analysis_context={"rule_metrics": rule_metrics, "legacy_metrics": rule_metrics},
    )
    combined_triggered_rules = _merge_triggered_rules(score_result.get("triggered_rules"), quality_result.get("triggered_rules"))
    error_result = locate_error_timestamps(
        action_name=mapped_rule_key,
        triggered_rules=combined_triggered_rules,
        event_times={
            "support": float(state.get("sequence_state", {}).get("action_started_at", now_t) or now_t),
            "contact": float(state.get("sequence_state", {}).get("last_contact_time", now_t) or now_t),
            "follow_through": float(state.get("sequence_state", {}).get("last_complete_time", now_t) or now_t),
        },
        default_time=now_t,
        trial_scores=score_result.get("metric_results") or None,
    )

    feedback_messages = list(feedback_result.get("feedback_messages") or [])
    fail_reasons = list(dict.fromkeys((feedback_result.get("fail_reasons") or []) + list(quality_result.get("fail_reasons") or [])))
    primary_metrics = [
        {
            "metric": metric.get("metric"),
            "label": metric.get("label"),
            "raw_value": metric.get("raw_value"),
            "score": metric.get("score"),
            "band": metric.get("band"),
            "role": metric.get("role"),
            "source_class": metric.get("source_class"),
            "use_as": metric.get("use_as"),
            "diagnostic_only": metric.get("diagnostic_only", False),
            "matched_key": metric.get("matched_key"),
        }
        for metric in score_result.get("metric_results") or []
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

    quality_gate_pass = bool(quality_result.get("passed", False))
    score_ready = scoring_state == "ready_to_score"
    display_overall_score = float(score_result.get("overall_score") or 0.0) if score_ready else 0.0
    display_outcome_score = float(score_result.get("outcome_score") or 0.0) if score_ready else 0.0
    display_technique_score = float(score_result.get("technique_score") or 0.0) if score_ready else 0.0
    display_action_safety = 100.0 if score_ready and quality_gate_pass else 0.0
    display_control_stability = display_outcome_score
    display_technical_execution = display_technique_score
    display_level_label = _score_level_label(display_overall_score) if score_ready else ""
    action_display_name = str(
        score_result.get("action_display_name")
        or rules.get("actions", {}).get(mapped_rule_key, {}).get("display_name", mapped_rule_key)
    )
    score_name = f"{action_display_name} Score / {action_display_name}评分"
    score_definition = str(rules.get("meta", {}).get("scoring_principle", "outcome_first_technique_second"))
    quality_hint = str(quality_result.get("reshoot_hint") or "")
    scoring_state_message = _score_state_message(scoring_state, quality_result, reliability, detected_action)

    if score_ready:
        summary_text = feedback_messages[0] if feedback_messages else f"{action_display_name} scored successfully."
        coach_summary = summary_text
        positive_feedback = feedback_messages[-1] if feedback_messages else f"{action_display_name} scoring is ready."
        suggestion = feedback_messages[1] if len(feedback_messages) > 1 else positive_feedback
        issue_show = combined_triggered_rules[0]["id"] if combined_triggered_rules else "stable_action"
        severity = max(0.0, min(1.0, 1.0 - display_overall_score / 100.0))
    elif scoring_state == "quality_fail":
        summary_text = quality_hint or scoring_state_message or "视频质量不足，请重拍后再分析。"
        coach_summary = summary_text
        positive_feedback = quality_hint or "请重拍更清晰的视频，再继续分析。"
        suggestion = quality_hint or positive_feedback
        issue_show = "video_quality_fail"
        severity = 0.95
    else:
        summary_text = scoring_state_message or "Primary target is not stable yet, so scoring is intentionally withheld."
        coach_summary = summary_text
        positive_feedback = "Keep one athlete centered and the product will switch into analysis. / 保持单一被检测者居中后，系统会进入分析状态。"
        suggestion = scoring_state_message or "hold center frame until primary target locks"
        issue_show = "capture_quality_low"
        severity = 0.45

    if score_ready:
        state["severity_ema"] = 0.80 * state["severity_ema"] + 0.20 * severity
    else:
        state["severity_ema"] = 0.88 * state["severity_ema"] + 0.12 * severity
    severity = state["severity_ema"]

    action_for_hist = mapped_rule_key if score_ready else detected_action
    issue_for_hist = issue_show
    state["action_hist"].append(action_for_hist)
    state["issue_hist"].append(issue_for_hist)
    stable_action = _majority_label(state["action_hist"], action_for_hist)
    stable_issue = _majority_label(state["issue_hist"], issue_for_hist)

    stats = state["session_stats"]
    stats["frame_count"] += 1
    if full_body:
        stats["valid_pose_frames"] += 1
    if ball is not None and ball.get("source") == "detected":
        stats["ball_frames"] += 1
    stats["severity_sum"] += float(severity)
    stats["max_severity"] = max(float(stats["max_severity"]), float(severity))
    _count_label(stats["issue_counts"], issue_show)
    _count_label(stats["action_counts"], action_for_hist)

    if score_ready:
        stats["frames"] += 1
        stats["score_frames"] += 1
        stats["overall_score_sum"] += float(display_overall_score)
        stats["outcome_score_sum"] += float(display_outcome_score)
        stats["technique_score_sum"] += float(display_technical_execution)
        stats["main_score_sum"] += float(display_overall_score)
        stats["technical_sum"] += float(display_technical_execution)
        stats["control_quality_sum"] += float(display_control_stability)
        stats["safety_quality_sum"] += float(display_action_safety)
        stats["technique_sum"] += float(display_technical_execution)
        stats["control_sum"] += float(display_control_stability)
        stats["risk_sum"] += float(1.0 - display_action_safety / 100.0)
        stats["ready_to_score_count"] += 1
        if sequence_snapshot is not None and sequence_snapshot.events.get("sequence_complete"):
            state["last_counted_event_ts"] = float(now_t)
            stats["event_count"] += 1
            state["task_completed"] = min(int(state.get("task_target", 12)), int(state["task_completed"]) + 1)
    elif scoring_state == "quality_fail":
        stats["quality_fail_count"] += 1
    else:
        stats["insufficient_evidence_count"] += 1

    key_issues = []
    for rule in combined_triggered_rules[:3]:
        sev = rule.get("severity", 0.0)
        if isinstance(sev, str):
            sev = 0.9 if sev == "fail" else 0.6 if sev == "warn" else 0.2
        try:
            sev_num = float(sev)
        except Exception:
            sev_num = 0.0
        key_issues.append(
            SimpleNamespace(
                code=str(rule.get("id") or rule.get("metric") or "issue"),
                label=str(rule.get("label") or rule.get("metric") or "Issue"),
                severity=sev_num,
                summary=str(rule.get("reason") or ""),
                cue=str(rule.get("cue") or suggestion or ""),
            )
        )
    if not key_issues:
        key_issues.append(
            SimpleNamespace(
                code="stable_action",
                label="Action quality is stable / 动作完成质量稳定",
                severity=0.12,
                summary=coach_summary,
                cue=suggestion,
            )
        )

    phase_scores = {
        "preparation": display_control_stability if score_ready else 0.0,
        "support": display_control_stability if score_ready else 0.0,
        "contact": display_technical_execution if score_ready else 0.0,
        "follow_through": display_action_safety if score_ready else 0.0,
    }

    latest_scoring = {
        "detected_action": detected_action,
        "detected_action_source": detected_action_source,
        "mapped_rule_key": mapped_rule_key,
        "action_display_name": action_display_name,
        "score_name": score_name,
        "score_definition": score_definition,
        "score_source": LIVE_RULE_SOURCE,
        "scoring_state": scoring_state,
        "scoring_state_message": scoring_state_message,
        "quality_status": str(quality_result.get("quality_status", "pass")),
        "quality_gate_pass": quality_gate_pass,
        "quality_result": quality_result,
        "score_result": score_result,
        "feedback_result": feedback_result,
        "primary_metrics": primary_metrics,
        "triggered_rules": combined_triggered_rules,
        "fail_reasons": fail_reasons,
        "feedback_messages": feedback_messages,
        "error_timestamps": error_result.get("error_timestamps", []),
        "best_trial": error_result.get("best_trial") or score_result.get("best_trial"),
        "worst_trial": error_result.get("worst_trial") or score_result.get("worst_trial"),
        "rule_metrics": rule_metrics,
        "analysis_confidence": float(temporal_prediction.confidence if temporal_prediction is not None else 0.0),
        "summary_text": summary_text,
        "core_problem": combined_triggered_rules[0]["reason"] if combined_triggered_rules else scoring_state_message,
        "next_step_advice": suggestion,
        "positive_feedback": positive_feedback,
        "quality_hint": quality_hint,
        "overall_score": display_overall_score if score_ready else 0.0,
        "outcome_score": display_outcome_score if score_ready else 0.0,
        "technique_score": display_technical_execution if score_ready else None,
        "display_level_label": display_level_label,
        "score_ready": score_ready,
    }
    state["latest_scoring"] = latest_scoring

    summary = {
        "ui_stage": "active",
        "mode_name": mode_name,
        "label": mapped_rule_key if score_ready else (target_status if scoring_state == "quality_fail" else "ready"),
        "issue": issue_show,
        "confidence": reliability.overall if score_ready else 0.0,
        "overall_score": display_overall_score if score_ready else 0.0,
        "score_name": score_name,
        "score_definition": score_definition,
        "set": 1,
        "reps": 0,
        "rep_target": 12,
        "task_title": state.get("session_goal", "Training Session / 训练会话"),
        "task_completed": int(state.get("task_completed", 0)),
        "task_target": int(state.get("task_target", 12)),
        "severity": severity,
        "suggestion": suggestion,
        "coach_summary": coach_summary,
        "problem_title": "Optimization Point / 可优化点" if score_ready and display_overall_score >= 80.0 else "Core Problem / 核心问题",
        "core_problem": latest_scoring["core_problem"] or coach_summary,
        "issue_phase_label": phase,
        "positive_feedback": positive_feedback,
        "template_label": action_display_name,
        "technical_execution_score": display_technical_execution if score_ready else 0.0,
        "control_stability_score": display_control_stability if score_ready else 0.0,
        "action_safety_score": display_action_safety if score_ready else 0.0,
        "score_ready": score_ready,
        "score_gate_reason": quality_result.get("quality_status"),
        "show_event_card": score_ready and sequence_snapshot is not None and sequence_snapshot.sequence_active,
        "classifier_label": detected_action,
        "classifier_confidence": float(temporal_prediction.confidence if temporal_prediction is not None else 0.0),
        "key_issues": [
            {"code": issue.code, "label": issue.label, "summary": issue.summary, "cue": issue.cue}
            for issue in key_issues
        ],
        "level_label": display_level_label,
        "mode_name": mode_name,
        "calibrated": calibration is not None,
        "phase": phase,
        "target_status": target_status,
        "support_side": support_side,
        "swing_side": swing_side,
        "technique_score": display_technical_execution if score_ready else 0.0,
        "control_score": display_control_stability if score_ready else 0.0,
        "risk_score": max(0.0, min(1.0, 1.0 - display_action_safety / 100.0)) if score_ready else (1.0 if scoring_state == "quality_fail" else 0.5),
        "ball_track_source": ball.get("source", "lost") if ball is not None else "lost",
        "score_source": LIVE_RULE_SOURCE,
        "detected_action": detected_action,
        "mapped_rule_key": mapped_rule_key,
        "scoring_state": scoring_state,
        "quality_status": str(quality_result.get("quality_status", "pass")),
        "quality_gate_pass": quality_gate_pass,
        "primary_metrics": primary_metrics,
        "triggered_rules": combined_triggered_rules,
        "fail_reasons": fail_reasons,
        "feedback_messages": feedback_messages,
        "error_timestamps": error_result.get("error_timestamps", []),
        "best_trial": latest_scoring["best_trial"],
        "worst_trial": latest_scoring["worst_trial"],
        "raw": (
            f"action={detected_action}->{mapped_rule_key} state={scoring_state} "
            f"score={display_overall_score:.1f} quality={quality_result.get('quality_status', 'pass')} "
            f"phase={phase} lock={lock_score:.2f} trust={reliability.overall:.2f}"
        ),
    }

    metrics = {
        "knee_l": context["metrics"].get("knee_l", 0.0),
        "knee_r": context["metrics"].get("knee_r", 0.0),
        "hip_l": context["metrics"].get("hip_l", 0.0),
        "hip_r": context["metrics"].get("hip_r", 0.0),
        "symmetry": symmetry,
        "balance": balance,
        "depth": context["metrics"].get("depth", 0.0),
        "trunk_lean_deg": trunk_lean_deg,
        "valgus_ratio": valgus_ratio,
        "visibility": vis_avg,
        "stability": context["stability"],
        "move_ratio": move_ratio,
        "ball_confidence": ball_confidence,
        "ball_contact": 1.0 if contact.get("contact") else 0.0,
        "contact_side": contact.get("side", "none"),
        "ball_track_source": ball.get("source", "lost") if ball is not None else "lost",
        "target_lock_score": lock_score,
        "target_switch_risk": float(state.get("lock_state", {}).get("switch_risk", 0.0)),
        "target_appearance_score": float(state.get("lock_state", {}).get("appearance_score", 0.0)),
        "target_status": target_status,
        "phase": phase,
        "phase_confidence": sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0,
        "phase_locked": 1.0 if sequence_snapshot is not None and sequence_snapshot.phase_locked else 0.0,
        "support_side": support_side,
        "swing_side": swing_side,
        "classifier_confidence": float(temporal_prediction.confidence if temporal_prediction is not None else 0.0),
        "technique_score": display_technical_execution if score_ready else 0.0,
        "control_score": display_control_stability if score_ready else 0.0,
        "risk_score": max(0.0, min(1.0, 1.0 - display_action_safety / 100.0)) if score_ready else (1.0 if scoring_state == "quality_fail" else 0.5),
        "support_ball_distance_px": 0.0 if ball is None else support_ball_ratio * body_span,
        "swing_ball_distance_px": 0.0 if ball is None else swing_ball_ratio * body_span,
        "support_ball_ratio": support_ball_ratio,
        "swing_ball_ratio": swing_ball_ratio,
        "ball_speed_ratio": ball_speed_ratio,
        "main_score": display_overall_score if score_ready else 0.0,
        "technical_execution_score": display_technical_execution if score_ready else 0.0,
        "control_stability_score": display_control_stability if score_ready else 0.0,
        "action_safety_score": display_action_safety if score_ready else 0.0,
        "preparation_score": phase_scores["preparation"],
        "support_score": phase_scores["support"],
        "contact_score": phase_scores["contact"],
        "follow_through_score": phase_scores["follow_through"],
        "reliability_overall": reliability.overall,
        "reliability_pose": reliability.pose,
        "reliability_ball": reliability.ball,
        "reliability_stage": reliability.stage,
        "reliability_environment": reliability.environment,
        "detected_action": detected_action,
        "mapped_rule_key": mapped_rule_key,
        "score_source": LIVE_RULE_SOURCE,
        "scoring_state": scoring_state,
        "quality_status": str(quality_result.get("quality_status", "pass")),
        "quality_gate_pass": quality_gate_pass,
    }
    if calibration is not None:
        scale = float(calibration.get("scale_m_per_px", 0.0))
        metrics["pixel_scale_cm"] = scale * 100.0
        metrics["ball_distance_m"] = float(contact["distance_px"]) * scale if contact.get("distance_px") is not None else 0.0
        metrics["stance_width_m"] = float(context["ankle_dist"]) * scale
    metrics["body_span_px"] = body_span

    state["display_state"] = _update_display_state(state["display_state"], summary, metrics, now_t)
    state["event_card"] = _update_event_card(state.get("event_card"), state["display_state"]["summary"], now_t)

    payload = {
        "summary": state["display_state"]["summary"],
        "metrics": state["display_state"]["metrics"],
        "landmarks": lm,
        "ball": ball,
        "contact": contact,
        "bounds": state["lock_state"]["bounds"],
        "target_locked": target_locked,
        "switch_risk": float(state["lock_state"]["switch_risk"]),
        "subject_ready": subject_ready,
    }
    state["last_render_payload"] = payload
    return payload


def _merge_triggered_rules(*groups):
    merged = []
    seen = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("id") or item.get("metric") or item.get("rule_id") or "")
            if not rule_id or rule_id in seen:
                continue
            seen.add(rule_id)
            merged.append(dict(item))
    return merged


def _reset_for_next_session(state):
    _reset_capture_session(state, keep_last_session=True)


def _enter_result_stage(state, session_summary, now_t):
    if session_summary is None:
        return
    state["session_started"] = False
    state["flow_stage"] = "result"
    state["post_session_summary"] = session_summary
    state["result_min_until"] = float(now_t) + RESULT_MIN_HOLD_S
    state["result_notice"] = ""
    state["result_notice_until"] = 0.0
    state["display_state"] = None
    state["event_card"] = None
    state["active_frames"] = 0
    state["severity_ema"] = 0.0


def _start_active_session(state, now_t):
    state["session_started"] = True
    state["flow_stage"] = "active"
    state["session_start_time"] = now_t
    state["severity_hist"].clear()
    state["display_state"] = None
    state["action_hist"].clear()
    state["issue_hist"].clear()
    state["ball_hist"].clear()
    state["last_event_ts"] = 0.0
    state["last_ball"] = None
    state["sequence_state"] = fresh_sequence_state()
    state["temporal_state"] = fresh_temporal_classifier_state()
    state["event_card"] = None
    state["post_session_summary"] = None
    state["latest_scoring"] = _fresh_live_scoring_state()
    state["result_min_until"] = 0.0
    state["result_notice"] = ""
    state["result_notice_until"] = 0.0
    state["session_stats"] = _fresh_session_stats()


def _count_label(counts, label):
    counts[label] = counts.get(label, 0) + 1


def _top_label(counts, default="stable_motion"):
    if not counts:
        return default
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _build_session_summary(state, now_t):
    stats = state.get("session_stats", {})
    latest = dict(state.get("latest_scoring") or {})
    score_result = dict(latest.get("score_result") or {})
    quality_result = dict(latest.get("quality_result") or {})
    primary_metrics = list(latest.get("primary_metrics") or [])
    triggered_rules = list(latest.get("triggered_rules") or [])
    fail_reasons = list(latest.get("fail_reasons") or [])
    feedback_messages = list(latest.get("feedback_messages") or [])
    error_timestamps = list(latest.get("error_timestamps") or [])

    score_frames = int(stats.get("score_frames", 0) or stats.get("frames", 0) or 0)
    ready_to_score = str(latest.get("scoring_state", "insufficient_evidence")) == "ready_to_score"
    quality_gate_pass = bool(latest.get("quality_gate_pass", False))
    quality_status = str(latest.get("quality_status", "pass"))
    overall_score = float(stats.get("overall_score_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    outcome_score = float(stats.get("outcome_score_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    technique_score = float(stats.get("technique_score_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    avg_severity = float(stats.get("severity_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    avg_technique = float(stats.get("technique_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    avg_control = float(stats.get("control_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    avg_risk = float(stats.get("risk_sum", 0.0)) / score_frames if score_frames > 0 else 0.0
    top_issue = _top_label(stats.get("issue_counts", {}), "stable_motion")
    top_action = _top_label(stats.get("action_counts", {}), str(latest.get("detected_action", "soccer_idle")))
    level_label = _score_level_label(overall_score) if ready_to_score else ""
    issue_title = "Optimization Point / 可优化点" if ready_to_score and overall_score >= 80.0 else "Core Problem / 核心问题"
    summary_text = str(latest.get("summary_text") or latest.get("scoring_state_message") or latest.get("quality_hint") or "")
    if not summary_text:
        summary_text = "Session completed. / 本次动作已完成。"
    return {
        "title": "Session Summary / 本次检测总结",
        "action": top_action,
        "action_name": str(latest.get("mapped_rule_key") or _template_to_rule_key(state.get("selected_template", "passing_stability"))),
        "action_label": str(latest.get("action_display_name") or latest.get("mapped_rule_key") or top_action),
        "detected_action": str(latest.get("detected_action", "soccer_idle")),
        "mapped_rule_key": str(latest.get("mapped_rule_key") or _template_to_rule_key(state.get("selected_template", "passing_stability"))),
        "score_source": str(latest.get("score_source", LIVE_RULE_SOURCE)),
        "scoring_state": str(latest.get("scoring_state", "insufficient_evidence")),
        "scoring_state_message": str(latest.get("scoring_state_message", "")),
        "quality_status": quality_status,
        "quality_gate_pass": quality_gate_pass,
        "primary_metrics": primary_metrics,
        "triggered_rules": triggered_rules,
        "fail_reasons": fail_reasons,
        "feedback_messages": feedback_messages,
        "error_timestamps": error_timestamps,
        "best_trial": latest.get("best_trial"),
        "worst_trial": latest.get("worst_trial"),
        "quality_result": quality_result,
        "score_result": score_result,
        "score_ready": ready_to_score,
        "level_label": level_label,
        "avg_main_score": overall_score if ready_to_score else 0.0,
        "avg_outcome_score": outcome_score if ready_to_score else 0.0,
        "avg_technique_score": technique_score if ready_to_score else 0.0,
        "avg_severity": avg_severity,
        "avg_technique": avg_technique,
        "avg_control": avg_control,
        "avg_risk": avg_risk,
        "issue": top_issue,
        "phase": str((state.get("sequence_state") or {}).get("phase", "set")),
        "template_label": get_template_meta(state.get("selected_template", "passing_stability"))["label"],
        "score_name": get_template_meta(state.get("selected_template", "passing_stability"))["score_name"],
        "goal": state.get("session_goal", "Training Session / 训练会话"),
        "completed": int(state.get("task_completed", 0)),
        "target": int(state.get("task_target", 12)),
        "events": int(stats.get("event_count", 0)),
        "avg_technical_score": float(score_result.get("technique_score") or 0.0) if ready_to_score else 0.0,
        "avg_control_quality_score": float(score_result.get("outcome_score") or 0.0) if ready_to_score else 0.0,
        "avg_safety_score": 100.0 if ready_to_score and quality_gate_pass else 0.0,
        "max_severity": float(stats.get("max_severity", 0.0)),
        "frames": score_frames,
        "frame_count": int(stats.get("frame_count", 0) or 0),
        "valid_pose_frames": int(stats.get("valid_pose_frames", 0) or 0),
        "ball_frames": int(stats.get("ball_frames", 0) or 0),
        "coach_summary": summary_text,
        "issue_title": issue_title,
        "core_problem": str(latest.get("core_problem") or latest.get("status_message") or "Review body alignment and finish quality. / 复盘身体对线与动作收尾质量。"),
        "suggestion": str(latest.get("next_step_advice") or latest.get("quality_hint") or "Repeat the same action at moderate speed and keep structure stable. / 以中等速度重复动作，先保证结构稳定。"),
        "positive_feedback": str(latest.get("positive_feedback") or "A valid football action sequence was captured. / 系统已捕捉到有效足球动作序列。"),
        "status_message": str(latest.get("scoring_state_message") or latest.get("quality_hint") or summary_text),
        "observations": quality_result.get("observed", {}),
    }


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save_session_summary(summary):
    if not summary:
        return None
    SESSION_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = SESSION_EXPORT_DIR / f"session_{stamp}.json"
    payload = dict(summary)
    payload["generated_at"] = _now_iso()
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return str(out_path)


def _ema_points(prev_points, points, alpha=0.7):
    if prev_points is None:
        return points
    out = {}
    for k, v in points.items():
        pv = prev_points.get(k, v)
        out[k] = (pv[0] * alpha + v[0] * (1 - alpha), pv[1] * alpha + v[1] * (1 - alpha))
    return out


def _camera_backends():
    system = platform.system().lower()
    backends = []
    if system == "darwin":
        cap_avf = getattr(cv2, "CAP_AVFOUNDATION", None)
        if cap_avf is not None:
            backends.append(cap_avf)
    elif system == "windows":
        for name in ("CAP_DSHOW", "CAP_MSMF"):
            val = getattr(cv2, name, None)
            if val is not None:
                backends.append(val)
    elif system == "linux":
        cap_v4l2 = getattr(cv2, "CAP_V4L2", None)
        if cap_v4l2 is not None:
            backends.append(cap_v4l2)
    cap_any = getattr(cv2, "CAP_ANY", None)
    if cap_any is not None:
        backends.append(cap_any)
    return backends or [None]


def _open_camera(camera_index=None, camera_source=None):
    if camera_source:
        cap = cv2.VideoCapture(camera_source)
        if cap.isOpened():
            return cap
        cap.release()
        return None

    indices = [camera_index] if camera_index is not None else [0, 1, 2, 3, 4]
    dark_candidate = None
    for idx in indices:
        for backend in _camera_backends():
            cap = cv2.VideoCapture(idx) if backend is None else cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
            if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if hasattr(cv2, "CAP_PROP_FPS"):
                cap.set(cv2.CAP_PROP_FPS, 30)
            found_valid = False
            found_dark = False
            for _ in range(15):
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                mean_val = float(frame.mean())
                if mean_val > 3.0:
                    found_valid = True
                    break
                found_dark = True
            if found_valid:
                return cap
            if found_dark and dark_candidate is None:
                dark_candidate = cap
            else:
                cap.release()
    return dark_candidate


def diagnose_cameras(max_index=6, camera_source=None):
    results = []
    if camera_source:
        cap = cv2.VideoCapture(camera_source)
        opened = cap.isOpened()
        ok, frame = cap.read() if opened else (False, None)
        results.append({
            "source": camera_source,
            "opened": bool(opened),
            "read_ok": bool(ok),
            "shape": None if frame is None else list(frame.shape),
            "mean_brightness": None if frame is None else float(frame.mean()),
        })
        cap.release()
        return results

    for idx in range(max_index):
        cap = cv2.VideoCapture(idx)
        opened = cap.isOpened()
        ok, frame = cap.read() if opened else (False, None)
        results.append({
            "index": idx,
            "opened": bool(opened),
            "read_ok": bool(ok),
            "shape": None if frame is None else list(frame.shape),
            "mean_brightness": None if frame is None else float(frame.mean()),
        })
        cap.release()
    return results


def _to_xy(lm, w, h):
    return (lm.x * w, lm.y * h)


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
    if w <= INFER_MAX_WIDTH:
        return frame
    scale = INFER_MAX_WIDTH / float(w)
    new_size = (INFER_MAX_WIDTH, max(1, int(h * scale)))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)


def _angle(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    abx, aby = ax - bx, ay - by
    cbx, cby = cx - bx, cy - by
    dot = abx * cbx + aby * cby
    mag_ab = (abx ** 2 + aby ** 2) ** 0.5
    mag_cb = (cbx ** 2 + cby ** 2) ** 0.5
    if mag_ab == 0 or mag_cb == 0:
        return 0.0
    cosang = max(-1.0, min(1.0, dot / (mag_ab * mag_cb)))
    return np.degrees(np.arccos(cosang))


def _is_horizontal(points):
    l_sh = points["left_shoulder"]
    l_hip = points["left_hip"]
    l_ank = points["left_ankle"]
    torso_dx = abs(l_sh[0] - l_hip[0])
    torso_dy = abs(l_sh[1] - l_hip[1])
    leg_dy = abs(l_hip[1] - l_ank[1])
    return torso_dx > torso_dy and torso_dy < leg_dy * 0.35


def _full_body_ready(lm, frame_h):
    required = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.RIGHT_KNEE,
        mp_pose.PoseLandmark.LEFT_ANKLE,
        mp_pose.PoseLandmark.RIGHT_ANKLE,
    ]
    vis = [lm[idx].visibility for idx in required]
    vis_ok = min(vis) > 0.55
    ys = [lm[idx].y * frame_h for idx in required]
    body_span_ok = (max(ys) - min(ys)) > frame_h * 0.45
    return vis_ok and body_span_ok, float(sum(vis) / len(vis))


def _draw_skeleton(image, landmarks, w, h):
    # Hide dense face lines to keep a professional motion-focused look.
    face_ids = set(range(0, 11))
    for a, b in mp_pose.POSE_CONNECTIONS:
        if a in face_ids and b in face_ids:
            continue
        pa = landmarks[a]
        pb = landmarks[b]
        x1, y1 = int(pa.x * w), int(pa.y * h)
        x2, y2 = int(pb.x * w), int(pb.y * h)
        cv2.line(image, (x1, y1), (x2, y2), (100, 220, 255), 2, cv2.LINE_AA)
    for i, lm in enumerate(landmarks):
        if i in face_ids:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(image, (x, y), 3, (0, 210, 255), -1, cv2.LINE_AA)


def _subject_bounds(points):
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    return (
        int(min(xs)),
        int(min(ys)),
        int(max(xs)),
        int(max(ys)),
    )


def _torso_center(points):
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


def _update_target_lock(lock_state, points, full_body, vis_avg, body_span):
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
            "locked": False,
            "bounds": bounds,
        }

    prev_center = lock_state["center"]
    prev_span = max(1.0, float(lock_state["body_span"]))
    dx = center[0] - prev_center[0]
    dy = center[1] - prev_center[1]
    dist_ratio = float((dx * dx + dy * dy) ** 0.5 / max(prev_span, float(body_span), 1.0))
    size_ratio = float(abs(float(body_span) - prev_span) / prev_span)
    consistent = full_body and vis_avg > 0.55 and dist_ratio < 0.85 and size_ratio < 0.55

    next_state = dict(lock_state)
    next_state["bounds"] = bounds
    next_state["dist_ratio"] = dist_ratio
    next_state["size_ratio"] = size_ratio

    if consistent:
        alpha = 0.82
        next_state["center"] = (
            prev_center[0] * alpha + center[0] * (1 - alpha),
            prev_center[1] * alpha + center[1] * (1 - alpha),
        )
        next_state["body_span"] = prev_span * alpha + float(body_span) * (1 - alpha)
        next_state["stable_frames"] = min(40, int(next_state["stable_frames"]) + 1)
        next_state["misses"] = max(0, int(next_state["misses"]) - 1)
        next_state["switch_risk"] = max(0.0, 0.7 * dist_ratio + 0.3 * size_ratio - 0.10)
    else:
        next_state["stable_frames"] = max(0, int(next_state["stable_frames"]) - 2)
        next_state["misses"] = int(next_state["misses"]) + 1
        next_state["switch_risk"] = min(1.0, max(dist_ratio, size_ratio))
        if full_body and next_state["misses"] > 8:
            next_state["center"] = center
            next_state["body_span"] = float(body_span)
            next_state["stable_frames"] = 1
            next_state["misses"] = 0

    next_state["lock_score"] = max(
        0.0,
        min(1.0, float(next_state["stable_frames"]) / 8.0) * (1.0 - float(next_state["switch_risk"])),
    )
    next_state["locked"] = bool(next_state["stable_frames"] >= 8 and next_state["misses"] < 3)
    return next_state


def _draw_target_box(image, bounds, locked=True, switch_risk=0.0):
    x0, y0, x1, y1 = bounds
    color = (70, 200, 120) if locked else (0, 160, 255)
    if switch_risk > 0.45:
        color = (0, 120, 255)
    cv2.rectangle(image, (x0 - 10, y0 - 14), (x1 + 10, y1 + 12), color, 2, cv2.LINE_AA)
    label = "Primary Target" if locked else "Reacquiring Target"
    cv2.putText(image, label, (x0 - 8, max(18, y0 - 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def _soccer_event(points, prev_points, ball, prev_ball, contact, cooldown_s, last_event_ts):
    if prev_points is None:
        return "soccer_idle", 0.20, "hold athletic stance", last_event_ts, {
            "max_leg_speed": 0.0,
            "hip_jump_px": 0.0,
            "ball_speed_px": 0.0,
            "fast_side": "none",
            "support_side": "none",
        }

    now = time.time()
    rs = ((points["right_ankle"][0] - prev_points["right_ankle"][0]) ** 2 + (points["right_ankle"][1] - prev_points["right_ankle"][1]) ** 2) ** 0.5
    ls = ((points["left_ankle"][0] - prev_points["left_ankle"][0]) ** 2 + (points["left_ankle"][1] - prev_points["left_ankle"][1]) ** 2) ** 0.5
    max_leg_speed = max(rs, ls)
    fast_side = "right" if rs >= ls else "left"
    support_side = "left" if fast_side == "right" else "right"
    fast_foot = points["right_ankle"] if rs >= ls else points["left_ankle"]
    fast_knee = points["right_knee"] if rs >= ls else points["left_knee"]
    prev_hip_y = (prev_points["left_hip"][1] + prev_points["right_hip"][1]) * 0.5
    hip_y = (points["left_hip"][1] + points["right_hip"][1]) * 0.5
    hip_jump = prev_hip_y - hip_y

    diagnostics = {
        "max_leg_speed": float(max_leg_speed),
        "hip_jump_px": float(hip_jump),
        "ball_speed_px": 0.0,
        "fast_side": fast_side,
        "support_side": support_side,
    }
    if ball is not None and prev_ball is not None:
        bx = float(ball["x"]) - float(prev_ball["x"])
        by = float(ball["y"]) - float(prev_ball["y"])
        diagnostics["ball_speed_px"] = float((bx * bx + by * by) ** 0.5)

    if now - last_event_ts < cooldown_s:
        return "soccer_idle", 0.22, "reset stance for next action", last_event_ts, diagnostics

    if contact.get("contact") and diagnostics["ball_speed_px"] > 10 and max_leg_speed > 18:
        return "shoot_like", 0.80, "plant foot and lock ankle through contact", now, diagnostics
    if contact.get("contact") and diagnostics["ball_speed_px"] > 5 and max_leg_speed > 10:
        return "pass_like", 0.68, "open hips and finish toward target", now, diagnostics
    if max_leg_speed > 20 and fast_foot[1] < fast_knee[1] + 25:
        return "shoot_like", 0.72, "plant foot and lock ankle through contact", now, diagnostics
    if max_leg_speed > 12:
        return "pass_like", 0.58, "open hips and finish toward target", now, diagnostics
    if hip_jump > 9:
        return "jump_like", 0.63, "land softly, knees over toes", now, diagnostics
    return "soccer_idle", 0.30, "scan and keep center of mass stable", last_event_ts, diagnostics


def _soccer_phase(contact, diag):
    if contact.get("contact"):
        return "contact"
    if diag.get("ball_speed_px", 0.0) > 8.0:
        return "follow_through"
    if diag.get("max_leg_speed", 0.0) > 16.0:
        return "strike_swing"
    if diag.get("max_leg_speed", 0.0) > 8.0:
        return "approach"
    if diag.get("hip_jump_px", 0.0) > 9.0:
        return "airborne"
    return "set"


def _render_payload_to_frame(frame, payload):
    overlay = frame.copy()
    landmarks = payload.get("landmarks")
    if landmarks is not None:
        _draw_skeleton(overlay, landmarks, frame.shape[1], frame.shape[0])
    draw_ball(overlay, payload.get("ball"), payload.get("contact"))
    bounds = payload.get("bounds")
    if bounds is not None:
        _draw_target_box(
            overlay,
            bounds,
            locked=payload.get("target_locked", False),
            switch_risk=float(payload.get("switch_risk", 0.0)),
        )
    return cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)


def _render_live_screen(frame, state, payload, dev_mode, fps_value, current_camera_index, camera_source, switch_notice="", switch_notice_until=0.0, now_t=None):
    summary = dict(payload["summary"])
    if summary.get("ui_stage") == "active":
        event_card = state.get("event_card")
        if event_card and float(event_card.get("expires_at", 0.0)) > float(now_t or time.time()):
            summary["event_card"] = event_card
    clip_name = f"Live Capture / 采集录制  Cam:{current_camera_index}" if camera_source is None else "Live Capture / 采集录制"
    if summary.get("ui_stage") == "session_end":
        session_summary = summary.get("session_summary") or {}
        clip_name = Path(
            session_summary.get("recorded_video_path")
            or session_summary.get("saved_path")
            or session_summary.get("clip_name")
            or clip_name
        ).name
    render_card(
        frame,
        summary,
        dev=dev_mode,
        severity_hist=list(state["severity_hist"]),
        metrics=payload.get("metrics", {}),
        fps=fps_value,
        clip_name=clip_name,
    )
    stage = state.get("flow_stage", "home")
    if dev_mode:
        hint = "q=quit  space=start/stop  h=reset  r=finish  d=dev  c=next_cam  0-5=direct_cam"
    elif stage in {"preview", "home"}:
        hint = "1/2/3=choose template  space=ready  h=reset  q=quit"
    elif stage == "ready_to_record":
        hint = "space=start recording  h=reset  q=quit"
    elif stage == "recording":
        hint = "space=stop & analyze  r=finish  h=reset  q=quit"
    elif stage == "processing":
        hint = "processing... please wait  h=reset  q=quit"
    elif stage in {"review", "result"}:
        hint = "space=next session  h=reset  q=quit"
    else:
        hint = "r=finish & review  h=reset  q=quit"
    cv2.putText(frame, hint, (18, frame.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
    if state["black_count"] > 8:
        cv2.putText(
            frame,
            "Camera signal is dark/black. Change index or grant camera permission.",
            (18, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 120, 255),
            2,
            cv2.LINE_AA,
        )
    if switch_notice and now_t is not None and now_t < switch_notice_until:
        cv2.putText(
            frame,
            switch_notice,
            (18, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (80, 220, 160),
            2,
            cv2.LINE_AA,
        )


def _open_reader(camera_index=None, camera_source=None):
    cap = _open_camera(camera_index, camera_source)
    if cap is None:
        return None
    loop_on_eof = bool(camera_source) and Path(str(camera_source)).exists()
    return LatestFrameReader(cap, loop_on_eof=loop_on_eof).start()


def _handle_live_key(key, state, dev_mode, subject_ready, reader, current_camera_index, camera_source, football_rules=None):
    running = True
    switch_notice = None
    switched = False
    now_t = time.time()
    stage = str(state.get("flow_stage", "preview"))
    recording_active = stage == "recording"
    processing_active = stage == "processing"
    review_active = stage == "review"

    if key == ord("q"):
        if recording_active:
            video_path = _stop_recording_writer(state, now_t, reason="quit")
            if video_path:
                _launch_offline_analysis(state, video_path, now_t)
        elif review_active and state.get("post_session_summary") is not None:
            state["last_session_path"] = _save_session_summary(state["post_session_summary"])
        running = False
        return running, dev_mode, state, reader, current_camera_index, switch_notice, switched
    if key == ord("d"):
        dev_mode = not dev_mode
    if key == ord("h"):
        saved_path = state.get("last_session_path")
        _reset_capture_session(state, keep_last_session=True)
        state["last_session_path"] = saved_path
        return running, dev_mode, state, reader, current_camera_index, "Returned to preview", False
    if stage not in {"recording", "processing"} and key == ord("1"):
        state["selected_template"] = "passing_stability"
        state["session_goal"] = "Passing Stability / 传球稳定性"
        state["task_target"] = 1
        state["flow_stage"] = "preview"
        state["capture_stage"] = "preview"
    if stage not in {"recording", "processing"} and key == ord("2"):
        state["selected_template"] = "shooting_quality"
        state["session_goal"] = "Shooting Quality / 射门动作质量"
        state["task_target"] = 1
        state["flow_stage"] = "preview"
        state["capture_stage"] = "preview"
    if stage not in {"recording", "processing"} and key == ord("3"):
        state["selected_template"] = "first_touch_control"
        state["session_goal"] = "First-Touch Control / 停球控制"
        state["task_target"] = 1
        state["flow_stage"] = "preview"
        state["capture_stage"] = "preview"
    if key == ord(" "):
        if stage in {"preview", "ready_to_record"}:
            if not subject_ready:
                state["flow_stage"] = "preview"
                state["capture_stage"] = "preview"
                state["recording_hint"] = "先让单人入镜并锁定主目标，再开始录制。"
            else:
                fps_value = sum(state["fps_hist"]) / len(state["fps_hist"]) if state["fps_hist"] else 30.0
                frame_shape = state.get("last_frame_shape")
                if frame_shape is None:
                    state["recording_hint"] = "当前还没有稳定帧，请稍等一秒再按 SPACE。"
                else:
                    writer_path = _open_recording_writer(state, frame_shape, fps_value, now_t)
                    if writer_path is None:
                        state["flow_stage"] = "preview"
                        state["capture_stage"] = "preview"
                        state["recording_hint"] = "录制启动失败，请检查摄像头分辨率或磁盘空间。"
                    else:
                        state["recording_hint"] = "录制中，再按 SPACE 结束录制并开始离线分析。"
        elif recording_active:
            video_path = _stop_recording_writer(state, now_t, reason="space")
            if video_path:
                _launch_offline_analysis(state, video_path, now_t)
        elif processing_active:
            state["processing_hint"] = "离线分析进行中，请稍候。"
        elif review_active:
            min_until = float(state.get("result_min_until", 0.0))
            if now_t < min_until:
                hold_left = max(0.0, min_until - now_t)
                state["result_notice"] = f"Review in progress ({hold_left:.1f}s left). / 结果展示中（剩余 {hold_left:.1f} 秒）"
                state["result_notice_until"] = now_t + 1.2
            else:
                _reset_for_next_session(state)
    if key == ord("r"):
        if recording_active:
            video_path = _stop_recording_writer(state, now_t, reason="manual_finish")
            if video_path:
                _launch_offline_analysis(state, video_path, now_t)
        elif processing_active:
            state["analysis_cancel_requested"] = True
            _reset_for_next_session(state)
        elif review_active:
            if now_t >= float(state.get("result_min_until", 0.0)):
                _reset_for_next_session(state)
            else:
                state["result_notice"] = "Review in progress / 结果展示中，请稍候"
                state["result_notice_until"] = now_t + 1.2
        else:
            _reset_for_next_session(state)
    template_key_in_preview = stage in {"preview", "ready_to_record", "setup", "home"} and key in (ord("1"), ord("2"), ord("3"))
    if camera_source is None and stage not in {"recording", "processing"} and not template_key_in_preview and (key == ord("c") or key == ord("x") or ord("0") <= key <= ord("9")):
        requested_index = (current_camera_index + 1) % 6 if key in (ord("c"), ord("x")) else int(chr(key))
        new_reader = _open_reader(requested_index, None)
        if new_reader is not None:
            reader.stop()
            reader = new_reader
            current_camera_index = requested_index
            saved_path = state.get("last_session_path")
            state = _fresh_runtime_state(football_rules or state.get("football_rules"))
            state["last_session_path"] = saved_path
            switch_notice = f"Switched camera -> {requested_index}"
            switched = True
        else:
            switch_notice = f"Camera {requested_index} unavailable"
    return running, dev_mode, state, reader, current_camera_index, switch_notice, switched


def _analyze_live_frame(frame, pose, state, calibration, sport_label, sport_mode, profiler=None):
    state["analysis_frame_idx"] += 1
    now_t = time.time()
    t_total = time.perf_counter()
    flow_stage = state.get("flow_stage", "home")
    if profiler is not None:
        profiler.record_analysis()
    if state.get("workflow_mode") == LIVE_CAPTURE_MODE:
        return _analyze_capture_frame(frame, pose, state, calibration, sport_label, sport_mode, profiler=profiler)
    selected_template = state.get("selected_template", "passing_stability")
    template_meta = get_template_meta(selected_template)
    effective_sport_mode = "soccer_basic"
    mode_name = "football_quality / 足球专项质量评估"
    if state.get("flow_stage") == "result" and state.get("post_session_summary") is not None:
        hold_left = max(0.0, float(state.get("result_min_until", 0.0)) - now_t)
        can_continue = hold_left <= 0.0
        continue_hint = (
            "Press SPACE to continue next session / 按空格开始下一次检测"
            if can_continue
            else f"Review lock: {hold_left:.1f}s remaining / 结果展示中：剩余 {hold_left:.1f} 秒"
        )
        if now_t < float(state.get("result_notice_until", 0.0)) and state.get("result_notice"):
            continue_hint = state["result_notice"]
        session_summary = dict(state["post_session_summary"])
        session_summary["hold_left_s"] = hold_left
        session_summary["can_continue"] = can_continue
        session_summary["continue_hint"] = continue_hint
        payload = {
            "summary": {
                "ui_stage": "session_end",
                "mode_name": mode_name,
                "session_summary": session_summary,
            },
            "metrics": {},
            "landmarks": None,
            "ball": None,
            "contact": None,
            "bounds": None,
            "target_locked": False,
            "switch_risk": 0.0,
            "subject_ready": False,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "result")
        return payload

    if state.get("flow_stage") == "home":
        payload = {
            "summary": {
                "ui_stage": "home",
                "mode_name": mode_name,
                "selected_template": selected_template,
                "template_label": template_meta["label"],
                "program_title": "Football Action Quality System / 足球专项动作质量评估系统",
                "program_subtitle": "Score one football action by quality, not by mixed internal metrics / 按足球动作质量评分，而不是混合内部指标",
                "home_hint": "Press 1/2/3 to choose a training template. Press SPACE to continue / 按 1/2/3 选择训练模板，按空格继续",
                "templates": get_template_catalog(),
                "last_session_path": state.get("last_session_path"),
            },
            "metrics": {},
            "landmarks": None,
            "ball": None,
            "contact": None,
            "bounds": None,
            "target_locked": False,
            "switch_risk": 0.0,
            "subject_ready": False,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "home")
        return payload

    h, w = frame.shape[:2]
    pose_frame = _prepare_pose_frame(frame)
    t_pose = time.perf_counter()
    rgb = cv2.cvtColor(pose_frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    if profiler is not None:
        profiler.record("pose_infer", time.perf_counter() - t_pose, flow_stage, "pose")

    if not results.pose_landmarks:
        state["display_state"] = None
        state["event_card"] = None
        if profiler is not None and state.get("session_started"):
            profiler.record_gate("no_pose", False)
        payload = {
            "summary": {
                "ui_stage": "setup",
                "label": "no_pose",
                "mode_name": mode_name,
                "lock_score": 0.0,
                "full_body": False,
                "subject_ready": False,
                "start_ready": False,
                "setup_hint": "No pose detected / 未检测到人体姿态",
            },
            "metrics": {"visibility": 0.0, "stability": 0.0},
            "landmarks": None,
            "ball": None,
            "contact": None,
            "bounds": None,
            "target_locked": False,
            "switch_risk": 0.0,
            "subject_ready": False,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "no_pose")
        return payload

    lm = results.pose_landmarks.landmark
    points = {
        "left_shoulder": _to_xy(lm[mp_pose.PoseLandmark.LEFT_SHOULDER], w, h),
        "right_shoulder": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_SHOULDER], w, h),
        "left_elbow": _to_xy(lm[mp_pose.PoseLandmark.LEFT_ELBOW], w, h),
        "right_elbow": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_ELBOW], w, h),
        "left_wrist": _to_xy(lm[mp_pose.PoseLandmark.LEFT_WRIST], w, h),
        "right_wrist": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_WRIST], w, h),
        "left_hip": _to_xy(lm[mp_pose.PoseLandmark.LEFT_HIP], w, h),
        "right_hip": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_HIP], w, h),
        "left_knee": _to_xy(lm[mp_pose.PoseLandmark.LEFT_KNEE], w, h),
        "right_knee": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_KNEE], w, h),
        "left_ankle": _to_xy(lm[mp_pose.PoseLandmark.LEFT_ANKLE], w, h),
        "right_ankle": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_ANKLE], w, h),
    }

    prev_raw_points = state["raw_last_points"]
    if prev_raw_points is not None:
        diffs = [
            abs(points[k][0] - prev_raw_points[k][0]) + abs(points[k][1] - prev_raw_points[k][1])
            for k in points.keys()
        ]
        state["move_hist"].append(sum(diffs) / len(diffs))
    state["raw_last_points"] = points
    points = _ema_points(state["last_points"], points, alpha=0.68)
    prev_points = state["last_points"]
    state["last_points"] = points

    move_score = float(sum(state["move_hist"]) / len(state["move_hist"])) if state["move_hist"] else 0.0
    body_span = max(
        abs(points["left_shoulder"][1] - points["left_ankle"][1]),
        abs(points["right_shoulder"][1] - points["right_ankle"][1]),
        1.0,
    )
    move_ratio = move_score / body_span
    moving = move_ratio > 0.017

    full_body, vis_avg = _full_body_ready(lm, h)
    subject_signature = compute_subject_signature(frame, points)
    state["lock_state"] = update_target_lock(state["lock_state"], points, full_body, vis_avg, body_span, subject_signature)
    target_locked = bool(state["lock_state"]["locked"])
    lock_score = float(state["lock_state"]["lock_score"])
    target_status = "locked" if target_locked else ("target_lost" if state["lock_state"]["misses"] > 2 else "target_locking")
    if moving and full_body:
        state["active_frames"] = min(60, state["active_frames"] + 1)
    else:
        state["active_frames"] = max(0, state["active_frames"] - 2)
    analysis_active = state["session_started"] and state["active_frames"] >= 6 and target_locked
    subject_ready = full_body and target_locked

    if not state["session_started"]:
        if not full_body:
            setup_hint = "Step back until full body is visible / 请后退，保证全身入镜"
        elif not target_locked:
            setup_hint = "Hold still for target lock / 请保持稳定，等待主目标锁定"
        else:
            setup_hint = "Ready. Press SPACE to start / 已准备好，按空格开始"
        payload = {
            "summary": {
                "ui_stage": "setup",
                "mode_name": mode_name,
                "lock_score": lock_score,
                "full_body": full_body,
                "subject_ready": subject_ready,
                "start_ready": subject_ready,
                "setup_hint": setup_hint,
            },
            "metrics": {"visibility": vis_avg, "target_lock_score": lock_score},
            "landmarks": lm,
            "ball": None,
            "contact": None,
            "bounds": state["lock_state"]["bounds"],
            "target_locked": target_locked,
            "switch_risk": float(state["lock_state"]["switch_risk"]),
            "subject_ready": subject_ready,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "setup")
        return payload

    l_knee = _angle(points["left_hip"], points["left_knee"], points["left_ankle"])
    r_knee = _angle(points["right_hip"], points["right_knee"], points["right_ankle"])
    l_hip = _angle(points["left_shoulder"], points["left_hip"], points["left_knee"])
    r_hip = _angle(points["right_shoulder"], points["right_hip"], points["right_knee"])
    symmetry = abs(l_knee - r_knee)
    depth = max(0.0, min(1.0, (180.0 - min(l_knee, r_knee)) / 90.0))
    fppa_proxy = (180.0 - min(l_knee, r_knee))
    shoulder_w = abs(points["left_shoulder"][0] - points["right_shoulder"][0]) + 1e-6
    shoulder_mid_x = (points["left_shoulder"][0] + points["right_shoulder"][0]) * 0.5
    hip_mid_x = (points["left_hip"][0] + points["right_hip"][0]) * 0.5
    shoulder_mid_y = (points["left_shoulder"][1] + points["right_shoulder"][1]) * 0.5
    hip_mid_y = (points["left_hip"][1] + points["right_hip"][1]) * 0.5
    balance = abs(shoulder_mid_x - hip_mid_x) / shoulder_w
    trunk_dx = shoulder_mid_x - hip_mid_x
    trunk_dy = max(1e-6, abs(shoulder_mid_y - hip_mid_y))
    trunk_lean_deg = abs(np.degrees(np.arctan2(abs(trunk_dx), trunk_dy)))
    knee_dist = abs(points["left_knee"][0] - points["right_knee"][0])
    ankle_dist = abs(points["left_ankle"][0] - points["right_ankle"][0]) + 1e-6
    valgus_ratio = knee_dist / ankle_dist
    stability = max(0.0, min(1.0, 1.0 - move_score / 20.0))

    phase_hint = str(state.get("sequence_state", {}).get("phase", "set"))
    ball_stride = _ball_detect_stride_for(phase_hint, state["last_ball"])
    t_ball = time.perf_counter()
    ball_candidate = None
    should_detect_ball = (
        state["analysis_frame_idx"] % ball_stride == 0
        or state["last_ball"] is None
        or float(state["last_ball"].get("confidence", 0.0)) < 0.42
        or state["last_ball"].get("source") != "detected"
    )
    if should_detect_ball:
        ball_candidate = detect_ball(
            frame,
            ankles={"left_ankle": points["left_ankle"], "right_ankle": points["right_ankle"]},
            last_ball=state["last_ball"],
        )
    ball = state["ball_tracker"].update(ball_candidate, body_span_px=body_span)
    contact = estimate_contact(
        ball,
        {"left_ankle": points["left_ankle"], "right_ankle": points["right_ankle"]},
        body_span_px=body_span,
    )
    prev_ball = state["last_ball"]
    if ball is not None:
        state["last_ball"] = ball
        if ball.get("source") == "detected":
            state["ball_hist"].append(float(ball["confidence"]))
        else:
            state["ball_hist"].append(float(ball["confidence"]) * 0.7)
    elif state["last_ball"] is not None:
        state["ball_hist"].append(0.0)
    if profiler is not None:
        profiler.record("ball_pipeline", time.perf_counter() - t_ball, flow_stage, phase_hint)

    if effective_sport_mode == "soccer_basic":
        t_sequence = time.perf_counter()
        kin = compute_football_kinematics(
            points,
            prev_points,
            ball,
            prev_ball,
            contact,
            body_span,
            move_ratio,
        )
        sequence_snapshot = update_football_sequence(state["sequence_state"], kin, now_t)
        if profiler is not None:
            profiler.record("sequence_update", time.perf_counter() - t_sequence, flow_stage, sequence_snapshot.phase)
        t_temporal = time.perf_counter()
        temporal_prediction = update_temporal_classifier(state["temporal_state"], sequence_snapshot, kin, now_t)
        if profiler is not None:
            profiler.record("temporal_classify", time.perf_counter() - t_temporal, flow_stage, sequence_snapshot.phase)
        if temporal_prediction.confidence >= max(0.46, sequence_snapshot.phase_confidence - 0.04):
            action_label = temporal_prediction.label
            conf = 0.45 * sequence_snapshot.phase_confidence + 0.55 * temporal_prediction.confidence
        else:
            action_label = sequence_snapshot.action_label
            conf = sequence_snapshot.phase_confidence
        cue = "repeat the target football action clearly"
        if any(sequence_snapshot.events.values()):
            state["last_event_ts"] = now_t
    else:
        action_label = sport_label if sport_label else ("pushup" if _is_horizontal(points) else "squat")
        conf = 0.80
        cue = "maintain posture and tempo"
        kin = None
        sequence_snapshot = None
        temporal_prediction = None
    state["conf_ema"] = 0.85 * state["conf_ema"] + 0.15 * conf

    if analysis_active and effective_sport_mode != "soccer_basic":
        now_rep = time.time()
        if action_label == "squat":
            knee = min(l_knee, r_knee)
            if knee < 95:
                state["squat_stage"] = "down"
            if knee > 165 and state["squat_stage"] == "down" and (now_rep - state["last_rep_time"]) > 0.6:
                state["squat_reps"] += 1
                state["squat_stage"] = "up"
                state["last_rep_time"] = now_rep
        else:
            l_elb = _angle(points["left_shoulder"], points["left_elbow"], points["left_wrist"])
            r_elb = _angle(points["right_shoulder"], points["right_elbow"], points["right_wrist"])
            elbow = min(l_elb, r_elb)
            if elbow < 90:
                state["pushup_stage"] = "down"
            if elbow > 160 and state["pushup_stage"] == "down" and (now_rep - state["last_rep_time"]) > 0.6:
                state["pushup_reps"] += 1
                state["pushup_stage"] = "up"
                state["last_rep_time"] = now_rep

    rule_metrics = {
        "visibility": vis_avg,
        "symmetry": symmetry,
        "fppa_proxy_deg": fppa_proxy,
        "trunk_lean_deg": trunk_lean_deg,
        "valgus_ratio": valgus_ratio,
    }
    rule_severity, rule_issue, rule_cue, rule_refs = analyze_biomech(rule_metrics, action_label)
    action_for_hist = action_label if (sequence_snapshot is None or sequence_snapshot.sequence_active) else "soccer_idle"
    issue_for_hist = rule_issue if (sequence_snapshot is None or sequence_snapshot.sequence_ready) else "stable_motion"
    state["action_hist"].append(action_for_hist)
    state["issue_hist"].append(issue_for_hist)
    stable_action = _majority_label(state["action_hist"], action_label)
    stable_issue = _majority_label(state["issue_hist"], rule_issue)
    phase = sequence_snapshot.phase if sequence_snapshot is not None else "set"
    swing_side = sequence_snapshot.swing_side if sequence_snapshot is not None else "none"
    support_side = sequence_snapshot.support_side if sequence_snapshot is not None else "none"
    support_ball_ratio = sequence_snapshot.metrics["support_ball_ratio"] if sequence_snapshot is not None else 0.28
    swing_ball_ratio = sequence_snapshot.metrics["swing_ball_ratio"] if sequence_snapshot is not None else 0.16
    ball_speed_ratio = sequence_snapshot.metrics["ball_speed_ratio"] if sequence_snapshot is not None else 0.0
    support_ball_px = None if ball is None else support_ball_ratio * body_span
    swing_ball_px = None if ball is None else swing_ball_ratio * body_span
    brightness = float(frame.mean())
    body_fill_ratio = float(body_span / max(1.0, float(h)))
    ball_confidence = float(sum(state["ball_hist"]) / len(state["ball_hist"])) if state["ball_hist"] else 0.0
    t_reliability = time.perf_counter()
    reliability = evaluate_reliability(
        visibility=vis_avg,
        lock_score=lock_score,
        full_body=full_body,
        target_locked=target_locked,
        body_fill_ratio=body_fill_ratio,
        brightness=brightness,
        switch_risk=float(state["lock_state"]["switch_risk"]),
        appearance_score=float(state["lock_state"].get("appearance_score", 0.0)),
        ball_confidence=ball_confidence,
        ball_detected=ball is not None and ball.get("source") == "detected",
        phase_confidence=sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0,
        phase_locked=sequence_snapshot.phase_locked if sequence_snapshot is not None else False,
        sequence_ready=sequence_snapshot.sequence_ready if sequence_snapshot is not None else False,
    )
    if profiler is not None:
        profiler.record("reliability_gate", time.perf_counter() - t_reliability, flow_stage, phase)

    if effective_sport_mode == "soccer_basic":
        live_context = {
            "state": state,
            "now_t": now_t,
            "calibration": calibration,
            "selected_template": selected_template,
            "mode_name": mode_name,
            "sequence_snapshot": sequence_snapshot,
            "temporal_prediction": temporal_prediction,
            "reliability": reliability,
            "contact": contact,
            "ball": ball,
            "vis_avg": vis_avg,
            "target_locked": target_locked,
            "lock_score": lock_score,
            "target_status": target_status,
            "support_side": support_side,
            "swing_side": swing_side,
            "support_ball_ratio": support_ball_ratio,
            "swing_ball_ratio": swing_ball_ratio,
            "ball_speed_ratio": ball_speed_ratio,
            "balance": balance,
            "trunk_lean_deg": trunk_lean_deg,
            "symmetry": symmetry,
            "valgus_ratio": valgus_ratio,
            "body_span": body_span,
            "move_ratio": move_ratio,
            "full_body": full_body,
            "subject_ready": subject_ready,
            "phase": phase,
            "ball_confidence": ball_confidence,
            "brightness": brightness,
            "body_fill_ratio": body_fill_ratio,
            "stability": stability,
            "lm": lm,
            "metrics": {
                "knee_l": l_knee,
                "knee_r": r_knee,
                "hip_l": l_hip,
                "hip_r": r_hip,
                "depth": depth,
            },
            "ankle_dist": ankle_dist,
            "profiler": profiler,
        }
        payload = _build_soccer_live_payload(live_context)
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, phase)
        return payload

    football_metrics = {
        "support_ball_ratio": support_ball_ratio,
        "swing_ball_ratio": swing_ball_ratio,
        "ball_speed_ratio": ball_speed_ratio,
        "balance": balance,
        "trunk_lean_deg": trunk_lean_deg,
        "valgus_ratio": valgus_ratio,
        "symmetry": symmetry,
        "stability": stability,
        "ball_contact": 1.0 if contact.get("contact") else 0.0,
        "visibility": vis_avg,
        "sequence_confidence": sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0,
        "phase_locked": 1.0 if sequence_snapshot is not None and sequence_snapshot.phase_locked else 0.0,
    }
    t_score = time.perf_counter()
    action_quality = score_football_action(football_metrics, stable_action, selected_template)
    if profiler is not None:
        profiler.record("score_compute", time.perf_counter() - t_score, flow_stage, phase)
    risk_screen_norm = (100.0 - action_quality.action_safety_score) / 100.0
    score_ready = analysis_active and reliability.should_score
    display_technical_execution = action_quality.technical_execution_score if score_ready else 0.0
    display_control_stability = action_quality.control_stability_score if score_ready else 0.0
    display_action_safety = action_quality.action_safety_score if score_ready else 0.0
    display_key_issues = (
        [
            {"code": issue.code, "label": issue.label, "summary": issue.summary, "cue": issue.cue}
            for issue in action_quality.key_issues
        ]
        if score_ready
        else []
    )

    if not full_body:
        label = "full_body_required"
        severity = 0.0
        suggestion = "step back until shoulders, hips, knees, ankles are visible"
        state["conf_ema"] = 0.0
        reps = 0
        issue_show = "capture_quality_low"
        coach_summary = "Analysis is paused until the athlete is fully visible. / 当前未进入正式分析，请先保证全身入镜。"
        positive_feedback = "System is ready to analyze once setup is valid. / 一旦准备完成，系统即可开始专项分析。"
        overall_score = 0.0
    elif not target_locked:
        label = target_status
        severity = 0.0
        suggestion = "hold center frame until primary target locks"
        state["conf_ema"] *= 0.88
        reps = 0
        issue_show = "capture_quality_low"
        coach_summary = "Primary target is not stable yet, so scoring is intentionally withheld. / 当前主目标尚未稳定锁定，因此系统不会给出专项评分。"
        positive_feedback = "Keep one athlete centered and the product will switch into analysis. / 保持单一被检测者居中后，系统会进入分析状态。"
        overall_score = 0.0
    elif not analysis_active:
        label = "ready"
        severity = 0.0
        suggestion = "start movement to begin analysis"
        state["conf_ema"] *= 0.9
        reps = 0
        issue_show = "stable_motion"
        coach_summary = "The system is armed for the training goal, but a valid passing sequence has not started yet. / 系统已经准备好，但还没有进入有效传球序列。"
        positive_feedback = "Setup quality is acceptable; start a clear passing action to generate a score. / 当前准备状态合格，开始明确的传球动作后会生成专项评分。"
        overall_score = 0.0
    elif not reliability.should_score:
        label = stable_action if sequence_snapshot is not None and sequence_snapshot.sequence_active else "ready"
        severity = 0.0
        suggestion = cue if reliability.gate_reason == "phase_unlocked" else "improve capture and ball evidence before scoring"
        state["conf_ema"] *= 0.90
        reps = 0
        issue_show = "capture_quality_low" if reliability.gate_reason in {"pose_unstable", "target_unstable", "ball_unstable"} else "stable_motion"
        coach_summary = reliability.user_message
        positive_feedback = "The system is tracking the movement, but it is waiting for cleaner evidence before issuing a score. / 系统正在跟踪动作，但会等待更可靠证据后再输出评分。"
        overall_score = 0.0
    else:
        label = stable_action
        target_sev = max(0.0, min(1.0, 0.60 * risk_screen_norm + 0.40 * rule_severity))
        state["severity_ema"] = 0.80 * state["severity_ema"] + 0.20 * target_sev
        severity = state["severity_ema"]
        issue_show = action_quality.key_issues[0].code if action_quality.key_issues else stable_issue
        suggestion = action_quality.next_step_advice
        coach_summary = action_quality.core_problem
        positive_feedback = action_quality.positive_feedback
        overall_score = action_quality.overall_score
        reps = state["squat_reps"] if stable_action == "squat" else state["pushup_reps"]
        if effective_sport_mode == "soccer_basic":
            reps = 0

    if not score_ready:
        state["severity_ema"] *= 0.88
        severity = state["severity_ema"]

    technique_score = max(
        0.0,
        min(
            1.0,
            1.0
            - 0.34 * min(1.0, symmetry / 18.0)
            - 0.26 * min(1.0, trunk_lean_deg / 20.0)
            - 0.20 * min(1.0, abs(1.0 - valgus_ratio) / 0.45)
            - 0.20 * min(1.0, balance / 0.45),
        ),
    )
    control_score = max(
        0.0,
        min(
            1.0,
            0.32 * stability
            + 0.24 * vis_avg
            + 0.24 * lock_score
            + 0.20 * (float(sum(state["ball_hist"]) / len(state["ball_hist"])) if state["ball_hist"] else 0.0),
        ),
    )
    risk_score = max(0.0, min(1.0, severity))
    if effective_sport_mode != "soccer_basic" and analysis_active:
        overall_score = 100.0 * (0.45 * technique_score + 0.35 * control_score + 0.20 * (1.0 - risk_score))
    state["severity_hist"].append(float(severity))
    if score_ready:
        stats = state["session_stats"]
        stats["frames"] += 1
        stats["severity_sum"] += float(severity)
        stats["max_severity"] = max(float(stats["max_severity"]), float(severity))
        stats["main_score_sum"] += float(overall_score)
        stats["technical_sum"] += float(action_quality.technical_execution_score)
        stats["control_quality_sum"] += float(action_quality.control_stability_score)
        stats["safety_quality_sum"] += float(action_quality.action_safety_score)
        stats["technique_sum"] += float(technique_score)
        stats["control_sum"] += float(control_score)
        stats["risk_sum"] += float(risk_score)
        _count_label(stats["issue_counts"], issue_show)
        _count_label(stats["action_counts"], label)
        if effective_sport_mode == "soccer_basic" and sequence_snapshot is not None and sequence_snapshot.events["sequence_complete"]:
            state["last_counted_event_ts"] = float(now_t)
            stats["event_count"] += 1
            state["task_completed"] = min(int(state.get("task_target", 12)), int(state["task_completed"]) + 1)

    metrics = {
        "knee_l": l_knee,
        "knee_r": r_knee,
        "hip_l": l_hip,
        "hip_r": r_hip,
        "symmetry": symmetry,
        "balance": balance,
        "depth": depth,
        "trunk_lean_deg": trunk_lean_deg,
        "valgus_ratio": valgus_ratio,
        "visibility": vis_avg,
        "stability": stability,
        "move_ratio": move_ratio,
        "ball_confidence": float(sum(state["ball_hist"]) / len(state["ball_hist"])) if state["ball_hist"] else 0.0,
        "ball_contact": 1.0 if contact.get("contact") else 0.0,
        "contact_side": contact.get("side", "none"),
        "ball_track_source": ball.get("source", "lost") if ball is not None else "lost",
        "target_lock_score": lock_score,
        "target_switch_risk": float(state["lock_state"]["switch_risk"]),
        "target_appearance_score": float(state["lock_state"].get("appearance_score", 0.0)),
        "target_status": target_status,
        "phase": phase,
        "phase_confidence": sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0,
        "phase_locked": 1.0 if sequence_snapshot is not None and sequence_snapshot.phase_locked else 0.0,
        "support_side": support_side,
        "swing_side": swing_side,
        "classifier_confidence": temporal_prediction.confidence if temporal_prediction is not None else 0.0,
        "technique_score": technique_score,
        "control_score": control_score,
        "risk_score": risk_score,
        "support_ball_distance_px": 0.0 if support_ball_px is None else support_ball_px,
        "swing_ball_distance_px": 0.0 if swing_ball_px is None else swing_ball_px,
        "support_ball_ratio": support_ball_ratio,
        "swing_ball_ratio": swing_ball_ratio,
        "ball_speed_ratio": ball_speed_ratio,
        "main_score": overall_score,
        "technical_execution_score": display_technical_execution,
        "control_stability_score": display_control_stability,
        "action_safety_score": display_action_safety,
        "preparation_score": action_quality.phase_scores["preparation"] if score_ready else 0.0,
        "support_score": action_quality.phase_scores["support"] if score_ready else 0.0,
        "contact_score": action_quality.phase_scores["contact"] if score_ready else 0.0,
        "follow_through_score": action_quality.phase_scores["follow_through"] if score_ready else 0.0,
        "reliability_overall": reliability.overall,
        "reliability_pose": reliability.pose,
        "reliability_ball": reliability.ball,
        "reliability_stage": reliability.stage,
        "reliability_environment": reliability.environment,
    }
    if calibration is not None:
        scale = float(calibration.get("scale_m_per_px", 0.0))
        metrics["pixel_scale_cm"] = scale * 100.0
        metrics["ball_distance_m"] = float(contact["distance_px"]) * scale if contact.get("distance_px") is not None else 0.0
        metrics["stance_width_m"] = float(ankle_dist) * scale

    t_text = time.perf_counter()
    summary = {
        "label": label,
        "issue": issue_show,
        "confidence": reliability.overall if score_ready else 0.0,
        "overall_score": overall_score,
        "score_name": action_quality.score_name,
        "score_definition": action_quality.score_definition,
        "set": 1,
        "reps": reps,
        "rep_target": 12,
        "task_title": state.get("session_goal", "Training Session / 训练会话"),
        "task_completed": int(state.get("task_completed", 0)),
        "task_target": int(state.get("task_target", 12)),
        "severity": severity,
        "suggestion": suggestion,
        "coach_summary": action_quality.one_line_summary if analysis_active else coach_summary,
        "problem_title": "Optimization Point / 可优化点" if analysis_active and overall_score >= 80.0 else "Core Problem / 核心问题",
        "core_problem": coach_summary,
        "issue_phase_label": phase,
        "positive_feedback": positive_feedback,
        "template_label": action_quality.template_label,
        "technical_execution_score": display_technical_execution,
        "control_stability_score": display_control_stability,
        "action_safety_score": display_action_safety,
        "score_ready": score_ready,
        "score_gate_reason": reliability.gate_reason,
        "show_event_card": score_ready and sequence_snapshot is not None and sequence_snapshot.sequence_active,
        "classifier_label": temporal_prediction.label if temporal_prediction is not None else "",
        "classifier_confidence": temporal_prediction.confidence if temporal_prediction is not None else 0.0,
        "key_issues": display_key_issues,
        "level_label": action_quality.level_label if score_ready else "",
        "mode_name": mode_name,
        "calibrated": calibration is not None,
        "phase": phase,
        "target_status": target_status,
        "support_side": support_side,
        "swing_side": swing_side,
        "technique_score": technique_score,
        "control_score": control_score,
        "risk_score": risk_score,
        "ball_track_source": ball.get("source", "lost") if ball is not None else "lost",
        "raw": (
            f"active={analysis_active} ready={score_ready} phase={phase} p_conf={sequence_snapshot.phase_confidence if sequence_snapshot is not None else 0.0:.2f} "
            f"motion={move_ratio:.3f} swing={kin.swing_speed_ratio if kin is not None else 0.0:.3f} support={kin.support_speed_ratio if kin is not None else 0.0:.3f} "
            f"ball={ball_speed_ratio:.3f} contact={contact.get('side', 'none')} lock={lock_score:.2f} trust={reliability.overall:.2f} "
            f"gate={reliability.gate_reason} refs={','.join(rule_refs)}"
        ),
    }
    if profiler is not None:
        profiler.record("text_build", time.perf_counter() - t_text, flow_stage, phase)
        profiler.record_gate(reliability.gate_reason, score_ready)
    state["display_state"] = _update_display_state(state["display_state"], summary, metrics, now_t)
    state["event_card"] = _update_event_card(state.get("event_card"), state["display_state"]["summary"], now_t)

    payload = {
        "summary": state["display_state"]["summary"],
        "metrics": state["display_state"]["metrics"],
        "landmarks": lm,
        "ball": ball,
        "contact": contact,
        "bounds": state["lock_state"]["bounds"],
        "target_locked": target_locked,
        "switch_risk": float(state["lock_state"]["switch_risk"]),
        "subject_ready": subject_ready,
    }
    state["last_render_payload"] = payload
    if profiler is not None:
        profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, phase)
    return payload


def _analyze_capture_frame(frame, pose, state, calibration, sport_label, sport_mode, profiler=None):
    state["analysis_frame_idx"] += 1
    now_t = time.time()
    t_total = time.perf_counter()
    flow_stage = str(state.get("flow_stage", "preview"))
    if profiler is not None:
        profiler.record_analysis()

    state["last_frame_shape"] = frame.shape
    selected_template = state.get("selected_template", "passing_stability")
    template_meta = get_template_meta(selected_template)
    mode_name = (
        f"{OFFLINE_ANALYSIS_MODE} / 离线分析模式"
        if flow_stage == "review" or state.get("analysis_mode") == OFFLINE_ANALYSIS_MODE
        else f"{LIVE_CAPTURE_MODE} / 采集录制模式"
    )

    if flow_stage == "review" and state.get("post_session_summary") is not None:
        hold_left = max(0.0, float(state.get("result_min_until", 0.0)) - now_t)
        can_continue = hold_left <= 0.0
        continue_hint = (
            "Press SPACE to continue next session / 按空格开始下一次检测"
            if can_continue
            else f"Review lock: {hold_left:.1f}s remaining / 结果展示中：剩余 {hold_left:.1f} 秒"
        )
        if now_t < float(state.get("result_notice_until", 0.0)) and state.get("result_notice"):
            continue_hint = state["result_notice"]
        session_summary = dict(state["post_session_summary"])
        session_summary["hold_left_s"] = hold_left
        session_summary["can_continue"] = can_continue
        session_summary["continue_hint"] = continue_hint
        payload = {
            "summary": {
                "ui_stage": "session_end",
                "mode_name": mode_name,
                "session_summary": session_summary,
            },
            "metrics": {},
            "landmarks": None,
            "ball": None,
            "contact": None,
            "bounds": None,
            "target_locked": False,
            "switch_risk": 0.0,
            "subject_ready": False,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "review")
        return payload

    h, w = frame.shape[:2]
    pose_frame = _prepare_pose_frame(frame)
    t_pose = time.perf_counter()
    rgb = cv2.cvtColor(pose_frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    if profiler is not None:
        profiler.record("pose_infer", time.perf_counter() - t_pose, flow_stage, "capture")

    if not results.pose_landmarks:
        if state.get("flow_stage") == "recording":
            _append_recording_frame(state, frame)
        state["display_state"] = None
        state["event_card"] = None
        payload = {
            "summary": {
                "ui_stage": _capture_stage_to_ui_stage(flow_stage),
                "mode_name": mode_name,
                "capture_stage": flow_stage,
                "selected_template": selected_template,
                "template_label": template_meta["label"],
                "label": "ready",
                "issue": "capture_quality_low",
                "confidence": 0.0,
                "severity": 0.0,
                "overall_score": 0.0,
                "setup_hint": "No pose detected / 未检测到人体姿态",
                "recording": flow_stage == "recording",
                "processing": flow_stage == "processing",
                "recording_hint": state.get("recording_hint", ""),
                "processing_hint": state.get("processing_hint", ""),
                "start_ready": False,
                "subject_ready": False,
                "lock_score": 0.0,
                "full_body": False,
                "recording_frame_count": int(state.get("recording_frame_count", 0) or 0),
                "recording_video_path": state.get("recording_video_path"),
                "recording_elapsed_s": max(0.0, now_t - float(state.get("recording_started_at") or now_t)) if state.get("recording_started_at") else 0.0,
                "analysis_job_running": bool(state.get("analysis_job_running", False)),
                "analysis_job_done": bool(state.get("analysis_job_done", False)),
                "analysis_job_error": str(state.get("analysis_job_error", "")),
                "analysis_mode": state.get("analysis_mode", LIVE_CAPTURE_MODE),
                "task_title": state.get("session_goal", "Training Session / 训练会话"),
                "task_completed": int(state.get("task_completed", 0)),
                "task_target": int(state.get("task_target", 1)),
            },
            "metrics": {"visibility": 0.0, "stability": 0.0, "target_lock_score": 0.0, "move_ratio": 0.0},
            "landmarks": None,
            "ball": None,
            "contact": None,
            "bounds": None,
            "target_locked": False,
            "switch_risk": 0.0,
            "subject_ready": False,
        }
        state["last_render_payload"] = payload
        if profiler is not None:
            profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "no_pose")
        return payload

    lm = results.pose_landmarks.landmark
    points = {
        "left_shoulder": _to_xy(lm[mp_pose.PoseLandmark.LEFT_SHOULDER], w, h),
        "right_shoulder": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_SHOULDER], w, h),
        "left_elbow": _to_xy(lm[mp_pose.PoseLandmark.LEFT_ELBOW], w, h),
        "right_elbow": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_ELBOW], w, h),
        "left_wrist": _to_xy(lm[mp_pose.PoseLandmark.LEFT_WRIST], w, h),
        "right_wrist": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_WRIST], w, h),
        "left_hip": _to_xy(lm[mp_pose.PoseLandmark.LEFT_HIP], w, h),
        "right_hip": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_HIP], w, h),
        "left_knee": _to_xy(lm[mp_pose.PoseLandmark.LEFT_KNEE], w, h),
        "right_knee": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_KNEE], w, h),
        "left_ankle": _to_xy(lm[mp_pose.PoseLandmark.LEFT_ANKLE], w, h),
        "right_ankle": _to_xy(lm[mp_pose.PoseLandmark.RIGHT_ANKLE], w, h),
    }

    prev_raw_points = state["raw_last_points"]
    if prev_raw_points is not None:
        diffs = [
            abs(points[k][0] - prev_raw_points[k][0]) + abs(points[k][1] - prev_raw_points[k][1])
            for k in points.keys()
        ]
        state["move_hist"].append(sum(diffs) / len(diffs))
    state["raw_last_points"] = points
    points = _ema_points(state["last_points"], points, alpha=0.68)
    prev_points = state["last_points"]
    state["last_points"] = points

    move_score = float(sum(state["move_hist"]) / len(state["move_hist"])) if state["move_hist"] else 0.0
    body_span = max(
        abs(points["left_shoulder"][1] - points["left_ankle"][1]),
        abs(points["right_shoulder"][1] - points["right_ankle"][1]),
        1.0,
    )
    move_ratio = move_score / body_span
    moving = move_ratio > 0.017

    full_body, vis_avg = _full_body_ready(lm, h)
    subject_signature = compute_subject_signature(frame, points)
    state["lock_state"] = update_target_lock(state["lock_state"], points, full_body, vis_avg, body_span, subject_signature)
    target_locked = bool(state["lock_state"]["locked"])
    lock_score = float(state["lock_state"]["lock_score"])
    target_status = "locked" if target_locked else ("target_lost" if state["lock_state"]["misses"] > 2 else "target_locking")
    subject_ready = full_body and target_locked
    body_fill_ratio = float(body_span / max(1.0, float(h)))
    switch_risk = float(state["lock_state"]["switch_risk"])

    if flow_stage in {"preview", "setup"}:
        if subject_ready:
            state["flow_stage"] = "ready_to_record"
            state["capture_stage"] = "ready_to_record"
            state["recording_hint"] = "已准备好，按 SPACE 开始录制。"
        else:
            state["flow_stage"] = "preview"
            state["capture_stage"] = "preview"
            state["recording_hint"] = "先让单人入镜并锁定主目标，再开始录制。"

    if state["flow_stage"] == "recording":
        _append_recording_frame(state, frame)
        state["recording_motion_peak"] = max(float(state.get("recording_motion_peak", 0.0) or 0.0), float(move_ratio))
        if moving and subject_ready:
            state["recording_motion_started"] = True
            state["recording_idle_frames"] = 0
        elif state.get("recording_motion_started"):
            state["recording_idle_frames"] = int(state.get("recording_idle_frames", 0) or 0) + 1
        if _maybe_auto_stop_recording(state, move_ratio, subject_ready, now_t):
            video_path = _stop_recording_writer(state, now_t, reason="auto")
            if video_path:
                _launch_offline_analysis(state, video_path, now_t)
        else:
            state["recording_hint"] = "录制中，再按 SPACE 结束录制并开始离线分析。"
    elif state["flow_stage"] == "processing":
        state["processing_hint"] = state.get("processing_hint") or "录制完成，正在离线分析..."

    if state["flow_stage"] == "ready_to_record" and not subject_ready:
        state["flow_stage"] = "preview"
        state["capture_stage"] = "preview"

    metrics = {
        "visibility": vis_avg,
        "stability": max(0.0, min(1.0, 1.0 - move_score / 20.0)),
        "move_ratio": move_ratio,
        "body_span_px": body_span,
        "target_lock_score": lock_score,
        "target_switch_risk": switch_risk,
        "target_appearance_score": float(state["lock_state"].get("appearance_score", 0.0)),
        "target_status": target_status,
        "phase": state.get("capture_stage", state.get("flow_stage", "preview")),
        "support_side": "none",
        "swing_side": "none",
        "analysis_mode": state.get("analysis_mode", LIVE_CAPTURE_MODE),
        "recording_frame_count": int(state.get("recording_frame_count", 0) or 0),
    }

    if calibration is not None:
        scale = float(calibration.get("scale_m_per_px", 0.0))
        metrics["pixel_scale_cm"] = scale * 100.0
        metrics["stance_width_m"] = float(abs(points["left_ankle"][0] - points["right_ankle"][0])) * scale

    summary = {
        "ui_stage": _capture_stage_to_ui_stage(state.get("flow_stage", "preview")),
        "mode_name": mode_name,
        "capture_stage": state.get("flow_stage", "preview"),
        "selected_template": selected_template,
        "template_label": template_meta["label"],
        "label": "ready" if subject_ready or flow_stage != "recording" else "recording",
        "issue": "stable_motion" if subject_ready else "capture_quality_low",
        "confidence": float(lock_score) if subject_ready else 0.0,
        "severity": 0.0,
        "overall_score": 0.0,
        "setup_hint": state.get("recording_hint")
        or ("Ready. Press SPACE to begin recording / 已就绪，按空格开始录制" if subject_ready else "Move into frame and lock the target / 进入画面并锁定主目标"),
        "recording": state.get("flow_stage") == "recording",
        "processing": state.get("flow_stage") == "processing",
        "start_ready": subject_ready and state.get("flow_stage") != "recording",
        "subject_ready": subject_ready,
        "lock_score": lock_score,
        "full_body": full_body,
        "recording_hint": state.get("recording_hint", ""),
        "processing_hint": state.get("processing_hint", ""),
        "recording_frame_count": int(state.get("recording_frame_count", 0) or 0),
        "recording_video_path": state.get("recording_video_path"),
        "recording_elapsed_s": max(0.0, now_t - float(state.get("recording_started_at") or now_t)) if state.get("recording_started_at") else 0.0,
        "analysis_job_running": bool(state.get("analysis_job_running", False)),
        "analysis_job_done": bool(state.get("analysis_job_done", False)),
        "analysis_job_error": str(state.get("analysis_job_error", "")),
        "analysis_mode": state.get("analysis_mode", LIVE_CAPTURE_MODE),
        "task_title": state.get("session_goal", "Training Session / 训练会话"),
        "task_completed": int(state.get("task_completed", 0)),
        "task_target": int(state.get("task_target", 1)),
        "clip_name": str(state.get("recording_video_path") or "Live Capture / 采集录制"),
        "coach_summary": state.get("recording_hint") or state.get("processing_hint") or "",
    }
    state["display_state"] = _update_display_state(state["display_state"], summary, metrics, now_t)
    state["event_card"] = _update_event_card(state.get("event_card"), state["display_state"]["summary"], now_t)

    payload = {
        "summary": state["display_state"]["summary"],
        "metrics": state["display_state"]["metrics"],
        "landmarks": lm,
        "ball": None,
        "contact": None,
        "bounds": state["lock_state"]["bounds"],
        "target_locked": target_locked,
        "switch_risk": switch_risk,
        "subject_ready": subject_ready,
    }
    state["last_render_payload"] = payload
    if profiler is not None:
        profiler.record("analysis_total", time.perf_counter() - t_total, flow_stage, "capture")
    return payload


def run_live(
    camera_index=None,
    camera_source=None,
    sport_label=None,
    sport_mode="auto",
    calibration_path=None,
    profile_output=None,
    max_runtime_s=None,
    headless=False,
    profile_label="live",
):
    football_rules = load_football_rules()
    reader = _open_reader(camera_index=camera_index, camera_source=camera_source)
    if reader is None:
        raise SystemExit("Failed to open camera. Try --camera_index 0/1/2 or provide --camera_source URL.")

    calibration = load_calibration(calibration_path) if calibration_path else None
    current_camera_index = 0 if camera_index is None else camera_index
    switch_notice = ""
    switch_notice_until = 0.0

    pose = mp_pose.Pose(
        model_complexity=0,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    dev_mode = False
    state = _fresh_runtime_state(football_rules)
    prev_render_t = time.time()
    last_analysis_t = 0.0
    payload = None
    subject_ready = False
    profiler = RuntimeProfiler(label=profile_label) if (profile_output or max_runtime_s is not None) else None
    run_started_at = time.time()
    auto_profile = headless and max_runtime_s is not None

    while True:
        loop_t = time.perf_counter()
        flow_hint = state.get("flow_stage", "preview")
        phase_hint = "set" if payload is None else str(payload.get("metrics", {}).get("phase", payload.get("summary", {}).get("phase", "set")))
        t_capture = time.perf_counter()
        frame, frame_ts = reader.read()
        if profiler is not None:
            profiler.record("capture_read", time.perf_counter() - t_capture, flow_hint, phase_hint)
        if frame is None:
            time.sleep(0.005)
            if max_runtime_s is not None and (time.time() - run_started_at) >= float(max_runtime_s):
                break
            continue
        if profiler is not None:
            profiler.record_frame()

        t_prep = time.perf_counter()
        frame = _trim_letterbox(frame)
        if profiler is not None:
            profiler.record("frame_prep", time.perf_counter() - t_prep, flow_hint, phase_hint)
        now_t = time.time()
        dt = max(1e-6, now_t - prev_render_t)
        prev_render_t = now_t
        state["fps_hist"].append(1.0 / dt)
        if frame.mean() < 2.0:
            state["black_count"] += 1
        else:
            state["black_count"] = 0

        phase_hint = "set" if payload is None else str(payload.get("metrics", {}).get("phase", payload.get("summary", {}).get("phase", "set")))
        analysis_interval = _analysis_interval_for(state.get("flow_stage", "preview"), phase_hint)
        if payload is None or (now_t - last_analysis_t) >= analysis_interval:
            payload = _analyze_live_frame(frame, pose, state, calibration, sport_label, sport_mode, profiler=profiler)
            subject_ready = bool(payload.get("subject_ready", False))
            last_analysis_t = now_t

        if (
            state.get("workflow_mode") == LIVE_CAPTURE_MODE
            and state.get("flow_stage") == "processing"
            and state.get("analysis_job_done")
            and state.get("offline_analysis_result") is not None
        ):
            session_summary = _build_offline_review_summary(state, state.get("offline_analysis_result"), now_t)
            saved_path = session_summary.get("saved_path")
            if saved_path:
                state["last_session_path"] = saved_path
            _enter_review_stage(state, session_summary, now_t)
            payload = None
            last_analysis_t = 0.0

        if auto_profile:
            elapsed = time.time() - run_started_at
            if state.get("flow_stage") == "preview" and elapsed > 0.4:
                state["flow_stage"] = "ready_to_record"
                state["capture_stage"] = "ready_to_record"
            elif state.get("flow_stage") == "ready_to_record" and subject_ready and elapsed > 1.0:
                fps_value = sum(state["fps_hist"]) / len(state["fps_hist"]) if state["fps_hist"] else 30.0
                frame_shape = state.get("last_frame_shape") or frame.shape
                writer_path = _open_recording_writer(state, frame_shape, fps_value, time.time())
                if writer_path is not None:
                    payload = None
                    last_analysis_t = 0.0
            elif state.get("flow_stage") == "recording" and elapsed > float(max_runtime_s) * 0.78:
                video_path = _stop_recording_writer(state, time.time(), reason="auto_profile")
                if video_path:
                    _launch_offline_analysis(state, video_path, time.time())
            elif state.get("flow_stage") == "processing" and state.get("analysis_job_done") and state.get("offline_analysis_result") is not None:
                session_summary = _build_offline_review_summary(state, state.get("offline_analysis_result"), time.time())
                saved_path = session_summary.get("saved_path")
                if saved_path:
                    state["last_session_path"] = saved_path
                _enter_review_stage(state, session_summary, time.time())
                payload = None
                last_analysis_t = 0.0

        render_frame = frame.copy()
        if payload is not None and payload.get("summary", {}).get("ui_stage") == "active":
            t_overlay = time.perf_counter()
            render_frame = _render_payload_to_frame(render_frame, payload)
            if profiler is not None:
                profiler.record("overlay_render", time.perf_counter() - t_overlay, state.get("flow_stage", "home"), phase_hint)
        if payload is not None:
            t_ui = time.perf_counter()
            _render_live_screen(
                render_frame,
                state,
                payload,
                dev_mode,
                sum(state["fps_hist"]) / len(state["fps_hist"]) if state["fps_hist"] else 0.0,
                current_camera_index,
                camera_source,
                switch_notice=switch_notice,
                switch_notice_until=switch_notice_until,
                now_t=now_t,
            )
            if profiler is not None:
                profiler.record("ui_render", time.perf_counter() - t_ui, state.get("flow_stage", "home"), phase_hint)

        if not headless:
            cv2.imshow("AI Coach Live", render_frame)
            key = cv2.waitKey(1) & 0xFF
        else:
            key = 255
        if key != 255:
            running, dev_mode, state, reader, current_camera_index, notice, switched = _handle_live_key(
                key,
                state,
                dev_mode,
                subject_ready,
                reader,
                current_camera_index,
                camera_source,
                football_rules=football_rules,
            )
            if notice:
                switch_notice = notice
                switch_notice_until = time.time() + 1.5
            if switched:
                payload = None
                subject_ready = False
                last_analysis_t = 0.0
                prev_render_t = time.time()
            if not running:
                break
        if profiler is not None:
            profiler.record("loop_total", time.perf_counter() - loop_t, state.get("flow_stage", "home"), phase_hint)
        if max_runtime_s is not None and (time.time() - run_started_at) >= float(max_runtime_s):
            break

    reader.stop()
    if not headless:
        cv2.destroyAllWindows()
    if profiler is not None and profile_output:
        return profiler.save(profile_output)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera_index", type=int, default=None)
    ap.add_argument("--camera_source", default=None)
    ap.add_argument("--sport_label", default=None)
    ap.add_argument("--sport_mode", choices=["auto", "soccer_basic"], default="soccer_basic")
    ap.add_argument("--calibration_path", default="calibration/user_profile.json")
    ap.add_argument("--profile_output", default=None)
    ap.add_argument("--profile_label", default="live")
    ap.add_argument("--max_runtime_s", type=float, default=None)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    out = run_live(
        camera_index=args.camera_index,
        camera_source=args.camera_source,
        sport_label=args.sport_label,
        sport_mode=args.sport_mode,
        calibration_path=args.calibration_path,
        profile_output=args.profile_output,
        max_runtime_s=args.max_runtime_s,
        headless=args.headless,
        profile_label=args.profile_label,
    )
    if out:
        print(out)


if __name__ == "__main__":
    main()
