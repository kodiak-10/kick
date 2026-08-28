import json
from pathlib import Path

import cv2
import pytest

import coach
from coach import analyze_video
import analysis.shot_analysis as shot_analysis


def test_video_analysis_returns_unified_json(tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    result = analyze_video(video_path, output_path=out_path)

    assert result["analysis_mode"] == "analyze_video"
    assert isinstance(result["analyzer_used"], str) and result["analyzer_used"]
    assert result["input_video_path"] == str(video_path)
    assert "detected_action" in result
    assert "action_confidence" in result
    assert "mapped_rule_key" in result
    assert "recommended_template" in result
    assert "fallback_used" in result
    assert "whether_fallback_template_used" in result
    assert "unsupported_action_for_current_analyzer" in result
    assert "raw_action_candidates" in result
    assert "candidate_scores" in result
    assert "sequence_upgrade_applied" in result
    assert "sequence_upgrade_reason" in result
    assert "final_detected_action" in result
    assert "final_mapped_rule_key" in result
    assert "score_source" in result
    assert "ball_speed_measurement_type" in result
    assert "score" in result and isinstance(result["score"], dict)
    assert "overall_score" in result
    assert result["overall_score"] == result["score"]["overall"]
    assert "primary_score" not in result
    assert 0.0 <= float(result["analysis_confidence"]) <= 1.0
    assert result["status"] in {"ok", "provisional", "error"}
    assert out_path.exists()

    payload = json.loads(out_path.read_text())
    assert payload["analysis_mode"] == "analyze_video"
    assert "overall_score" in payload
    assert payload["overall_score"] == payload["score"]["overall"]


@pytest.mark.parametrize(
    "detected_action,expected_rule_key,expected_analyzer,expected_action_name",
    [
        ("pass_like", "short_pass", "short_pass_analyzer_v1", "pass"),
        ("shot_like", "shot_instep", "shot_instep_analyzer_v1", "shot"),
    ],
)
def test_video_analysis_routes_supported_actions(monkeypatch, tmp_path, detected_action, expected_rule_key, expected_analyzer, expected_action_name):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}],
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
                "support_ball_ratio": 0.22,
                "swing_ball_ratio": 0.12,
                "ball_speed_ratio": 0.18,
                "stability": 0.82,
                "sequence_confidence": 0.78,
                "visibility": 0.9,
                "ball_contact": 0.86,
                "ball_confidence": 0.8,
                "move_ratio": 0.21,
                "trunk_lean_deg": 8.0,
                "balance": 0.08,
                "symmetry": 3.0,
                "valgus_ratio": 1.02,
            },
            {"preparation": 82.0, "support": 84.0, "contact": 86.0, "follow_through": 88.0},
            {"support": 0.25, "contact": 0.45, "follow_through": 0.6},
            {"analysis_confidence": 0.83},
            {"contact": 0.4, "follow_through": 0.62},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": detected_action,
            "action_label": "pass" if detected_action == "pass_like" else "shot",
            "action_display_name": "传球" if detected_action == "pass_like" else "射门",
            "action_confidence": 0.91,
            "detection_source": "temporal",
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_load_video_calibration",
        lambda calibration_path=None: None,
    )
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
            "action_display_name": "传球" if action_name == "short_pass" else "射门",
            "quality_status": "pass",
            "overall_score": 88.0,
            "outcome_score": 86.0,
            "technique_score": 84.0,
            "primary_score": 87.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": 88.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 88.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
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

    result = analyze_video(video_path, output_path=out_path)

    assert result["detected_action"] == expected_action_name
    assert result["final_detected_action"] == expected_action_name
    assert result["mapped_rule_key"] == expected_rule_key
    assert result["final_mapped_rule_key"] == expected_rule_key
    assert result["analyzer_used"] == expected_analyzer
    assert result["unsupported_action_for_current_analyzer"] is False
    assert result["fallback_used"] is False
    assert result["status"] == "ok"
    assert result["action_name"] == expected_action_name
    assert result["recommended_template"] == expected_rule_key
    assert result["action_display_name"] == ("传球" if expected_rule_key == "short_pass" else "射门")
    assert result["score"]["source"] == "proxy_rule_metrics"
    assert "overall_score" in result
    assert result["overall_score"] == result["score"]["overall"]
    assert out_path.exists()


