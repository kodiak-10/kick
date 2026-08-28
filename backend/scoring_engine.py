from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from rules_loader import get_action_rules, load_football_rules, resolve_action_name


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return default
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _normalize_key(name: str) -> str:
    key = name.lower().strip()
    key = re.sub(r"(?:_mps|_kmh|_km_s|_cm|_mm|_m|_s|_pct|_deg|_count)$", "", key)
    key = re.sub(r"^(max_|mean_|avg_|average_|min_|sum_)", "", key)
    key = key.replace("__", "_")
    return key


def _threshold_value(thresholds: Dict[str, Any], *names: str) -> Optional[float]:
    for name in names:
        value = _safe_float(thresholds.get(name))
        if value is not None:
            return value
    return None


def _metric_display_name(metric_name: str, metric_cfg: Dict[str, Any]) -> str:
    if metric_cfg.get("display_name"):
        return str(metric_cfg["display_name"])
    return metric_name.replace("_", " ")


def _candidate_names(metric_name: str) -> List[str]:
    base = _normalize_key(metric_name)
    candidates = {metric_name, base, base.replace("_", "")}
    alias_map = {
        "ball_speed": {"max_ball_speed_mps", "max_ball_speed_proxy_mps", "ball_speed_proxy_mps", "ball_speed_ratio", "speed", "speed_ratio"},
        "ball_speed_proxy": {"max_ball_speed_proxy_mps", "ball_speed_proxy_mps", "ball_speed_proxy"},
        "accuracy": {"target_zone_hit", "endpoint_error_m", "endpoint_error"},
        "consistency": {"shot_consistency_cv_pct", "consistency_cv_pct"},
        "endpoint_error": {"endpoint_error_m"},
        "execution_time": {"execution_time_s"},
        "penalty_events": {"penalty_events"},
        "control_zone_success_rate": {"control_zone_success_rate"},
        "stabilization_time": {"stabilization_time_s"},
        "corrective_touch_count": {"corrective_touch_count"},
        "first_touch_displacement": {"first_touch_displacement_m"},
        "completion_time": {"completion_time_s"},
        "cone_hit": {"cone_hit_count"},
        "out_of_lane": {"out_of_lane_count"},
        "control_loss": {"control_loss_count"},
        "drop_count": {"drop_count"},
        "consecutive_touches": {"consecutive_touches_dominant_foot", "consecutive_touches_freestyle"},
        "lateral_offset": {"support_foot_lateral_offset_cm", "lateral_offset_m"},
        "plant_foot_orientation": {"plant_foot_orientation_deg"},
        "body_open_angle": {"body_open_angle_deg", "body_open_angle_deg_before_pass"},
        "orientation": {"body_orientation_to_ball_deg"},
        "recenter": {"recenter_time_s"},
    }
    for alias, names in alias_map.items():
        if alias in base or base in alias:
            candidates.update(names)
    return [candidate for candidate in candidates if candidate]


def _lookup_metric_value(metric_name: str, metrics: Dict[str, Any], analysis_context: Optional[Dict[str, Any]] = None) -> Tuple[Any, Optional[str]]:
    search_spaces: List[Dict[str, Any]] = []
    if metrics:
        search_spaces.append(metrics)
    if analysis_context:
        rule_metrics = analysis_context.get("rule_metrics")
        if isinstance(rule_metrics, dict):
            search_spaces.append(rule_metrics)
        legacy_metrics = analysis_context.get("legacy_metrics")
        if isinstance(legacy_metrics, dict):
            search_spaces.append(legacy_metrics)
    candidates = _candidate_names(metric_name)
    normalized_candidates = {_normalize_key(name) for name in candidates}

    for space in search_spaces:
        for key, value in space.items():
            normalized_key = _normalize_key(str(key))
            if key in candidates or normalized_key in normalized_candidates or any(c in normalized_key or normalized_key in c for c in normalized_candidates):
                return value, str(key)
    return None, None


