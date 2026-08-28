from analysis.football_scoring import score_football_action


def test_score_football_action_low_score_summary_is_specific():
    metrics = {
        "balance": 0.5,
        "trunk_lean_deg": 30.0,
        "valgus_ratio": 0.5,
        "symmetry": 20.0,
        "stability": 0.0,
        "support_ball_ratio": 0.0,
        "swing_ball_ratio": 0.0,
        "ball_speed_ratio": 0.0,
        "ball_contact": 0.0,
        "visibility": 0.0,
        "sequence_confidence": 0.0,
        "phase_locked": 0.0,
    }

    result = score_football_action(metrics, action_label="pass_like", template_code="passing_stability")

    assert result.overall_score < 40.0
    assert result.level_code == "needs_strengthen"
    assert result.level_label == "需加强"
    assert "当前动作" not in result.one_line_summary
    assert "当前主要" in result.one_line_summary