def test_video_analysis_normalizes_receive_actions(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}],
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
                "body_span_px": 160.0,
                "support_ball_ratio": 0.24,
                "swing_ball_ratio": 0.13,
                "ball_speed_ratio": 0.12,
                "stability": 0.7,
                "sequence_confidence": 0.6,
                "visibility": 0.88,
                "ball_contact": 0.75,
                "ball_confidence": 0.7,
                "move_ratio": 0.18,
                "trunk_lean_deg": 9.0,
                "balance": 0.1,
                "symmetry": 4.0,
                "valgus_ratio": 1.0,
            },
            {"preparation": 78.0, "support": 80.0, "contact": 82.0, "follow_through": 84.0},
            {"support": 0.2, "contact": 0.4, "follow_through": 0.55},
            {"analysis_confidence": 0.72},
            {"contact": 0.36, "follow_through": 0.57},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": "first_touch_like",
            "action_label": "first_touch",
            "action_display_name": "停球",
            "action_confidence": 0.86,
            "detection_source": "temporal",
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_load_video_calibration",
        lambda calibration_path=None: None,
    )
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
            "action_display_name": "停球",
            "quality_status": "pass",
            "overall_score": 72.0,
            "outcome_score": 71.0,
            "technique_score": 73.0,
            "primary_score": 72.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": 72.0, "raw_value": None, "role": "summary", "band": "fair", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 72.0, "raw_value": None, "role": "summary", "band": "fair", "source": "metric_proxy"},
            "metric_results": [],
        },
    )

    result = analyze_video(video_path, output_path=out_path)

    assert result["detected_action"] == "receive"
    assert result["final_detected_action"] == "receive"
    assert result["mapped_rule_key"] == "receive_control"
    assert result["final_mapped_rule_key"] == "receive_control"
    assert result["recommended_template"] == "receive_control"
    assert result["action_name"] == "receive"
    assert result["action_display_name"] == "停球"
    assert result["analyzer_used"] == "receive_control_analyzer_v1"
    assert result["sequence_upgrade_applied"] is False
    assert result["unsupported_action_for_current_analyzer"] is False
    assert result["fallback_used"] is False
    assert result["status"] == "ok"
    assert result["score"]["level_code"] == "fair"
    assert result["score_source"] == "proxy_rule_metrics"
    assert "overall_score" in result
    assert result["overall_score"] == result["score"]["overall"]
    assert out_path.exists()


def test_video_analysis_prefers_user_selected_action(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}],
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
                "support_ball_ratio": 0.22,
                "swing_ball_ratio": 0.12,
                "ball_speed_ratio": 0.18,
                "stability": 0.82,
                "sequence_confidence": 0.78,
                "visibility": 0.9,
                "ball_contact": 0.86,
                "ball_confidence": 0.8,
                "move_ratio": 0.21,
                "trunk_lean_deg": 8.0,
                "balance": 0.08,
                "symmetry": 3.0,
                "valgus_ratio": 1.02,
            },
            {"preparation": 82.0, "support": 84.0, "contact": 86.0, "follow_through": 88.0},
            {"support": 0.25, "contact": 0.45, "follow_through": 0.6},
            {"analysis_confidence": 0.83},
            {"contact": 0.4, "follow_through": 0.62},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": "shot_like",
            "action_label": "shot",
            "action_display_name": "射门",
            "action_confidence": 0.93,
            "confidence_gap": 0.31,
            "detection_source": "temporal",
            "needs_confirmation": False,
            "uncertainty_reasons": [],
            "action_candidates": [
                {"label": "shot", "action": "shot", "display_name": "射门", "score": 0.93, "sources": ["stage2.shot"], "template": "shot_instep"},
                {"label": "pass", "action": "pass", "display_name": "传球", "score": 0.48, "sources": ["stage2.pass"], "template": "short_pass"},
            ],
            "stage1_action_label": "kick",
            "stage1_confidence": 0.85,
            "raw_action_candidates": [
                {"action": "shot_like", "score": 0.93, "sources": ["stage2.shot"]},
                {"action": "pass_like", "score": 0.48, "sources": ["stage2.pass"]},
            ],
            "candidate_scores": {"shot": 0.93, "pass": 0.48},
            "sequence_context": {},
            "mapped_rule_key": "shot_instep",
            "recommended_template": "shot_instep",
            "fallback_used": False,
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": False,
            "analyzer_used": "shot_instep_analyzer_v1",
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_load_video_calibration",
        lambda calibration_path=None: None,
    )
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
            "action_display_name": "传球" if action_name == "short_pass" else "射门",
            "quality_status": "pass",
            "overall_score": 86.0,
            "outcome_score": 84.0,
            "technique_score": 85.0,
            "primary_score": 85.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": 86.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 86.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
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

    result = analyze_video(video_path, output_path=out_path, selected_action="pass")

    assert result["analysis_routed_by"] == "user_selected"
    assert result["selected_action"] == "pass"
    assert result["analysis_template"] == "short_pass"
    assert result["routed_analyzer"] == "short_pass_analyzer_v1"
    assert result["detected_action"] == "pass"
    assert result["final_detected_action"] == "pass"
    assert result["mapped_rule_key"] == "short_pass"
    assert result["recommended_template"] == "short_pass"
    assert result["action_display_name"] == "传球"
    assert result["suggested_action"] == "shot"
    assert result["suggestion_reason"]
    assert result["fallback_used"] is False
    assert result["status"] == "ok"
    assert out_path.exists()


