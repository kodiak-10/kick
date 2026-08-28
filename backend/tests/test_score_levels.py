import pytest

from analysis.score_levels import score_level_from_overall


@pytest.mark.parametrize(
    "score,expected_code,expected_label",
    [
        (100.0, "excellent", "优秀"),
        (90.0, "excellent", "优秀"),
        (89.9, "good", "良好"),
        (75.0, "good", "良好"),
        (74.9, "fair", "一般"),
        (60.0, "fair", "一般"),
        (59.9, "needs_improve", "待提高"),
        (40.0, "needs_improve", "待提高"),
        (39.9, "needs_strengthen", "需加强"),
        (0.0, "needs_strengthen", "需加强"),
    ],
)
def test_score_level_mapping(score, expected_code, expected_label):
    assert score_level_from_overall(score) == (expected_code, expected_label)
