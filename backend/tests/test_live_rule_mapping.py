from rules_loader import load_football_rules
from vision.live_mode import _resolve_live_rule_key


def test_live_rule_mapping_prefers_detected_action_aliases():
    rules = load_football_rules()
    cases = [
        ("pass_like", "passing_stability", "short_pass"),
        ("shoot_like", "shooting_quality", "shot_instep"),
        ("shot_like", "shooting_quality", "shot_instep"),
        ("first_touch_like", "first_touch_control", "receive_control"),
        ("dribble_like", "passing_stability", "dribble_change_direction"),
        ("juggle_like", "passing_stability", "juggling"),
    ]

    for detected_action, template_code, expected_rule_key in cases:
        mapped_rule_key, source_action = _resolve_live_rule_key(detected_action, template_code, rules)
        assert mapped_rule_key == expected_rule_key
        assert source_action == detected_action
