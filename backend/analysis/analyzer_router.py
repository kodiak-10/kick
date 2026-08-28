from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _normalize_action(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if any(token in text for token in ("full_match_player", "full_match", "match_player", "整场比赛", "比赛分析", "全场")):
        return "full_match"
    if any(token in text for token in ("pass_receive_sequence", "sequence", "传接球")):
        return "pass_receive_sequence"
    if any(token in text for token in ("receive_control", "first_touch", "stop_ball", "接球", "停球")):
        return "receive_control"
    if any(token in text for token in ("shot_instep", "shot_like", "shoot_like", "shoot", "shot", "射门", "clearance")):
        return "shot"
    if any(token in text for token in ("short_pass", "pass_like", "long_ball", "pass", "传球")):
        return "pass"
    if any(token in text for token in ("review_required", "uncertain", "unknown", "待确认")):
        return "review_required"
    return text


def _action_family(action: str) -> str:
    normalized = _normalize_action(action)
    if normalized in {"full_match", "full_match_player", "match_player"}:
        return "full_match"
    if normalized in {"pass", "short_pass", "pass_like", "long_ball"}:
        return "pass"
    if normalized in {"shot", "shot_instep", "shoot_like", "clearance"}:
        return "shot"
    if normalized in {"receive_control", "receive", "first_touch"}:
        return "receive"
    if normalized in {"pass_receive_sequence"}:
        return "pass_receive_sequence"
    if normalized in {"review_required", "uncertain", ""}:
        return "review_required"
    return "unknown"


@dataclass(frozen=True)
class AnalyzerRoute:
    selected_action: str
    selected_action_family: str
    analysis_routed_by: str
    routed_analyzer: str
    routed_analyzer_family: str
    analysis_template: str
    system_action_suggestion: str
    route_mismatch: bool
    route_mismatch_message: str
    integrity_state: str
    analysis_status: str
    failure_reason: str
    failure_message: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_action": self.selected_action,
            "selected_action_family": self.selected_action_family,
            "analysis_routed_by": self.analysis_routed_by,
            "routed_analyzer": self.routed_analyzer,
            "routed_analyzer_family": self.routed_analyzer_family,
            "analysis_template": self.analysis_template,
            "system_action_suggestion": self.system_action_suggestion,
            "route_mismatch": self.route_mismatch,
            "route_mismatch_message": self.route_mismatch_message,
            "integrity_state": self.integrity_state,
            "analysis_status": self.analysis_status,
            "failure_reason": self.failure_reason,
            "failure_message": self.failure_message,
            "warnings": list(self.warnings),
        }


_ROUTE_TABLE: Dict[str, Dict[str, str]] = {
    "pass": {
        "analysis_template": "short_pass",
        "routed_analyzer": "short_pass_analyzer_v1",
    },
    "shot": {
        "analysis_template": "shot_instep",
        "routed_analyzer": "shot_instep_analyzer_v1",
    },
    "receive_control": {
        "analysis_template": "receive_control",
        "routed_analyzer": "receive_control_analyzer_v1",
    },
    "pass_receive_sequence": {
        "analysis_template": "pass_receive_sequence",
        "routed_analyzer": "pass_receive_sequence_engine_v1",
    },
    "full_match": {
        "analysis_template": "full_match_player",
        "routed_analyzer": "full_match_player_analyzer_v1",
    },
}


def resolve_analysis_route(
    selected_action: Any,
    *,
    analysis_template: Any = None,
    system_action_suggestion: Any = None,
    analysis_routed_by: str | None = None,
) -> AnalyzerRoute:
    normalized_selected = _normalize_action(selected_action)
    selected_family = _action_family(normalized_selected)
    normalized_template = _normalize_action(analysis_template)
    normalized_suggestion = _normalize_action(system_action_suggestion)

    routed_by = str(analysis_routed_by or ("user_selected" if normalized_selected else "auto_detected")).strip() or "auto_detected"

    if selected_family == "review_required" or not normalized_selected:
        return AnalyzerRoute(
            selected_action=normalized_selected,
            selected_action_family=selected_family,
            analysis_routed_by=routed_by,
            routed_analyzer="",
            routed_analyzer_family="review_required",
            analysis_template=normalized_template or "",
            system_action_suggestion=normalized_suggestion or "",
            route_mismatch=False,
            route_mismatch_message="",
            integrity_state="normal",
            analysis_status="failed",
            failure_reason="unsupported_action",
            failure_message="当前动作暂不支持，请切换到已支持的分析模板。",
            warnings=["unsupported_action"],
        )

    route_key = normalized_selected if normalized_selected in _ROUTE_TABLE else selected_family
    route = _ROUTE_TABLE.get(route_key)
    if route is None:
        return AnalyzerRoute(
            selected_action=normalized_selected,
            selected_action_family=selected_family,
            analysis_routed_by=routed_by,
            routed_analyzer="",
            routed_analyzer_family="unknown",
            analysis_template=normalized_template or "",
            system_action_suggestion=normalized_suggestion or "",
            route_mismatch=False,
            route_mismatch_message="",
            integrity_state="normal",
            analysis_status="failed",
            failure_reason="unsupported_action",
            failure_message="当前动作暂不支持，请切换到已支持的分析模板。",
            warnings=["unsupported_action"],
        )

    routed_analyzer = route["routed_analyzer"]
    routed_family = _action_family(routed_analyzer)
    analysis_template_value = route["analysis_template"]

    suggested_family = _action_family(normalized_suggestion)
    route_mismatch = (
        selected_family not in {"unknown", "review_required"}
        and suggested_family not in {"unknown", "review_required", ""}
        and suggested_family != selected_family
    )
    route_mismatch_message = ""
    warnings: List[str] = []
    if route_mismatch:
        warnings.append("route_mismatch")
        route_mismatch_message = (
            f"你当前选择的是“{normalized_selected}”，但系统自动识别更像“{normalized_suggestion}”，"
            f"已按当前选择继续分析。"
        )

    integrity_state = "route_mismatch" if route_mismatch else "normal"
    if selected_family != routed_family and routed_family not in {"unknown", "review_required"}:
        integrity_state = "anomaly"
        route_mismatch = True
        route_mismatch_message = (
            f"你当前选择的是“{normalized_selected}”，但后端路由到了“{routed_analyzer}”。"
        )
        if "route_mismatch" not in warnings:
            warnings.append("route_mismatch")
        warnings.append("route_integrity_anomaly")

    return AnalyzerRoute(
        selected_action=normalized_selected,
        selected_action_family=selected_family,
        analysis_routed_by=routed_by,
        routed_analyzer=routed_analyzer,
        routed_analyzer_family=routed_family,
        analysis_template=analysis_template_value,
        system_action_suggestion=normalized_suggestion or selected_family,
        route_mismatch=route_mismatch,
        route_mismatch_message=route_mismatch_message,
        integrity_state=integrity_state,
        analysis_status="success",
        failure_reason="",
        failure_message="",
        warnings=warnings,
    )
