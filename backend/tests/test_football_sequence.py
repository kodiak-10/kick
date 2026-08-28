from analysis.football_sequence import compute_football_kinematics, fresh_sequence_state, update_football_sequence


def _points(left_ankle, right_ankle):
    return {
        "left_shoulder": (100.0, 40.0),
        "right_shoulder": (140.0, 40.0),
        "left_hip": (108.0, 95.0),
        "right_hip": (132.0, 95.0),
        "left_knee": (110.0, 145.0),
        "right_knee": (130.0, 145.0),
        "left_ankle": left_ankle,
        "right_ankle": right_ankle,
    }


def test_sequence_tracks_contact_and_completion():
    state = fresh_sequence_state()
    body_span = 140.0
    now_t = 10.0
    prev_ball = {"x": 126.0, "y": 190.0, "radius": 10.0}

    kin1 = compute_football_kinematics(
        _points((112.0, 190.0), (126.0, 184.0)),
        _points((112.0, 190.0), (120.0, 192.0)),
        {"x": 127.0, "y": 189.0, "radius": 10.0},
        prev_ball,
        {"contact": False, "side": "none"},
        body_span,
        0.030,
    )
    snap1 = update_football_sequence(state, kin1, now_t)
    snap2 = update_football_sequence(state, kin1, now_t + 0.03)
    assert snap2.phase in {"approach", "support"}
    assert snap2.sequence_active

    kin_contact = compute_football_kinematics(
        _points((112.0, 190.0), (126.0, 184.0)),
        _points((112.0, 190.0), (126.0, 184.0)),
        {"x": 126.0, "y": 185.0, "radius": 10.0},
        {"x": 127.0, "y": 189.0, "radius": 10.0},
        {"contact": True, "side": "right"},
        body_span,
        0.028,
    )
    snap3 = update_football_sequence(state, kin_contact, now_t + 0.08)
    assert snap3.phase == "contact"
    assert snap3.events["contact"]

    kin_recovery = compute_football_kinematics(
        _points((112.0, 190.0), (134.0, 176.0)),
        _points((112.0, 190.0), (130.0, 180.0)),
        {"x": 154.0, "y": 180.0, "radius": 10.0},
        {"x": 126.0, "y": 185.0, "radius": 10.0},
        {"contact": False, "side": "none"},
        body_span,
        0.018,
    )
    snap4 = update_football_sequence(state, kin_recovery, now_t + 0.30)
    snap5 = update_football_sequence(state, kin_recovery, now_t + 0.36)

    kin_set = compute_football_kinematics(
        _points((112.0, 190.0), (134.0, 176.0)),
        _points((112.0, 190.0), (134.0, 176.0)),
        {"x": 172.0, "y": 178.0, "radius": 10.0},
        {"x": 154.0, "y": 180.0, "radius": 10.0},
        {"contact": False, "side": "none"},
        body_span,
        0.004,
    )
    snap6 = update_football_sequence(state, kin_set, now_t + 0.60)
    snap7 = update_football_sequence(state, kin_set, now_t + 0.70)
    assert snap5.phase in {"follow_through", "recovery", "set"}
    assert snap7.events["sequence_complete"] or not snap7.sequence_active
