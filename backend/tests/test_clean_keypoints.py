import json
from pathlib import Path

from vision.clean_keypoints import clean_keypoints


def test_clean_keypoints(tmp_path):
    sample = Path(__file__).parent / "samples" / "keypoints_sample.json"
    out = tmp_path / "cleaned.json"

    summary = clean_keypoints(sample, out, threshold=0.6, max_gap_frames=5, window=5)
    data = json.loads(out.read_text())

    assert out.exists()
    assert summary["frames_out"] < summary["frames_in"]
    assert summary["gaps_interpolated"] > 0
    assert "original_frame_indices" in data