def _higher_better_score(value: float, thresholds: Dict[str, Any]) -> Tuple[float, str]:
    excellent = _threshold_value(thresholds, "excellent_min", "excellent")
    good = _threshold_value(thresholds, "good_min", "good")
    needs_work = _threshold_value(thresholds, "needs_work_below", "needs_work")

    if excellent is not None and good is not None and good > excellent:
        good = excellent
    if good is not None and needs_work is not None and needs_work > good:
        needs_work = good

    if excellent is not None and value >= excellent:
        return 100.0, "excellent"

    if good is not None and value >= good:
        if excellent is not None and excellent > good:
            span = max(1e-6, excellent - good)
            return 80.0 + 20.0 * _clamp((value - good) / span), "good"
        return 80.0, "good"

    if needs_work is not None and value >= needs_work:
        if good is not None and good > needs_work:
            span = max(1e-6, good - needs_work)
            return 45.0 + 35.0 * _clamp((value - needs_work) / span), "needs_work"
        return 55.0, "needs_work"

    if needs_work is not None:
        span = max(1e-6, needs_work)
        return 30.0 * _clamp(value / span), "poor"

    if good is not None:
        return 78.0 if value >= good else 30.0, "good" if value >= good else "poor"

    return 0.0, "missing"


def _lower_better_score(value: float, thresholds: Dict[str, Any]) -> Tuple[float, str]:
    excellent = _threshold_value(thresholds, "excellent_max", "excellent")
    good = _threshold_value(thresholds, "good_max", "good")
    poor = _threshold_value(thresholds, "poor_over", "poor")

    if excellent is not None and good is not None and excellent > good:
        excellent, good = good, excellent
    if good is not None and poor is not None and good > poor:
        good = poor

    if excellent is not None and value <= excellent:
        return 100.0, "excellent"

    if good is not None and value <= good:
        if excellent is not None and good > excellent:
            span = max(1e-6, good - excellent)
            return 80.0 + 20.0 * _clamp((good - value) / span), "good"
        return 80.0, "good"

    if poor is not None and value <= poor:
        if good is not None and poor > good:
            span = max(1e-6, poor - good)
            return 45.0 + 35.0 * _clamp((poor - value) / span), "needs_work"
        return 55.0, "needs_work"

    if poor is not None:
        span = max(1e-6, poor)
        return max(0.0, 30.0 * _clamp(poor / max(value, 1e-6))), "poor"

    if good is not None:
        return 78.0 if value <= good else 30.0, "good" if value <= good else "poor"

    return 0.0, "missing"


def _reference_score(value: float, thresholds: Dict[str, Any], direction: str = "higher_is_better") -> Tuple[float, str]:
    if direction == "lower_is_better":
        return _lower_better_score(value, thresholds)
    return _higher_better_score(value, thresholds)


def _zone_score(value: Any, zones: Dict[str, Any]) -> Tuple[float, str]:
    if value is None:
        return 0.0, "missing"
    if isinstance(value, str):
        reverse = {str(zone_name).lower(): score for zone_name, score in zones.items()}
        matched = reverse.get(value.lower())
        if matched is None:
            return 0.0, "missing"
        value = matched
    value = _safe_float(value, 0.0) or 0.0
    max_zone = max(float(v) for v in zones.values()) if zones else 3.0
    if max_zone <= 0:
        return 0.0, "missing"
    score = 100.0 * _clamp(value / max_zone)
    if value >= max_zone:
        band = "excellent"
    elif value >= max_zone * 0.66:
        band = "good"
    elif value >= max_zone * 0.33:
        band = "needs_work"
    else:
        band = "poor"
    return score, band


def _diagnostic_band(value: float, bands: Iterable[float]) -> str:
    ordered = list(float(v) for v in bands if v is not None)
    if not ordered:
        return "unknown"
    ordered.sort()
    if value <= ordered[0]:
        return "good"
    if len(ordered) >= 2 and value <= ordered[1]:
        return "watch"
    if len(ordered) >= 3 and value <= ordered[2]:
        return "warn"
    return "poor"


def _metric_role(metric_name: str, metric_cfg: Dict[str, Any]) -> str:
    if str(metric_cfg.get("use_as", "")).lower() == "diagnostic_only":
        return "diagnostic_only"
    lowered = metric_name.lower()
    if any(token in lowered for token in ("stabilization", "execution_time", "consistency", "orientation", "recenter", "plant_foot", "trunk_lean", "support_foot")):
        return "technique"
    return "outcome"