def test_video_analysis_prefers_user_selected_sequence_action(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}],
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
                "support_ball_ratio": 0.22,
                "swing_ball_ratio": 0.12,
                "ball_speed_ratio": 0.18,
                "stability": 0.82,
                "sequence_confidence": 0.78,
                "visibility": 0.9,
                "ball_contact": 0.86,
                "ball_confidence": 0.8,
                "move_ratio": 0.21,
                "trunk_lean_deg": 8.0,
                "balance": 0.08,
                "symmetry": 3.0,
                "valgus_ratio": 1.02,
            },
            {"preparation": 82.0, "support": 84.0, "contact": 86.0, "follow_through": 88.0},
            {"support": 0.25, "contact": 0.45, "follow_through": 0.6},
            {"analysis_confidence": 0.83},
            {"contact": 0.4, "follow_through": 0.62},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": "shot_like",
            "action_label": "shot",
            "action_display_name": "射门",
            "action_confidence": 0.93,
            "confidence_gap": 0.31,
            "detection_source": "temporal",
            "needs_confirmation": False,
            "uncertainty_reasons": [],
            "action_candidates": [
                {"label": "shot", "action": "shot", "display_name": "射门", "score": 0.93, "sources": ["stage2.shot"], "template": "shot_instep"},
                {"label": "pass_receive_sequence", "action": "pass_receive_sequence", "display_name": "传接球", "score": 0.62, "sources": ["stage2.sequence"], "template": "pass_receive_sequence"},
            ],
            "stage1_action_label": "kick",
            "stage1_confidence": 0.85,
            "raw_action_candidates": [
                {"action": "shot_like", "score": 0.93, "sources": ["stage2.shot"]},
                {"action": "pass_receive_sequence", "score": 0.62, "sources": ["stage2.sequence"]},
            ],
            "candidate_scores": {"shot": 0.93, "pass_receive_sequence": 0.62},
            "sequence_context": {},
            "mapped_rule_key": "shot_instep",
            "recommended_template": "shot_instep",
            "fallback_used": False,
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": False,
            "analyzer_used": "shot_instep_analyzer_v1",
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_load_video_calibration",
        lambda calibration_path=None: None,
    )
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
            "action_display_name": "传接球" if action_name == "pass_receive_sequence" else "射门",
            "quality_status": "pass",
            "overall_score": 86.0,
            "outcome_score": 84.0,
            "technique_score": 85.0,
            "primary_score": 85.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": 86.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 86.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
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

    result = analyze_video(video_path, output_path=out_path, selected_action="pass_receive_sequence")

    assert result["analysis_routed_by"] == "user_selected"
    assert result["selected_action"] == "pass_receive_sequence"
    assert result["analysis_template"] == "pass_receive_sequence"
    assert result["routed_analyzer"] == "pass_receive_sequence_engine_v1"
    assert result["detected_action"] == "pass_receive_sequence"
    assert result["final_detected_action"] == "pass_receive_sequence"
    assert result["mapped_rule_key"] == "pass_receive_sequence"
    assert result["recommended_template"] == "pass_receive_sequence"
    assert result["action_display_name"] == "传接球"
    assert result["suggested_action"] == "shot"
    assert result["suggestion_reason"]
    assert result["fallback_used"] is False
    assert result["status"] == "ok"
    assert out_path.exists()


