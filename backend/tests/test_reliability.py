from analysis.reliability import evaluate_reliability


def test_reliability_withholds_score_when_ball_is_unstable():
    report = evaluate_reliability(
        visibility=0.92,
        lock_score=0.88,
        full_body=True,
        target_locked=True,
        body_fill_ratio=0.54,
        brightness=86.0,
        switch_risk=0.08,
        ball_confidence=0.08,
        ball_detected=False,
        phase_confidence=0.84,
        phase_locked=True,
        sequence_ready=True,
    )
    assert not report.should_score
    assert report.gate_reason == "ball_unstable"


def test_reliability_allows_score_when_evidence_is_consistent():
    report = evaluate_reliability(
        visibility=0.94,
        lock_score=0.92,
        full_body=True,
        target_locked=True,
        body_fill_ratio=0.58,
        brightness=92.0,
        switch_risk=0.06,
        ball_confidence=0.82,
        ball_detected=True,
        phase_confidence=0.90,
        phase_locked=True,
        sequence_ready=True,
    )
    assert report.should_score
    assert report.gate_reason == "ready"
