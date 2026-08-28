import json
from pathlib import Path

from tools.preprocessing import preprocess


def test_preprocessing(tmp_path):
    sample = Path(__file__).parent / "samples" / "keypoints_sample.json"
    out = tmp_path / "cleaned.json"

    summary = preprocess(sample, out, threshold=0.6, window=5, max_gap_frames=5)
    data = json.loads(out.read_text())

    assert "original_frame_indices" in data
    assert summary["frames_out"] == summary["frames_in"]
    assert summary["gaps_interpolated"] > 0
    # no NaN
    for fr in data["frames"]:
        if fr["keypoints"] is None:
            continue
        assert len(fr["keypoints"]) == len(data["keypoint_names"]) * 3