def test_video_analysis_promotes_pass_receive_sequence(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}, {"time": 0.5}, {"time": 1.0}],
            "frame_count": 90,
            "fps": 30.0,
            "temporal_best_prediction": {
                "label": "pass_like",
                "confidence": 0.86,
                "source": "temporal",
                "features": {
                    "pass_score": 0.84,
                    "first_touch_score": 0.79,
                    "shoot_score": 0.28,
                },
            },
            "temporal_action_votes": {"pass_like": 4, "first_touch_like": 3},
            "sequence_snapshot": {
                "phase": "follow_through",
                "phase_confidence": 0.81,
                "phase_locked": True,
                "sequence_active": True,
                "sequence_ready": True,
                "action_label": "pass_like",
                "support_side": "left",
                "swing_side": "right",
                "events": {"support_plant": True, "contact": True, "follow_through_complete": True, "sequence_complete": False},
                "metrics": {},
            },
            "sequence_action_label": "pass_like",
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_aggregate_metrics",
        lambda samples: (
            {
                "body_span_px": 190.0,
                "support_ball_ratio": 0.21,
                "swing_ball_ratio": 0.13,
                "ball_speed_ratio": 0.14,
                "stability": 0.84,
                "sequence_confidence": 0.79,
                "visibility": 0.91,
                "ball_contact": 0.88,
                "ball_confidence": 0.81,
                "move_ratio": 0.18,
                "trunk_lean_deg": 7.0,
                "balance": 0.07,
                "symmetry": 2.0,
                "valgus_ratio": 1.01,
                "phase_locked": 1.0,
            },
            {"preparation": 81.0, "support": 83.0, "contact": 85.0, "follow_through": 87.0},
            {"support": 0.28, "contact": 0.52, "follow_through": 0.78},
            {"analysis_confidence": 0.87},
            {"contact": 0.46, "follow_through": 0.84},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": "first_touch_like",
            "action_confidence": 0.92,
            "detection_source": "temporal",
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "_load_video_calibration",
        lambda calibration_path=None: None,
    )
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
            "action_display_name": "传接球",
            "quality_status": "pass",
            "overall_score": 87.0,
            "outcome_score": None,
            "technique_score": None,
            "primary_score": None,
            "sub_scores": {},
            "triggered_rules": [
                {
                    "id": "sequence_continuity_score",
                    "metric": "sequence_continuity_score",
                    "label": "序列衔接分",
                    "severity": "warn",
                    "reason": "序列衔接分表现仍可继续提升。",
                    "phase": "follow_through",
                    "time": 0.8,
                    "role": "primary",
                    "quality_impact": "primary",
                }
            ],
            "best_trial": {"metric": "overall", "label": "summary", "score": 87.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 87.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "metric_results": [
                {
                    "metric": "pass_endpoint_error_m",
                    "label": "Pass Endpoint Error / 传球终点误差",
                    "raw_value": 0.22,
                    "score": 84.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.18,
                },
                {
                    "metric": "pass_execution_time_s",
                    "label": "Pass Execution Time / 传球完成时间",
                    "raw_value": 1.65,
                    "score": 88.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.12,
                },
                {
                    "metric": "receive_control_zone_success_rate",
                    "label": "Receive Control Zone Success Rate / 接球控制区成功率",
                    "raw_value": 0.81,
                    "score": 86.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.18,
                },
                {
                    "metric": "receive_stabilization_time_s",
                    "label": "Receive Stabilization Time / 接球稳定时间",
                    "raw_value": 1.02,
                    "score": 83.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.12,
                },
                {
                    "metric": "receive_corrective_touch_count",
                    "label": "Receive Corrective Touch Count / 接球补救触球数",
                    "raw_value": 1.0,
                    "score": 90.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.10,
                },
                {
                    "metric": "sequence_continuity_score",
                    "label": "Sequence Continuity Score / 序列衔接分",
                    "raw_value": 0.82,
                    "score": 87.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.18,
                },
                {
                    "metric": "next_action_readiness",
                    "label": "Next Action Readiness / 下一动作准备度",
                    "raw_value": 0.76,
                    "score": 85.0,
                    "band": "good",
                    "role": "outcome",
                    "source_class": "product_default",
                    "use_as": "",
                    "weight": 0.12,
                },
            ],
        },
    )
    monkeypatch.setattr(
        shot_analysis,
        "build_feedback_messages",
        lambda **kwargs: {"feedback_messages": ["传接球链条整体可用，继续优化衔接。"], "fail_reasons": []},
    )
    monkeypatch.setattr(
        shot_analysis,
        "locate_error_timestamps",
        lambda **kwargs: {"error_timestamps": []},
    )

    result = analyze_video(video_path, output_path=out_path)

    assert result["input_action_name"] == "first_touch_like"
    assert result["detected_action"] == "pass_receive_sequence"
    assert result["final_detected_action"] == "pass_receive_sequence"
    assert result["mapped_rule_key"] == "pass_receive_sequence"
    assert result["final_mapped_rule_key"] == "pass_receive_sequence"
    assert result["analyzer_used"] == "pass_receive_sequence_engine_v1"
    assert result["unsupported_action_for_current_analyzer"] is False
    assert result["fallback_used"] is False
    assert result["sequence_upgrade_applied"] is True
    assert result["sequence_upgrade_reason"]
    assert result["candidate_scores"]["pass_like"] >= 0.8
    assert result["candidate_scores"]["first_touch_like"] >= 0.7
    assert result["raw_action_candidates"]
    assert result["status"] == "ok"
    assert result["overall_score"] == result["score"]["overall"]
    assert result["score"]["provisional_score"] == result["score"]["confidence_adjusted_score"]
    assert result["pass_subscore"] == result["score"]["pass_subscore"]
    assert result["receive_subscore"] == result["score"]["receive_subscore"]
    assert result["sequence_continuity_score"] == result["score"]["sequence_continuity_score"]
    assert result["next_action_readiness"] == result["score"]["next_action_readiness"]
    assert result["metric_debug"]["receive_control_zone_success_rate_band_logic"]["band"] == "good"
    assert "pass_execution_time_debug" not in result
    assert "pass_receive_gap_debug" not in result
    assert "receive_stabilization_time_debug" not in result
    assert result["metric_debug"]["pass_execution_time"]["low_confidence"] is True
    assert result["metric_debug"]["pass_receive_gap"]["low_confidence"] is True
    assert result["metric_debug"]["receive_stabilization_time"]["low_confidence"] is True
    assert "technical_execution" not in result["score"]
    assert "control_stability" not in result["score"]
    assert "action_safety" not in result["score"]
    assert out_path.exists()


