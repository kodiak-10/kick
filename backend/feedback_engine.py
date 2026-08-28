from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from rules_loader import get_action_rules, load_football_rules


_METRIC_LABELS = {
    "max_ball_speed_mps": "球速",
    "target_zone_hit": "命中区",
    "shot_consistency_cv_pct": "连续性/一致性",
    "support_foot_lateral_offset_cm": "支撑脚横向落点",
    "support_foot_ap_offset_cm": "支撑脚前后落点",
    "trunk_lean_deg_at_impact_proxy": "触球时上体后仰",
    "endpoint_error_m": "终点误差",
    "execution_time_s": "完成时间",
    "penalty_events": "失误次数",
    "control_zone_success_rate": "控制区成功率",
    "stabilization_time_s": "稳定时间",
    "corrective_touch_count": "补救触球数",
    "first_touch_displacement_m": "第一脚触球位移",
    "completion_time_s": "完成时间",
    "pass_endpoint_error_m": "传球终点误差",
    "pass_execution_time_s": "传球完成时间",
    "receive_control_zone_success_rate": "接球控制区成功率",
    "receive_stabilization_time_s": "接球稳定时间",
    "receive_corrective_touch_count": "接球补救触球数",
    "sequence_continuity_score": "序列衔接分",
    "next_action_readiness": "下一动作准备度",
    "pass_receive_gap_s": "传接间隔",
    "cone_hit_count": "碰杆/碰桩次数",
    "out_of_lane_count": "出线次数",
    "control_loss_count": "控球失误数",
    "consecutive_touches_dominant_foot": "连续颠球数",
    "consecutive_touches_freestyle": "连续颠球数",
    "drop_count": "掉球次数",
}

_SHOT_HINTS = {
    "support_foot_too_far": "支撑脚再靠近球侧后方一点，落点不要离球太远。",
    "support_foot_too_close": "支撑脚再离球远一点，给摆腿留出更完整的通道。",
    "upper_body_back_lean": "触球前把胸口稳住，不要向后倒。",
    "follow_through_incomplete": "触球后把摆腿继续送出去，不要在碰球瞬间急停。",
    "stable_action": "当前动作结构比较稳定，先保持节奏再提速。",
}


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item:
            continue
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _metric_label(metric_name: str, metric_cfg: Dict[str, Any]) -> str:
    if metric_name in _METRIC_LABELS:
        return _METRIC_LABELS[metric_name]
    if metric_cfg.get("display_name"):
        return str(metric_cfg["display_name"])
    return metric_name.replace("_", " ")


def _format_metric_feedback(metric_result: Dict[str, Any], metric_cfg: Dict[str, Any]) -> Optional[str]:
    raw_value = metric_result.get("raw_value")
    if raw_value is None:
        return f"{_metric_label(metric_result['metric'], metric_cfg)} 暂时没有稳定数值，建议补拍更清晰的视频。"

    label = _metric_label(metric_result["metric"], metric_cfg)
    band = str(metric_result.get("band", "unknown"))
    thresholds = metric_cfg.get("beginner_thresholds") or metric_cfg.get("beginner_reference") or metric_cfg.get("amateur_thresholds") or metric_cfg.get("amateur_reference") or {}
    direction = str(metric_cfg.get("direction", "higher_is_better"))

    if metric_result.get("diagnostic_only"):
        if metric_result.get("soft_bands"):
            return f"{label} 当前为 {float(raw_value):.1f}，处于诊断提示区间，可作为动作细节参考。"
        return f"{label} 当前为 {float(raw_value):.1f}，属于诊断提示项。"

    if metric_result.get("score") is None:
        return f"{label} 还没有形成稳定评分，建议继续补充样本。"

    if direction == "lower_is_better":
        good_key = thresholds.get("good_max")
        excellent_key = thresholds.get("excellent_max")
        if good_key is not None and float(raw_value) > float(good_key):
            return f"{label} 偏大，当前 {float(raw_value):.1f}，建议压到 {float(good_key):.1f} 以内。"
        if excellent_key is not None and float(raw_value) <= float(excellent_key):
            return f"{label} 表现不错，当前 {float(raw_value):.1f}，可以继续保持。"
    else:
        good_key = thresholds.get("good_min")
        excellent_key = thresholds.get("excellent_min")
        if good_key is not None and float(raw_value) < float(good_key):
            return f"{label} 偏低，当前 {float(raw_value):.1f}，建议提升到 {float(good_key):.1f} 以上。"
        if excellent_key is not None and float(raw_value) >= float(excellent_key):
            return f"{label} 已达到较高水平，当前 {float(raw_value):.1f}，可以继续稳定输出。"

    if band == "excellent":
        return f"{label} 表现不错，当前已达到 excellent 区间，可以继续保持。"
    if band == "good":
        return f"{label} 表现良好，当前处于 good 区间，可以继续保持。"
    if band in {"needs_work", "poor"}:
        return f"{label} 仍有提升空间，当前处于 {band} 区间，建议继续纠正。"
    return f"{label} 当前结果暂时不足以稳定判断，建议补充更完整样本。"


