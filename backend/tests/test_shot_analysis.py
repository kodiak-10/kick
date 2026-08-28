import json
from pathlib import Path

from coach import analyze_shot
from analysis.shot_analysis import _video_summary


def test_shot_analysis_returns_structured_json(tmp_path):
    video_path = Path(__file__).parent / "samples" / "sample_short.mp4"
    out_path = tmp_path / "shot_analysis.json"

    result = analyze_shot(video_path, output_path=out_path)

    assert result["action_type"] == "shooting"
    assert "score" in result and isinstance(result["score"], dict)
    assert "summary" in result and isinstance(result["summary"], str)
    assert "issues" in result and isinstance(result["issues"], list)
    assert 0.0 <= float(result["analysis_confidence"]) <= 1.0
    assert result["status"] in {"ok", "provisional", "error"}
    assert out_path.exists()

    payload = json.loads(out_path.read_text())
    assert payload["action_type"] == "shooting"
    if payload["issues"]:
        issue = payload["issues"][0]
        for key in (
            "id",
            "title",
            "phase",
            "time",
            "short_hint",
            "explanation",
            "fix_advice",
            "training_advice",
        ):
            assert key in issue


def test_video_summary_rewrites_generic_low_score_summary():
    summary = _video_summary(
        "传球",
        {"overall": 37.0},
        [
            {
                "id": "stable_action",
                "title": "动作整体稳定",
                "phase": "follow_through",
                "time": 0.0,
            }
        ],
        {"analysis_confidence": 0.32},
        fallback_used=False,
    )

    assert "当前动作" not in summary
    assert "最值得继续保持的是当前动作" not in summary
    assert "37/100" in summary
    assert "主要问题" in summary
    assert "动作完成度" in summary