def test_dispatch_routes_video_path_to_generic_analyzer(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    called = {}

    def fake_analyze_video(path, *, output_path=None, work_dir=None, frame_stride=1, calibration_path=None):
        called["path"] = Path(path)
        called["output_path"] = Path(output_path) if output_path is not None else None
        return {
            "analysis_mode": "analyze_video",
            "analyzer_used": "short_pass_analyzer_v1",
            "input_video_path": str(path),
            "video_path": str(Path(path)),
            "detected_action": "pass_like",
            "action_confidence": 0.78,
            "mapped_rule_key": "short_pass",
            "recommended_template": "short_pass",
            "fallback_used": False,
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": False,
            "score_source": "proxy_rule_metrics",
            "ball_speed_measurement_type": "proxy",
            "action_name": "short_pass",
            "input_action_name": "pass_like",
            "resolved_action_name": "short_pass",
            "action_display_name": "短传",
            "score": {
                "overall": 0.0,
                "technical_execution": 0.0,
                "control_stability": 0.0,
                "action_safety": 0.0,
                "level_code": "needs_strengthen",
                "level_label": "需加强",
                "source": "proxy_rule_metrics",
                "measurement_mode": "proxy",
            },
            "summary": "ok",
            "issues": [],
            "phase_scores": {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            "analysis_confidence": 0.8,
            "score_ready": True,
            "scoring_state": "ready_to_score",
            "status": "ok",
            "primary_metrics": [],
            "sub_scores": {},
            "triggered_rules": [],
            "fail_reasons": [],
            "feedback_messages": [],
            "error_timestamps": [],
            "quality_status": "pass",
            "quality_gate": {"quality_status": "pass", "passed": True, "observed": {}},
            "best_trial": None,
            "worst_trial": None,
            "rule_metrics": {},
            "warnings": [],
        }

    def fail_if_shot(*args, **kwargs):
        raise AssertionError("analyze_shot should not be called for generic video analysis")

    monkeypatch.setattr(coach, "analyze_video", fake_analyze_video)
    monkeypatch.setattr(coach, "analyze_shot", fail_if_shot)

    args = coach.build_parser().parse_args(["--video_path", str(video_path), "--repo_path", str(tmp_path)])
    coach.dispatch(args)

    assert called["path"] == video_path
    assert called["output_path"] == tmp_path / "logs" / f"video_analysis_{video_path.stem}.json"


def test_dispatch_routes_legacy_shot_mode_to_generic_analyzer(monkeypatch, tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    called = {}

    def fake_analyze_video(path, *, output_path=None, work_dir=None, frame_stride=1, calibration_path=None):
        called["path"] = Path(path)
        called["output_path"] = Path(output_path) if output_path is not None else None
        return {
            "analysis_mode": "analyze_video",
            "analyzer_used": "video_analysis_router_v1",
            "input_video_path": str(path),
            "video_path": str(Path(path)),
            "detected_action": "pass_like",
            "action_confidence": 0.78,
            "mapped_rule_key": "short_pass",
            "recommended_template": "short_pass",
            "fallback_used": False,
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": False,
            "score_source": "proxy_rule_metrics",
            "ball_speed_measurement_type": "proxy",
            "action_name": "short_pass",
            "input_action_name": "pass_like",
            "resolved_action_name": "short_pass",
            "action_display_name": "短传",
            "score": {
                "overall": 0.0,
                "technical_execution": 0.0,
                "control_stability": 0.0,
                "action_safety": 0.0,
                "level_code": "needs_strengthen",
                "level_label": "需加强",
                "source": "proxy_rule_metrics",
                "measurement_mode": "proxy",
            },
            "summary": "ok",
            "issues": [],
            "phase_scores": {"preparation": 0.0, "support": 0.0, "contact": 0.0, "follow_through": 0.0},
            "analysis_confidence": 0.8,
            "score_ready": True,
            "scoring_state": "ready_to_score",
            "status": "ok",
            "primary_metrics": [],
            "sub_scores": {},
            "triggered_rules": [],
            "fail_reasons": [],
            "feedback_messages": [],
            "error_timestamps": [],
            "quality_status": "pass",
            "quality_gate": {"quality_status": "pass", "passed": True, "observed": {}},
            "best_trial": None,
            "worst_trial": None,
            "rule_metrics": {},
            "warnings": [],
        }

    def fail_if_shot(*args, **kwargs):
        raise AssertionError("analyze_shot should not be called for --mode shot")

    monkeypatch.setattr(coach, "analyze_video", fake_analyze_video)
    monkeypatch.setattr(coach, "analyze_shot", fail_if_shot)

    args = coach.build_parser().parse_args(["--mode", "shot", "--video_path", str(video_path), "--repo_path", str(tmp_path)])
    coach.dispatch(args)

    assert called["path"] == video_path
    assert called["output_path"] == tmp_path / "logs" / f"video_analysis_{video_path.stem}.json"


def test_fast_mode_plan_uses_windows_for_long_video():
    stride, windows = shot_analysis._build_fast_mode_plan(
        frame_count=900,
        fps=30.0,
        duration_s=30.0,
        frame_stride=1,
        fast_mode_enabled=True,
    )

    assert stride >= 4
    assert windows
    assert windows[0][0] == 0
    assert windows[-1][1] == 899


def test_video_analysis_emits_fast_mode_logs(monkeypatch, tmp_path, capsys):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "video_analysis.json"

    monkeypatch.setattr(
        shot_analysis,
        "_process_video",
        lambda *args, **kwargs: {
            "samples": [{"time": 0.0}],
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
                "support_ball_ratio": 0.22,
                "swing_ball_ratio": 0.12,
                "ball_speed_ratio": 0.18,
                "stability": 0.82,
                "sequence_confidence": 0.78,
                "visibility": 0.9,
                "ball_contact": 0.86,
                "ball_confidence": 0.8,
                "move_ratio": 0.21,
                "trunk_lean_deg": 8.0,
                "balance": 0.08,
                "symmetry": 3.0,
                "valgus_ratio": 1.02,
            },
            {"preparation": 82.0, "support": 84.0, "contact": 86.0, "follow_through": 88.0},
            {"support": 0.25, "contact": 0.45, "follow_through": 0.6},
            {"analysis_confidence": 0.83},
            {"contact": 0.4, "follow_through": 0.62},
            [],
        ),
    )
    monkeypatch.setattr(
        shot_analysis,
        "_video_detect_action_context",
        lambda run_data, metrics, evidence: {
            "detected_action": "pass_like",
            "action_label": "pass",
            "action_display_name": "传球",
            "action_confidence": 0.93,
            "confidence_gap": 0.31,
            "detection_source": "temporal",
            "needs_confirmation": False,
            "uncertainty_reasons": [],
            "action_candidates": [],
            "stage1_action_label": "kick",
            "stage1_confidence": 0.85,
            "raw_action_candidates": [],
            "candidate_scores": {},
            "sequence_context": {},
            "mapped_rule_key": "short_pass",
            "recommended_template": "short_pass",
            "fallback_used": False,
            "whether_fallback_template_used": False,
            "unsupported_action_for_current_analyzer": False,
            "analyzer_used": "short_pass_analyzer_v1",
        },
    )
    monkeypatch.setattr(shot_analysis, "_load_video_calibration", lambda calibration_path=None: None)
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
            "action_display_name": "传球",
            "quality_status": "pass",
            "overall_score": 88.0,
            "outcome_score": 86.0,
            "technique_score": 84.0,
            "primary_score": 87.0,
            "sub_scores": {},
            "triggered_rules": [],
            "best_trial": {"metric": "overall", "label": "summary", "score": 88.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
            "worst_trial": {"metric": "overall", "label": "summary", "score": 88.0, "raw_value": None, "role": "summary", "band": "good", "source": "metric_proxy"},
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

    analyze_video(video_path, output_path=out_path)
    captured = capsys.readouterr().out

    assert "KICK_BACKEND_VIDEO_DURATION =" in captured
    assert "KICK_BACKEND_FRAME_COUNT = 60" in captured
    assert "KICK_BACKEND_PROCESSING_TIME =" in captured
    assert "KICK_BACKEND_FAST_MODE_ENABLED = False" in captured


def test_video_analysis_uses_long_video_locator_for_16s_pass_clip(tmp_path):
    source_video = Path(__file__).resolve().parents[1] / "ios" / "AICoach" / "AICoach" / "Resources" / "传球.mp4"
    assert source_video.exists()

    cap = cv2.VideoCapture(str(source_video))
    assert cap.isOpened()

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frames.append(frame)
    cap.release()
    assert frames

    height, width = frames[0].shape[:2]
    output_video = tmp_path / "long_pass_16_6s.mp4"
    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        30.0,
        (width, height),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV mp4 writer is unavailable in this environment")

    for index in range(498):
        writer.write(frames[index % len(frames)])
    writer.release()

    result = analyze_video(output_video, selected_action="pass")

    assert result["selected_action"] == "pass"
    assert result["analysis_routed_by"] == "user_selected"
    assert result["routed_analyzer"] == "short_pass_analyzer_v1"
    assert result["video_duration_s"] == pytest.approx(16.6, abs=0.2)
    assert result["long_video_localized"] is True
    assert result["fast_mode_enabled"] is True
    assert result["candidate_window_count"] == 0
    assert result["status"] == "provisional"
    assert result["analysis_status"] == "partial"
    assert result["failure_reason"] is None
    assert result["error_code"] == ""
    assert result["evidence_limited_fallback"] is True
    assert result["action_name"] == "pass"
    assert result["detected_action"] == "pass"
    assert result["recommended_template"] == "short_pass"
    assert result["action_display_name"] == "传球"
    assert result["score"]["level_label"] == "参考项"
    assert result["overall_score"] is None
