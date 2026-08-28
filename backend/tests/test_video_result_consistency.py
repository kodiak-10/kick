from pathlib import Path

from coach import analyze_video
import analysis.shot_analysis as shot_analysis


def _patch_video_pipeline(monkeypatch, *, route: dict, score_overall: float, score_level_override=None):
    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0, "goal_visible": False}],
            "frame_count": 60,
            "fps": 30.0,
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_aggregate_metrics",
        lambda samples: (
            {
                "body_span_px": 180.0,
                "support_ball_ratio": 0.24,
                "swing_ball_ratio": 0.09,
                "ball_speed_ratio": 0.10,
                "stability": 0.80,
                "sequence_confidence": 0.72,
                "visibility": 0.90,
                "ball_contact": 0.86,
                "ball_confidence": 0.86,
                "move_ratio": 0.20,
                "trunk_lean_deg": 7.0,
                "balance": 0.06,
                "symmetry": 2.0,
                "valgus_ratio": 1.02,
            },
            {"preparation": 82.0, "support": 84.0, "contact": 86.0, "follow_through": 88.0},
            {"support": 0.25, "contact": 0.45, "follow_through": 0.60},
            {"analysis_confidence": 0.86},
            {"contact": 0.40, "follow_through": 0.62},
            [],
        ),
    )
    monkeypatch.setattr(shot_analysis, "_load_video_calibration", lambda calibration_path=None: None)
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": route.get("raw_detected_action", "pass_like"),
            "action_label": route.get("action_label", "pass"),
            "action_display_name": route.get("action_display_name", "传球"),
            "action_confidence": route.get("action_confidence", 0.91),
            "detection_source": "temporal",
            "needs_confirmation": route.get("needs_confirmation", False),
            "confidence_gap": route.get("confidence_gap", 0.32),
            "uncertainty_reasons": route.get("uncertainty_reasons", []),
            "action_candidates": route.get("action_candidates", []),
            "stage1_action_label": route.get("stage1_action_label", "kick"),
            "stage1_confidence": route.get("stage1_confidence", 0.78),
            "raw_action_candidates": route.get("raw_action_candidates", []),
            "candidate_scores": route.get("candidate_scores", {}),
            "sequence_context": route.get("sequence_context", {}),
            "mapped_rule_key": route.get("mapped_rule_key", "short_pass"),
            "recommended_template": route.get("recommended_template", "short_pass"),
            "fallback_used": route.get("fallback_used", False),
            "whether_fallback_template_used": route.get("whether_fallback_template_used", False),
            "unsupported_action_for_current_analyzer": route.get("unsupported_action_for_current_analyzer", False),
            "analyzer_used": route.get("analyzer_used", "short_pass_analyzer_v1"),
        },
    )
    monkeypatch.setattr(shot_analysis, "video_analysis_router_v1", lambda *args, **kwargs: route)
    monkeypatch.setattr(
        shot_analysis,
        "evaluate_global_quality_gate",
        lambda **kwargs: {
            "quality_status": "pass",
            "passed": True,
            "allow_micro_technique_score": True,
            "hide_micro_technique_score": False,
            "should_reshoot": False,
            "reshoot_hint": "",
            "triggered_rules": [],
            "fail_reasons": [],
            "thresholds": {},
            "observed": {},
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "score_action",
        lambda action_name, metrics, rules, **kwargs: {
            "action_name": action_name,
            "input_action_name": action_name,
            "resolved_action_name": action_name,
            "action_display_name": route.get("action_display_name", "传球"),
            "quality_status": "pass",
            "overall_score": score_overall,
            "confidence_adjusted_score": score_overall,
            "provisional_score": score_overall,
            "technique_score": score_overall,
            "outcome_score": score_overall,
            "primary_score": score_overall,
            "confidence_penalty_ratio": 0.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": score_overall, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": score_overall, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "metric_results": [],
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "build_feedback_messages",
        lambda **kwargs: {"feedback_messages": [], "fail_reasons": []},
    )
    monkeypatch.setattr(
        shot_analysis,
        "locate_error_timestamps",
        lambda **kwargs: {"error_timestamps": []},
    )
    if score_level_override is not None:
        monkeypatch.setattr(shot_analysis, "_score_level_from_overall", score_level_override)


def _video_path() -> Path:
    return Path(__file__).parent / "samples" / "sample_short.mp4"


def test_video_analysis_normalizes_level_from_total_score(monkeypatch, tmp_path):
    route = {
        "raw_detected_action": "pass_like",
        "action_label": "pass",
        "action_display_name": "传球",
        "action_confidence": 0.92,
        "confidence": 0.92,
        "confidence_gap": 0.34,
        "needs_confirmation": False,
        "uncertainty_reasons": [],
        "stage1_action_label": "kick",
        "stage1_confidence": 0.80,
        "detected_action": "pass",
        "final_detected_action": "pass",
        "mapped_rule_key": "short_pass",
        "final_mapped_rule_key": "short_pass",
        "recommended_template": "short_pass",
        "analyzer_used": "short_pass_analyzer_v1",
        "fallback_used": False,
        "whether_fallback_template_used": False,
        "unsupported_action_for_current_analyzer": False,
        "raw_action_candidates": [{"action": "pass", "score": 0.92, "sources": ["stage2.pass"]}],
        "candidate_scores": {"pass": 0.92, "shot": 0.12},
        "sequence_context": {},
        "action_candidates": [
            {"label": "pass", "action": "pass", "display_name": "传球", "score": 0.92, "sources": ["stage2.pass"], "template": "short_pass"}
        ],
    }
    _patch_video_pipeline(
        monkeypatch,
        route=route,
        score_overall=38.0,
        score_level_override=lambda overall_score: {"level_code": "excellent", "level_label": "优秀"},
    )

    result = analyze_video(_video_path(), output_path=tmp_path / "score_mismatch.json")

    assert result["status"] in {"ok", "provisional"}
    assert result["fallback_used"] is False
    assert result["error_code"] == ""
    assert result["anomaly_reason"] == ""
    assert result["inconsistent_fields"] == []
    assert result["action_name"] == "pass"
    assert result["detected_action"] == "pass"
    assert result["recommended_template"] == "short_pass"
    assert result["overall_score"] == 38.0
    assert result["score"]["overall"] == 38.0
    assert result["score"]["level_code"] == "needs_strengthen"
    assert result["score"]["level_label"] == "需加强"
    assert "当前动作" not in result["summary"]


def test_video_analysis_normalizes_action_fields(monkeypatch, tmp_path):
    route = {
        "raw_detected_action": "pass_like",
        "action_label": "pass",
        "action_display_name": "传球",
        "action_confidence": 0.93,
        "confidence": 0.93,
        "confidence_gap": 0.42,
        "needs_confirmation": False,
        "uncertainty_reasons": [],
        "stage1_action_label": "kick",
        "stage1_confidence": 0.82,
        "detected_action": "pass",
        "final_detected_action": "pass",
        "mapped_rule_key": "short_pass",
        "final_mapped_rule_key": "short_pass",
        "recommended_template": "shot_instep",
        "analyzer_used": "short_pass_analyzer_v1",
        "fallback_used": False,
        "whether_fallback_template_used": False,
        "unsupported_action_for_current_analyzer": False,
        "raw_action_candidates": [{"action": "pass", "score": 0.93, "sources": ["stage2.pass"]}],
        "candidate_scores": {"pass": 0.93, "shot": 0.11},
        "sequence_context": {},
        "action_candidates": [
            {"label": "pass", "action": "pass", "display_name": "传球", "score": 0.93, "sources": ["stage2.pass"], "template": "short_pass"}
        ],
    }
    _patch_video_pipeline(monkeypatch, route=route, score_overall=88.0)

    result = analyze_video(_video_path(), output_path=tmp_path / "action_conflict.json")

    assert result["status"] in {"ok", "provisional"}
    assert result["fallback_used"] is False
    assert result["error_code"] == ""
    assert result["anomaly_reason"] == ""
    assert result["inconsistent_fields"] == []
    assert result["action_name"] == "pass"
    assert result["detected_action"] == "pass"
    assert result["recommended_template"] == "short_pass"
    assert result["action_display_name"] == "传球"
    assert result["overall_score"] == 88.0
    assert result["score"]["level_label"] == "良好"


def test_video_analysis_returns_anomaly_when_result_requires_confirmation(monkeypatch, tmp_path):
    route = {
        "raw_detected_action": "pass_like",
        "action_label": "uncertain",
        "action_display_name": "动作待确认",
        "action_confidence": 0.56,
        "confidence": 0.56,
        "confidence_gap": 0.04,
        "needs_confirmation": True,
        "uncertainty_reasons": ["low_confidence", "ambiguous_pass_shot"],
        "stage1_action_label": "kick",
        "stage1_confidence": 0.64,
        "detected_action": "uncertain",
        "final_detected_action": "uncertain",
        "mapped_rule_key": "short_pass",
        "final_mapped_rule_key": "short_pass",
        "recommended_template": "short_pass",
        "analyzer_used": "video_analysis_router_v1",
        "fallback_used": True,
        "whether_fallback_template_used": True,
        "unsupported_action_for_current_analyzer": False,
        "raw_action_candidates": [
            {"action": "pass", "score": 0.56, "sources": ["stage2.pass"]},
            {"action": "shot", "score": 0.52, "sources": ["stage2.shot"]},
        ],
        "candidate_scores": {"pass": 0.56, "shot": 0.52},
        "sequence_context": {},
        "action_candidates": [
            {"label": "pass", "action": "pass", "display_name": "传球", "score": 0.56, "sources": ["stage2.pass"], "template": "short_pass"},
            {"label": "shot", "action": "shot", "display_name": "射门", "score": 0.52, "sources": ["stage2.shot"], "template": "shot_instep"},
        ],
    }
    _patch_video_pipeline(monkeypatch, route=route, score_overall=56.0)

    result = analyze_video(_video_path(), output_path=tmp_path / "confirmation.json")

    assert result["status"] == "provisional"
    assert result["fallback_used"] is True
    assert result["error_code"] == ""
    assert result["anomaly_reason"] == ""
    assert result["inconsistent_fields"] == []
    assert result["action_name"] == "review_required"
    assert result["action_display_name"] == "动作待确认"
    assert result["detected_action"] == "review_required"
    assert result["recommended_template"] == "review_required"
    assert result["overall_score"] is None
    assert result["score"]["level_code"] == "pending_confirmation"
    assert result["score"]["level_label"] == "待确认"
    assert result["fallback_reason"]


def test_video_analysis_logs_final_response_debug(monkeypatch, tmp_path, capsys):
    route = {
        "raw_detected_action": "pass_like",
        "action_label": "pass",
        "action_display_name": "传球",
        "action_confidence": 0.93,
        "confidence": 0.93,
        "confidence_gap": 0.41,
        "needs_confirmation": False,
        "uncertainty_reasons": [],
        "stage1_action_label": "kick",
        "stage1_confidence": 0.84,
        "detected_action": "pass",
        "final_detected_action": "pass",
        "mapped_rule_key": "short_pass",
        "final_mapped_rule_key": "short_pass",
        "recommended_template": "short_pass",
        "analyzer_used": "short_pass_analyzer_v1",
        "fallback_used": False,
        "whether_fallback_template_used": False,
        "unsupported_action_for_current_analyzer": False,
        "raw_action_candidates": [{"action": "pass", "score": 0.93, "sources": ["stage2.pass"]}],
        "candidate_scores": {"pass": 0.93, "shot": 0.11},
        "sequence_context": {},
        "action_candidates": [
            {"label": "pass", "action": "pass", "display_name": "传球", "score": 0.93, "sources": ["stage2.pass"], "template": "short_pass"}
        ],
    }
    _patch_video_pipeline(monkeypatch, route=route, score_overall=88.0)

    result = analyze_video(_video_path(), output_path=tmp_path / "final_debug.json")
    captured = capsys.readouterr().out

    assert "KICK_BACKEND_ANALYZER_RESULT_DEBUG" in captured
    assert '"final_action_name"' in captured
    assert '"final_action_display_name"' in captured
    assert '"final_recommended_template"' in captured
    assert '"final_overall_score"' in captured
    assert '"final_level_label"' in captured
    assert '"final_summary"' in captured
    assert '"fallback_used"' in captured
    assert '"fallback_reason"' in captured
    assert '"action_name"' in captured
    assert '"action_display_name"' in captured
    assert '"detected_action"' in captured
    assert '"recommended_template"' in captured
    assert '"score.overall"' in captured
    assert '"score.level_code"' in captured
    assert '"score.level_label"' in captured
    assert '"overall_score"' in captured
    assert '"summary"' in captured
    assert '"error_code"' in captured
    assert '"anomaly_reason"' in captured
    assert '"inconsistent_fields"' in captured
    assert result["status"] in {"ok", "provisional"}