def _metric_label(metric_name: str, metric_cfg: Dict[str, Any]) -> str:
    return _metric_display_name(metric_name, metric_cfg)


def _score_metric(metric_name: str, metric_cfg: Dict[str, Any], value: Any, *, audience: str) -> Dict[str, Any]:
    role = _metric_role(metric_name, metric_cfg)
    source_class = str(metric_cfg.get("source_class", "unknown"))
    use_as = str(metric_cfg.get("use_as", ""))
    payload: Dict[str, Any] = {}
    confidence = None
    resolved = None
    low_confidence = False
    if isinstance(value, dict):
        payload = dict(value)
        raw_value = _safe_float(payload.get("value", payload.get("raw_value")), None)
        confidence = _safe_float(payload.get("confidence"), None)
        resolved = payload.get("resolved")
        if resolved is None:
            resolved = raw_value is not None
        low_confidence = bool(payload.get("low_confidence")) or (confidence is not None and confidence < 0.6)
        if raw_value is None or not resolved or low_confidence:
            return {
                "metric": metric_name,
                "label": _metric_label(metric_name, metric_cfg),
                "raw_value": raw_value,
                "score": None,
                "band": "low_confidence" if low_confidence else "unresolved",
                "role": role,
                "source_class": source_class,
                "use_as": use_as,
                "direction": str(metric_cfg.get("direction", "higher_is_better")),
                "diagnostic_only": role == "diagnostic_only",
                "confidence": confidence,
                "resolved": bool(resolved),
                "low_confidence": low_confidence,
                "start_time": payload.get("start_time"),
                "end_time": payload.get("end_time"),
                "start_event": payload.get("start_event"),
                "end_event": payload.get("end_event"),
                "event_source": payload.get("event_source"),
                "fallback_to_video_end": payload.get("fallback_to_video_end", False),
                "thresholds": None,
                **{k: v for k, v in payload.items() if k not in {"value", "raw_value", "confidence", "resolved", "low_confidence"}},
            }
        value = raw_value
    if value is None:
        return {
            "metric": metric_name,
            "label": _metric_label(metric_name, metric_cfg),
            "raw_value": None,
            "score": None,
            "band": "missing",
            "role": role,
            "source_class": source_class,
            "use_as": use_as,
            "diagnostic_only": role == "diagnostic_only",
        }

    thresholds = metric_cfg.get(f"{audience}_thresholds") or metric_cfg.get(f"{audience}_reference") or metric_cfg.get("beginner_thresholds") or metric_cfg.get("beginner_reference") or metric_cfg.get("amateur_thresholds") or metric_cfg.get("amateur_reference") or {}
    direction = str(metric_cfg.get("direction", "higher_is_better"))

    score = None
    band = "missing"
    if "zones" in metric_cfg and isinstance(metric_cfg["zones"], dict):
        score, band = _zone_score(value, metric_cfg["zones"])
    elif thresholds:
        raw = _safe_float(value, None)
        if raw is not None:
            score, band = _reference_score(raw, thresholds, direction=direction)
    elif "soft_bands" in metric_cfg:
        # Diagnostic-only metrics keep the engineering seed bands for feedback,
        # but they are not treated as hard gates in the single-camera setup.
        raw = _safe_float(value, None)
        if raw is not None:
            band = _diagnostic_band(raw, metric_cfg.get("soft_bands", []))

    return {
        "metric": metric_name,
        "label": _metric_label(metric_name, metric_cfg),
        "raw_value": _safe_float(value, None),
        "score": None if score is None else round(float(score), 2),
        "band": band,
        "role": role,
        "source_class": source_class,
        "use_as": use_as,
        "direction": direction,
        "diagnostic_only": role == "diagnostic_only",
        "confidence": confidence,
        "resolved": bool(resolved) if resolved is not None else True,
        "low_confidence": low_confidence,
        "thresholds": thresholds if thresholds else None,
        "zones": metric_cfg.get("zones"),
        "soft_bands": metric_cfg.get("soft_bands"),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "start_event": payload.get("start_event"),
        "end_event": payload.get("end_event"),
        "event_source": payload.get("event_source"),
        "fallback_to_video_end": payload.get("fallback_to_video_end", False),
        **{k: v for k, v in payload.items() if k not in {"value", "raw_value", "confidence", "resolved", "low_confidence"}},
    }


