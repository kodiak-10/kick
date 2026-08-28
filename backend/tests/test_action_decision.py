from analysis.action_decision import build_video_action_decision
from analysis.shot_analysis import video_analysis_router_v1
from rules_loader import load_football_rules


def _make_samples(*, frame_count: int = 60, goal_visible: bool = False):
    samples = []
    for idx in range(frame_count):
        samples.append(
            {
                "time": idx / 30.0,
                "ball_present": True,
                "ball_x": 80.0 + idx * 2.0,
                "ball_y": 120.0,
                "ball_speed_ratio": 0.10 if 18 <= idx <= 24 else 0.06,
                "support_ball_ratio": 0.24,
                "swing_ball_ratio": 0.09,
                "support_speed_ratio": 0.12,
                "swing_speed_ratio": 0.10,
                "phase_confidence": 0.72,
                "visibility": 0.90,
                "stability": 0.80,
                "move_ratio": 0.20,
                "trunk_lean_deg": 7.0,
                "balance": 0.06,
                "goal_visible": goal_visible,
                "events": {
                    "contact": idx == 20,
                    "support_plant": idx == 18,
                    "follow_through_complete": idx == 30,
                },
            }
        )
    return samples


def test_build_video_action_decision_prefers_pass_over_shot():
    run_data = {
        "samples": _make_samples(goal_visible=False),
        "fps": 30.0,
        "frame_count": 60,
        "temporal_best_prediction": {
            "label": "pass_like",
            "confidence": 0.84,
            "features": {
                "pass_score": 0.88,
                "shoot_score": 0.16,
                "first_touch_score": 0.08,
            },
        },
    }
    metrics = {
        "body_span_px": 180.0,
        "support_ball_ratio": 0.24,
        "swing_ball_ratio": 0.09,
        "ball_speed_ratio": 0.10,
        "stability": 0.80,
        "sequence_confidence": 0.72,
        "visibility": 0.90,
        "ball_contact": 0.90,
        "ball_confidence": 0.86,
        "move_ratio": 0.20,
        "trunk_lean_deg": 7.0,
        "balance": 0.06,
        "symmetry": 2.0,
        "valgus_ratio": 1.02,
    }
    evidence = {
        "pose_frames": 50,
        "ball_frames": 55,
        "analysis_confidence": 0.86,
    }

    decision = build_video_action_decision(run_data, metrics, evidence)

    assert decision["stage1_action_label"] == "kick"
    assert decision["action_label"] == "pass"
    assert decision["action_display_name"] == "传球"
    assert decision["recommended_template"] == "short_pass"
    assert decision["needs_confirmation"] is False
    assert decision["confidence"] >= decision["confidence_gap"]
    assert decision["raw_detected_action"] == "pass_like"


def test_video_analysis_router_forces_confirmation_on_ambiguous_result():
    decision = {
        "raw_detected_action": "pass_like",
        "action_label": "uncertain",
        "action_display_name": "动作待确认",
        "action_candidates": [
            {
                "label": "pass",
                "action": "pass",
                "display_name": "传球",
                "score": 0.56,
                "sources": ["stage2.pass"],
                "template": "short_pass",
            },
            {
                "label": "shot",
                "action": "shot",
                "display_name": "射门",
                "score": 0.52,
                "sources": ["stage2.shot"],
                "template": "shot_instep",
            },
        ],
        "confidence": 0.56,
        "confidence_gap": 0.04,
        "needs_confirmation": True,
        "uncertainty_reasons": ["low_confidence", "ambiguous_pass_shot"],
        "stage1_action_label": "kick",
        "stage1_confidence": 0.64,
        "recommended_template": "short_pass",
        "raw_action_candidates": [
            {"action": "pass", "score": 0.56, "sources": ["stage2.pass"]},
            {"action": "shot", "score": 0.52, "sources": ["stage2.shot"]},
        ],
        "candidate_scores": {"pass": 0.56, "shot": 0.52},
        "sequence_context": {},
        "analyzer_used": "video_analysis_router_v1",
    }

    route = video_analysis_router_v1(
        decision,
        rules=load_football_rules(),
        run_data={"samples": [], "fps": 30.0, "frame_count": 0},
        metrics={},
        evidence={},
    )

    assert route["needs_confirmation"] is True
    assert route["action_label"] == "uncertain"
    assert route["action_display_name"] == "动作待确认"
    assert route["detected_action"] == "uncertain"
    assert route["recommended_template"] in {"short_pass", "shot_instep"}
    assert route["fallback_used"] is True