def build_feedback_messages(
    *,
    action_name: str,
    rules: Optional[Dict[str, Any]] = None,
    score_result: Dict[str, Any],
    quality_result: Dict[str, Any],
    analysis_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    action_cfg = get_action_rules(action_name, rules)
    primary_cfg = dict(action_cfg.get("primary_metrics") or {})
    secondary_cfg = dict(action_cfg.get("secondary_metrics") or {})
    triggered_rules = list(score_result.get("triggered_rules") or [])
    feedback_messages: List[str] = []
    fail_reasons: List[str] = []
    needs_confirmation = bool(score_result.get("needs_confirmation") or (analysis_context or {}).get("needs_confirmation"))

    if needs_confirmation:
        if quality_result.get("should_reshoot"):
            hint = str(quality_result.get("reshoot_hint") or "请重拍更清晰的视频。")
            feedback_messages.append(hint)
            fail_reasons.extend(quality_result.get("fail_reasons") or [])

        candidate_names = []
        for candidate in score_result.get("action_candidates") or (analysis_context or {}).get("action_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            label = str(candidate.get("display_name") or candidate.get("label") or candidate.get("action") or "").strip()
            if label and label not in candidate_names:
                candidate_names.append(label)
        if candidate_names:
            feedback_messages.append(f"当前动作类型仍待确认，更像 { ' / '.join(candidate_names[:2]) }。")
        else:
            feedback_messages.append("当前动作类型仍待确认。")

        reason_map = {
            "no_pose": "人体姿态证据不足",
            "target_unstable": "主目标跟踪不稳定",
            "ball_unstable": "球轨迹不稳定",
            "goal_not_visible": "球门上下文不清晰",
            "low_confidence": "动作置信度偏低",
            "ambiguous_pass_shot": "传球与射门边界模糊",
            "ambiguous_action": "动作候选仍有歧义",
            "short_clip": "视频时长太短",
            "kick_stage_uncertain": "踢球阶段仍不够明确",
        }
        uncertainty_reasons = list(score_result.get("uncertainty_reasons") or (analysis_context or {}).get("uncertainty_reasons") or [])
        mapped_reasons = [reason_map.get(reason, reason) for reason in uncertainty_reasons if reason]
        if mapped_reasons:
            feedback_messages.append(f"主要不确定原因：{ '、'.join(mapped_reasons[:3]) }。")

        return {
            "feedback_messages": _dedupe(feedback_messages)[:6],
            "fail_reasons": _dedupe(fail_reasons)[:6],
        }

    if quality_result.get("should_reshoot"):
        hint = str(quality_result.get("reshoot_hint") or "请重拍更清晰的视频。")
        feedback_messages.append(hint)
        fail_reasons.extend(quality_result.get("fail_reasons") or [])

    for rule in quality_result.get("triggered_rules") or []:
        reason = str(rule.get("reason", ""))
        if reason:
            feedback_messages.append(reason)

    metric_index = {metric["metric"]: metric for metric in score_result.get("metric_results") or [] if isinstance(metric, dict)}
    for rule in triggered_rules:
        metric_name = rule.get("metric") or rule.get("id")
        metric_result = metric_index.get(metric_name)
        if metric_result is None:
            continue
        metric_cfg = primary_cfg.get(metric_name) or secondary_cfg.get(metric_name) or {}
        message = _format_metric_feedback(metric_result, metric_cfg)
        if message:
            feedback_messages.append(message)
        if rule.get("severity") in {"fail", "warn"}:
            fail_reasons.append(str(rule.get("reason") or message or ""))

    if not feedback_messages:
        if quality_result.get("passed"):
            feedback_messages.append(f"{action_cfg.get('display_name', action_name)} 当前整体可用，继续保持节奏。")
        else:
            feedback_messages.append("视频质量不足，建议重拍后再分析。")

    if action_name == "shot_instep":
        for rule in triggered_rules:
            rule_id = str(rule.get("id") or "")
            if rule_id in _SHOT_HINTS:
                feedback_messages.append(_SHOT_HINTS[rule_id])

    return {
        "feedback_messages": _dedupe(feedback_messages)[:6],
        "fail_reasons": _dedupe(fail_reasons)[:6],
    }
