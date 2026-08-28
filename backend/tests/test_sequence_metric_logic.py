import scoring_engine

from analysis.shot_analysis import _video_rule_metrics
from feedback_engine import _format_metric_feedback
from scoring_engine import _score_metric, score_action


def test_receive_control_zone_success_rate_accepts_shorthand_thresholds():
    metric_cfg = {
        "direction": "higher_is_better",
        "display_name": "Receive Control Zone Success Rate / 接球控制区成功率",
        "beginner_thresholds": {
            "excellent": 0.82,
            "good": 0.65,
            "needs_work": 0.45,
        },
    }

    result = _score_metric("receive_control_zone_success_rate", metric_cfg, 0.97, audience="beginner")

    assert result["raw_value"] == 0.97
    assert result["band"] == "excellent"
    assert result["score"] == 100.0


def test_metric_feedback_matches_band_direction():
    metric_cfg = {
        "direction": "higher_is_better",
        "display_name": "Receive Control Zone Success Rate / 接球控制区成功率",
        "beginner_thresholds": {
            "excellent": 0.82,
            "good": 0.65,
            "needs_work": 0.45,
        },
    }

    excellent_result = {
        "metric": "receive_control_zone_success_rate",
        "label": "Receive Control Zone Success Rate / 接球控制区成功率",
        "raw_value": 0.97,
        "score": 100.0,
        "band": "excellent",
        "diagnostic_only": False,
    }
    poor_result = {
        "metric": "receive_control_zone_success_rate",
        "label": "Receive Control Zone Success Rate / 接球控制区成功率",
        "raw_value": 0.31,
        "score": 18.0,
        "band": "poor",
        "diagnostic_only": False,
    }

    assert "继续保持" in _format_metric_feedback(excellent_result, metric_cfg)
    assert "建议" in _format_metric_feedback(poor_result, metric_cfg)


def test_time_metrics_with_low_confidence_do_not_score_hard():
    metric_cfg = {
        "direction": "lower_is_better",
        "display_name": "Pass Execution Time / 传球完成时间",
        "beginner_thresholds": {
            "excellent_max": 1.8,
            "good_max": 2.8,
            "poor_over": 4.0,
        },
    }

    result = _score_metric(
        "pass_execution_time_s",
        metric_cfg,
        {
            "value": 0.0,
            "resolved": False,
            "low_confidence": True,
            "confidence": 0.0,
            "start_time": 0.0,
            "end_time": 0.0,
            "start_event": "support_plant",
            "end_event": "contact",
            "event_source": "unresolved",
        },
        audience="beginner",
    )

    assert result["score"] is None
    assert result["band"] in {"low_confidence", "unresolved"}
    assert result["raw_value"] == 0.0
    assert result["low_confidence"] is True
    assert result["resolved"] is False


def test_score_action_applies_confidence_adjustment_for_low_confidence_primary_metrics(monkeypatch):
    custom_rules = {
        "actions": {
            "pass_receive_sequence": {
                "display_name": "Pass Receive Sequence / 传接球序列",
                "primary_metrics": {
                    "pass_execution_time_s": {
                        "display_name": "Pass Execution Time / 传球完成时间",
                        "direction": "lower_is_better",
                        "beginner_thresholds": {
                            "excellent_max": 1.8,
                            "good_max": 2.8,
                            "poor_over": 4.0,
                        },
                        "source_class": "product_default",
                    },
                    "sequence_continuity_score": {
                        "display_name": "Sequence Continuity Score / 序列衔接分",
                        "direction": "higher_is_better",
                        "beginner_thresholds": {
                            "excellent": 0.85,
                            "good": 0.70,
                            "needs_work": 0.50,
                        },
                        "source_class": "product_default",
                    },
                },
                "secondary_metrics": {},
                "score_weights": {
                    "beginner": {
                        "pass_execution_time_s": 0.2,
                        "sequence_continuity_score": 0.8,
                    }
                },
            }
        }
    }

    monkeypatch.setattr(scoring_engine, "resolve_action_name", lambda action_name, rules: action_name)
    monkeypatch.setattr(scoring_engine, "get_action_rules", lambda action_name, rules: custom_rules["actions"]["pass_receive_sequence"])

    result = score_action(
        "pass_receive_sequence",
        {
            "pass_execution_time_s": {
                "value": 0.0,
                "resolved": False,
                "low_confidence": True,
                "confidence": 0.0,
                "start_time": 0.0,
                "end_time": 0.0,
                "start_event": "support_plant",
                "end_event": "pass_contact",
                "event_source": "unresolved",
            },
            "sequence_continuity_score": 0.96,
        },
        rules={"actions": {"pass_receive_sequence": {}}},
        audience="beginner",
        quality_result={"quality_status": "pass", "allow_micro_technique_score": True},
    )

    assert result["provisional_score"] == 100.0
    assert result["confidence_adjusted_score"] < result["provisional_score"]
    assert result["overall_score"] == result["confidence_adjusted_score"]
    assert result["overall_score"] <= 95.0
    assert result["low_confidence_metric_count"] == 1


