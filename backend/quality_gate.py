from __future__ import annotations

from typing import Any, Dict, List, Optional


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _format_ratio(value: float) -> float:
    return _clamp(float(value), 0.0, 1.0)


def evaluate_global_quality_gate(
    *,
    run_data: Dict[str, Any],
    metrics: Dict[str, Any],
    rules: Dict[str, Any],
    action_name: Optional[str] = None,
) -> Dict[str, Any]:
    gate = dict(rules.get("global_quality_gate", {}))
    fps_outcome = float(gate.get("min_video_fps_outcome", 30.0))
    fps_technique = float(gate.get("min_video_fps_technique", 60.0))
    min_pose_visibility = float(gate.get("min_pose_visibility", 0.75))
    min_pose_presence = float(gate.get("min_pose_presence", 0.75))
    min_visible_frame_ratio = float(gate.get("min_visible_frame_ratio", 0.85))
    max_ball_track_missing_ratio = float(gate.get("max_ball_track_missing_ratio", 0.10))

    frame_count = int(run_data.get("frame_count", 0) or 0)
    valid_pose_frames = int(run_data.get("valid_pose_frames", 0) or 0)
    ball_frames = int(run_data.get("ball_frames", 0) or 0)
    fps = float(run_data.get("fps", 0.0) or 0.0)

    pose_presence = _format_ratio(valid_pose_frames / max(1, frame_count))
    visible_frame_ratio = _format_ratio(valid_pose_frames / max(1, frame_count))
    pose_visibility = float(metrics.get("visibility", 0.0) or 0.0)
    ball_track_missing_ratio = _format_ratio(1.0 - (ball_frames / max(1, frame_count)))

    triggered_rules: List[Dict[str, Any]] = []
    fail_reasons: List[str] = []

    def add_rule(rule_id: str, reason: str, severity: str = "fail") -> None:
        triggered_rules.append(
            {
                "id": rule_id,
                "severity": severity,
                "reason": reason,
            }
        )
        fail_reasons.append(reason)

    if fps < fps_outcome:
        add_rule(
            "video_quality_fail",
            f"视频帧率过低，当前 {fps:.1f}fps，低于结果评分所需的 {fps_outcome:.0f}fps。",
        )
    elif fps < fps_technique:
        add_rule(
            "video_quality_degraded",
            f"视频帧率只有 {fps:.1f}fps，能做结果判断，但不适合做微观技术评分。",
            severity="warn",
        )

    if pose_presence < min_pose_presence:
        add_rule(
            "pose_presence_low",
            f"姿态可用帧比例偏低，当前 {pose_presence:.2%}，低于门槛 {min_pose_presence:.2%}。",
        )

    if visible_frame_ratio < min_visible_frame_ratio:
        add_rule(
            "visible_frame_ratio_low",
            f"可见帧比例偏低，当前 {visible_frame_ratio:.2%}，低于门槛 {min_visible_frame_ratio:.2%}。",
        )

    if pose_visibility < min_pose_visibility:
        add_rule(
            "pose_visibility_low",
            f"平均姿态可见度偏低，当前 {pose_visibility:.2f}，低于门槛 {min_pose_visibility:.2f}。",
        )

    if ball_track_missing_ratio > max_ball_track_missing_ratio:
        add_rule(
            "ball_track_missing_ratio_high",
            f"球轨迹缺失比例偏高，当前 {ball_track_missing_ratio:.2%}，高于门槛 {max_ball_track_missing_ratio:.2%}。",
        )

    hard_fail = any(item["id"] in {"video_quality_fail", "pose_presence_low", "visible_frame_ratio_low", "pose_visibility_low", "ball_track_missing_ratio_high"} for item in triggered_rules)
    degrade_only = any(item["id"] == "video_quality_degraded" for item in triggered_rules) and not hard_fail

    if hard_fail:
        quality_status = "fail"
    elif degrade_only:
        quality_status = "outcome_only"
    else:
        quality_status = "pass"

    allow_micro_technique_score = quality_status == "pass"
    hide_micro_technique_score = not allow_micro_technique_score
    should_reshoot = quality_status != "pass"

    if should_reshoot and not fail_reasons:
        fail_reasons.append("视频质量不足，建议重拍。")

    reshoot_hint = "请重拍更清晰的全身视频，确保球、支撑脚和关键触球瞬间都入镜。"
    if fps < fps_outcome:
        reshoot_hint = "请使用更高帧率的视频重拍，建议 60fps 以上并保证全身入镜。"
    elif ball_track_missing_ratio > max_ball_track_missing_ratio:
        reshoot_hint = "请让球完整入镜并减少遮挡，方便系统稳定追踪球轨迹。"
    elif pose_visibility < min_pose_visibility:
        reshoot_hint = "请让身体关键关节更清晰入镜，避免遮挡和背光。"

    return {
        "action_name": action_name,
        "quality_status": quality_status,
        "passed": quality_status == "pass",
        "allow_micro_technique_score": allow_micro_technique_score,
        "hide_micro_technique_score": hide_micro_technique_score,
        "should_reshoot": should_reshoot,
        "reshoot_hint": reshoot_hint,
        "thresholds": {
            "min_video_fps_outcome": fps_outcome,
            "min_video_fps_technique": fps_technique,
            "min_pose_visibility": min_pose_visibility,
            "min_pose_presence": min_pose_presence,
            "min_visible_frame_ratio": min_visible_frame_ratio,
            "max_ball_track_missing_ratio": max_ball_track_missing_ratio,
        },
        "observed": {
            "fps": fps,
            "pose_presence": pose_presence,
            "visible_frame_ratio": visible_frame_ratio,
            "pose_visibility": pose_visibility,
            "ball_track_missing_ratio": ball_track_missing_ratio,
            "frame_count": frame_count,
            "valid_pose_frames": valid_pose_frames,
            "ball_frames": ball_frames,
        },
        "triggered_rules": triggered_rules,
        "fail_reasons": fail_reasons,
    }