def _weight_value(weight_map: Dict[str, float], metric_name: str, metric_cfg: Dict[str, Any]) -> float:
    normalized_metric = _normalize_key(metric_name)
    for weight_key, weight_value in weight_map.items():
        normalized_weight = _normalize_key(str(weight_key))
        if (
            normalized_weight == normalized_metric
            or normalized_weight in normalized_metric
            or normalized_metric in normalized_weight
            or normalized_weight.replace("_", "") in normalized_metric.replace("_", "")
        ):
            return float(weight_value)

    aliases = {
        "ball_speed": "max_ball_speed_mps",
        "ball_speed_proxy": "max_ball_speed_proxy_mps",
        "accuracy": "target_zone_hit",
        "consistency": "shot_consistency_cv_pct",
        "endpoint_error": "endpoint_error_m",
        "execution_time": "execution_time_s",
        "penalty_events": "penalty_events",
        "control_zone_success_rate": "control_zone_success_rate",
        "stabilization_time": "stabilization_time_s",
        "corrective_touch_count": "corrective_touch_count",
        "first_touch_displacement": "first_touch_displacement_m",
        "completion_time": "completion_time_s",
        "cone_hit": "cone_hit_count",
        "out_of_lane": "out_of_lane_count",
        "control_loss": "control_loss_count",
        "drop_count": "drop_count",
    }
    for weight_key, weight_value in weight_map.items():
        alias_target = aliases.get(str(weight_key))
        if alias_target and alias_target == metric_name:
            return float(weight_value)

    default_weight = metric_cfg.get("weight")
    if default_weight is not None:
        return float(default_weight)
    return 0.0


def _weighted_average(items: List[Tuple[float, float]]) -> Optional[float]:
    total_weight = sum(weight for _, weight in items if weight > 0.0)
    if total_weight <= 0.0:
        return None
    return sum(score * weight for score, weight in items if weight > 0.0) / total_weight


def _default_trigger_rule(metric_result: Dict[str, Any], *, good_threshold_band: str = "good") -> Optional[Dict[str, Any]]:
    score = metric_result.get("score")
    band = str(metric_result.get("band", "missing"))
    if score is None:
        if metric_result.get("low_confidence") or metric_result.get("resolved") is False or band in {"low_confidence", "unresolved"}:
            return {
                "id": metric_result["metric"],
                "metric": metric_result["metric"],
                "label": metric_result["label"],
                "role": metric_result["role"],
                "severity": "info",
                "reason": f"{metric_result['label']} 当前没有稳定数值，已按保守结果处理。",
                "raw_value": metric_result.get("raw_value"),
                "score": None,
                "band": band,
                "quality_impact": "diagnostic_only",
            }
        return {
            "id": metric_result["metric"],
            "metric": metric_result["metric"],
            "label": metric_result["label"],
            "role": metric_result["role"],
            "severity": "fail",
            "reason": f"{metric_result['label']} 暂时没有可用数值，无法稳定评分。",
            "raw_value": None,
            "score": None,
            "band": band,
            "quality_impact": "primary",
        }
    if band in {"excellent", good_threshold_band}:
        return None
    severity = "warn" if band == "needs_work" else "fail"
    return {
        "id": metric_result["metric"],
        "metric": metric_result["metric"],
        "label": metric_result["label"],
        "role": metric_result["role"],
        "severity": severity,
        "reason": f"{metric_result['label']} 表现偏弱，当前处于 {band} 区间。",
        "raw_value": metric_result.get("raw_value"),
        "score": score,
        "band": band,
        "quality_impact": "primary" if metric_result["role"] != "diagnostic_only" else "diagnostic_only",
    }