def test_pass_receive_sequence_separates_time_windows():
    run_data = {
        "fps": 30.0,
        "frame_count": 176,
        "samples": [
            {"time": 0.00, "phase": "support", "events": {"support_plant": True}, "support_ball_ratio": 0.30, "swing_ball_ratio": 0.18, "ball_speed_ratio": 0.03, "sequence_ready": False},
            {"time": 0.18, "phase": "contact", "events": {"contact": True}, "support_ball_ratio": 0.28, "swing_ball_ratio": 0.16, "ball_speed_ratio": 0.14, "sequence_ready": False},
            {"time": 0.52, "phase": "follow_through", "events": {}, "support_ball_ratio": 0.26, "swing_ball_ratio": 0.15, "ball_speed_ratio": 0.12, "sequence_ready": False},
            {"time": 0.90, "phase": "contact", "events": {"contact": True}, "support_ball_ratio": 0.22, "swing_ball_ratio": 0.14, "ball_speed_ratio": 0.11, "sequence_ready": False},
            {"time": 1.20, "phase": "recovery", "events": {}, "support_ball_ratio": 0.18, "swing_ball_ratio": 0.13, "ball_speed_ratio": 0.05, "sequence_ready": True},
            {"time": 1.50, "phase": "set", "events": {}, "support_ball_ratio": 0.17, "swing_ball_ratio": 0.12, "ball_speed_ratio": 0.04, "sequence_ready": True},
            {"time": 5.82, "phase": "follow_through", "events": {}, "support_ball_ratio": 0.17, "swing_ball_ratio": 0.12, "ball_speed_ratio": 0.03, "sequence_ready": True},
        ],
    }
    metrics = {
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
    }
    event_times = {
        "support": 0.0,
        "contact": 0.18,
        "follow_through": 0.52,
        "sequence_complete": 5.82,
    }

    result = _video_rule_metrics("pass_receive_sequence", metrics, run_data, event_times, calibration=None)

    assert result["pass_execution_time_s"]["value"] > 0.0
    assert result["pass_execution_time_s"]["resolved"] is True
    assert result["pass_execution_time_s"]["low_confidence"] is False
    assert result["metric_debug"]["pass_execution_time"]["start_event"] == "support_plant"
    assert result["metric_debug"]["pass_execution_time"]["end_event"] == "pass_contact"

    assert result["pass_receive_gap_s"]["value"] > 0.0
    assert result["pass_receive_gap_s"]["resolved"] is True
    assert result["pass_receive_gap_s"]["low_confidence"] is False
    assert result["metric_debug"]["pass_receive_gap"]["start_event"] == "pass_contact"
    assert result["metric_debug"]["pass_receive_gap"]["end_event"] == "receive_contact"

    assert result["receive_stabilization_time_s"]["value"] > 0.0
    assert result["receive_stabilization_time_s"]["resolved"] is True
    assert result["receive_stabilization_time_s"]["low_confidence"] is False
    assert result["metric_debug"]["receive_stabilization_time"]["start_event"] == "receive_contact"
    assert result["metric_debug"]["receive_stabilization_time"]["end_event"] == "receive_stable_state"

    assert result["metric_debug"]["pass_receive_gap"]["end_time"] < result["metric_debug"]["receive_stabilization_time"]["end_time"]
    assert result["metric_debug"]["pass_execution_time"]["end_time"] < result["metric_debug"]["pass_receive_gap"]["end_time"]
    assert result["metric_debug"]["receive_stabilization_time"]["event_source"] == "stable_control_window"
    assert result["metric_debug"]["fallback_flags"]["used_video_end_time"] is False


def test_pass_receive_sequence_stays_low_confidence_without_stable_end():
    run_data = {
        "fps": 30.0,
        "frame_count": 180,
        "samples": [
            {"time": 0.00, "phase": "support", "events": {"support_plant": True}, "support_ball_ratio": 0.30, "swing_ball_ratio": 0.18, "ball_speed_ratio": 0.03, "sequence_ready": False},
            {"time": 0.18, "phase": "contact", "events": {"contact": True}, "support_ball_ratio": 0.28, "swing_ball_ratio": 0.16, "ball_speed_ratio": 0.14, "sequence_ready": False},
            {"time": 0.52, "phase": "follow_through", "events": {}, "support_ball_ratio": 0.26, "swing_ball_ratio": 0.15, "ball_speed_ratio": 0.12, "sequence_ready": False},
            {"time": 0.90, "phase": "recovery", "events": {}, "support_ball_ratio": 0.22, "swing_ball_ratio": 0.14, "ball_speed_ratio": 0.09, "sequence_ready": True},
            {"time": 1.10, "phase": "follow_through", "events": {}, "support_ball_ratio": 0.24, "swing_ball_ratio": 0.14, "ball_speed_ratio": 0.10, "sequence_ready": False},
            {"time": 5.95, "phase": "follow_through", "events": {}, "support_ball_ratio": 0.22, "swing_ball_ratio": 0.13, "ball_speed_ratio": 0.09, "sequence_ready": False},
        ],
    }
    metrics = {
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
    }
    event_times = {
        "support": 0.0,
        "contact": 0.18,
        "follow_through": 0.52,
        "sequence_complete": 5.95,
    }

    result = _video_rule_metrics("pass_receive_sequence", metrics, run_data, event_times, calibration=None)

    assert result["pass_execution_time_s"]["value"] > 0.0
    assert result["metric_debug"]["pass_receive_gap"]["resolved"] is False
    assert result["metric_debug"]["pass_receive_gap"]["low_confidence"] is True
    assert result["pass_receive_gap_s"]["value"] is not None
    assert result["metric_debug"]["receive_stabilization_time"]["resolved"] is False
    assert result["metric_debug"]["receive_stabilization_time"]["low_confidence"] is True
    assert result["receive_stabilization_time_s"]["value"] is None
    assert result["metric_debug"]["receive_stabilization_time"]["end_event"] == "unresolved"
    assert result["metric_debug"]["receive_stabilization_time"]["low_confidence"] is True
