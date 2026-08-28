from types import SimpleNamespace

from analysis.temporal_classifier import fresh_temporal_classifier_state, update_temporal_classifier


def _snap(phase, conf=0.85, active=True, label="pass_like"):
    return SimpleNamespace(
        phase=phase,
        phase_confidence=conf,
        phase_locked=True,
        sequence_active=active,
        sequence_ready=active,
        action_label=label,
    )


def _kin(contact, ball_speed, swing_speed, support_speed=0.015, support_ball=0.24, swing_ball=0.10):
    return SimpleNamespace(
        contact=contact,
        ball_speed_ratio=ball_speed,
        swing_speed_ratio=swing_speed,
        support_speed_ratio=support_speed,
        support_ball_ratio=support_ball,
        swing_ball_ratio=swing_ball,
    )


def test_temporal_classifier_prefers_pass_for_moderate_release():
    state = fresh_temporal_classifier_state()
    now = 0.0
    for idx in range(8):
        pred = update_temporal_classifier(
            state,
            _snap("support" if idx < 3 else "contact", conf=0.82, label="pass_like"),
            _kin(contact=idx >= 3, ball_speed=0.10, swing_speed=0.07),
            now + idx * 0.03,
        )
    assert pred.label == "pass_like"
    assert pred.confidence > 0.45


def test_temporal_classifier_prefers_shoot_for_fast_release():
    state = fresh_temporal_classifier_state()
    now = 0.0
    for idx in range(8):
        pred = update_temporal_classifier(
            state,
            _snap("support" if idx < 3 else "contact", conf=0.88, label="shoot_like"),
            _kin(contact=idx >= 3, ball_speed=0.28, swing_speed=0.15, support_ball=0.20),
            now + idx * 0.03,
        )
    assert pred.label == "shoot_like"
    assert pred.confidence > 0.50