def _diagnostic_trigger(metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if metric_result.get("role") != "diagnostic_only":
        return None
    band = str(metric_result.get("band", "unknown"))
    if band in {"good", "unknown"}:
        return None
    return {
        "id": metric_result["metric"],
        "metric": metric_result["metric"],
        "label": metric_result["label"],
        "role": metric_result["role"],
        "severity": "info",
        "reason": f"{metric_result['label']} 处于 {band} 区间，可作为诊断提示。",
        "raw_value": metric_result.get("raw_value"),
        "score": metric_result.get("score"),
        "band": band,
        "quality_impact": "diagnostic_only",
    }


def _best_and_worst_metric(metric_results: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    scored = [item for item in metric_results if item.get("score") is not None and item.get("role") != "diagnostic_only"]
    if not scored:
        return None, None
    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    best = scored[0]
    worst = scored[-1]
    return (
        {
            "metric": best["metric"],
            "label": best["label"],
            "score": round(float(best["score"]), 2),
            "raw_value": best.get("raw_value"),
            "role": best.get("role"),
            "band": best.get("band"),
            "source": "metric_proxy",
        },
        {
            "metric": worst["metric"],
            "label": worst["label"],
            "score": round(float(worst["score"]), 2),
            "raw_value": worst.get("raw_value"),
            "role": worst.get("role"),
            "band": worst.get("band"),
            "source": "metric_proxy",
        },
    )


def score_action(
    action_name: str,
    metrics: Dict[str, Any],
    rules: Optional[Dict[str, Any]] = None,
    *,
    audience: str = "beginner",
    quality_result: Optional[Dict[str, Any]] = None,
    analysis_context: Optional[Dict[str, Any]] = None,
    trial_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    resolved_action_name = resolve_action_name(action_name, rules)
    action_cfg = get_action_rules(resolved_action_name, rules)
    primary_cfg = dict(action_cfg.get("primary_metrics") or {})
    secondary_cfg = dict(action_cfg.get("secondary_metrics") or {})
    weight_map = dict((action_cfg.get("score_weights") or {}).get(audience) or {})
    quality_status = str((quality_result or {}).get("quality_status", "pass"))
    allow_micro_technique_score = bool((quality_result or {}).get("allow_micro_technique_score", True))
    rule_source = dict((analysis_context or {}).get("rule_metrics") or metrics or {})

    metric_results: List[Dict[str, Any]] = []
    triggered_rules: List[Dict[str, Any]] = []
    total_primary_base_weight = 0.0
    low_confidence_base_weight = 0.0
    low_confidence_metric_count = 0

    for metric_name, metric_cfg in primary_cfg.items():
        # `source_class == "product_default"` entries here are engineering seed values.
        value, matched_key = _lookup_metric_value(metric_name, rule_source, analysis_context)
        metric_result = _score_metric(metric_name, metric_cfg, value, audience=audience)
        metric_result["matched_key"] = matched_key
        base_weight = _weight_value(weight_map, metric_name, metric_cfg)
        metric_weight = base_weight
        confidence = metric_result.get("confidence")
        if confidence is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
                metric_weight *= confidence
            except Exception:
                pass
        metric_result["base_weight"] = base_weight
        metric_result["confidence_factor"] = confidence if confidence is not None else 1.0
        metric_result["weight"] = metric_weight
        metric_results.append(metric_result)
        total_primary_base_weight += float(base_weight or 0.0)
        if metric_result.get("score") is None or metric_result.get("low_confidence") or metric_result.get("resolved") is False:
            low_confidence_metric_count += 1
            low_confidence_base_weight += float(base_weight or 0.0)
        trigger = _default_trigger_rule(metric_result)
        if trigger is not None:
            triggered_rules.append(trigger)

    for metric_name, metric_cfg in secondary_cfg.items():
        # `source_class == "product_default"` diagnostic bands are engineering seed values,
        # used to guide coaching feedback for the single-camera setup.
        value, matched_key = _lookup_metric_value(metric_name, rule_source, analysis_context)
        metric_result = _score_metric(metric_name, metric_cfg, value, audience=audience)
        metric_result["matched_key"] = matched_key
        metric_result["weight"] = 0.0
        metric_results.append(metric_result)
        trigger = _diagnostic_trigger(metric_result)
        if trigger is not None:
            triggered_rules.append(trigger)

    outcome_items: List[Tuple[float, float]] = []
    technique_items: List[Tuple[float, float]] = []
    all_primary_items: List[Tuple[float, float]] = []

    for metric_result in metric_results:
        if metric_result["role"] == "diagnostic_only":
            continue
        if metric_result.get("score") is None:
            continue
        item = (float(metric_result["score"]), float(metric_result.get("weight") or 0.0))
        all_primary_items.append(item)
        if metric_result["role"] == "technique":
            technique_items.append(item)
        else:
            outcome_items.append(item)

    outcome_score = _weighted_average(outcome_items)
    technique_score = _weighted_average(technique_items) if allow_micro_technique_score else None
    primary_score = _weighted_average(all_primary_items)

    if quality_status != "pass":
        overall_score = outcome_score if outcome_score is not None else primary_score
    else:
        overall_score = primary_score if primary_score is not None else outcome_score

    provisional_score = None if overall_score is None else float(overall_score)
    confidence_adjusted_score = provisional_score
    confidence_penalty_ratio = 0.0
    low_confidence_weight_ratio = 0.0
    if provisional_score is not None and total_primary_base_weight > 0.0 and low_confidence_base_weight > 0.0:
        low_confidence_weight_ratio = low_confidence_base_weight / total_primary_base_weight
        confidence_penalty_ratio = min(0.20, 0.25 * low_confidence_weight_ratio)
        confidence_adjusted_score = provisional_score * (1.0 - confidence_penalty_ratio)
        if low_confidence_metric_count > 0:
            confidence_adjusted_score = min(confidence_adjusted_score, 95.0)
        confidence_adjusted_score = _clamp(confidence_adjusted_score, 0.0, 100.0)
        overall_score = confidence_adjusted_score
    elif provisional_score is not None:
        overall_score = provisional_score

    sub_scores: Dict[str, Any] = {}
    for metric_result in metric_results:
        visible = metric_result["role"] != "diagnostic_only"
        if quality_status != "pass" and metric_result["role"] == "technique":
            visible = False
        if quality_status != "pass" and metric_result["role"] == "diagnostic_only":
            visible = False
        if not visible:
            continue
        sub_scores[metric_result["metric"]] = {
            "label": metric_result["label"],
            "raw_value": metric_result.get("raw_value"),
            "score": metric_result.get("score"),
            "band": metric_result.get("band"),
            "role": metric_result.get("role"),
            "weight": round(float(metric_result.get("weight") or 0.0), 3),
            "source_class": metric_result.get("source_class"),
            "use_as": metric_result.get("use_as"),
            "diagnostic_only": metric_result.get("diagnostic_only", False),
            "matched_key": metric_result.get("matched_key"),
        }

    if trial_records:
        candidate_trials = [item for item in trial_records if isinstance(item, dict) and item.get("score") is not None]
        candidate_trials.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        best_trial = dict(candidate_trials[0]) if candidate_trials else None
        worst_trial = dict(candidate_trials[-1]) if candidate_trials else None
    else:
        best_trial, worst_trial = _best_and_worst_metric(metric_results)

    if best_trial is None:
        best_trial = {
            "metric": "overall",
            "label": action_cfg.get("display_name", action_name),
            "score": round(float(overall_score or 0.0), 2),
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        }
    if worst_trial is None:
        worst_trial = {
            "metric": "overall",
            "label": action_cfg.get("display_name", action_name),
            "score": round(float(overall_score or 0.0), 2),
            "raw_value": None,
            "role": "summary",
            "band": "unknown",
            "source": "overall_proxy",
        }

    return {
        "action_name": resolved_action_name,
        "input_action_name": action_name,
        "resolved_action_name": resolved_action_name,
        "action_display_name": action_cfg.get("display_name", action_name),
        "audience": audience,
        "quality_status": quality_status,
        "provisional_score": None if provisional_score is None else round(float(provisional_score), 1),
        "confidence_adjusted_score": None if confidence_adjusted_score is None else round(float(confidence_adjusted_score), 1),
        "confidence_penalty_ratio": round(float(confidence_penalty_ratio), 3),
        "low_confidence_metric_count": int(low_confidence_metric_count),
        "low_confidence_weight_ratio": round(float(low_confidence_weight_ratio), 3),
        "overall_score": round(float(overall_score or 0.0), 1),
        "outcome_score": None if outcome_score is None else round(float(outcome_score), 1),
        "technique_score": None if technique_score is None else round(float(technique_score), 1),
        "primary_score": None if primary_score is None else round(float(primary_score), 1),
        "sub_scores": sub_scores,
        "triggered_rules": triggered_rules,
        "best_trial": best_trial,
        "worst_trial": worst_trial,
        "metric_results": metric_results,
    }
