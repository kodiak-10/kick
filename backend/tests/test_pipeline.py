import json
from pathlib import Path

import pipeline


def test_pipeline_quick(tmp_path):
    repo = tmp_path
    (repo / "raw").mkdir(parents=True, exist_ok=True)

    # copy sample video
    sample = Path(__file__).parent / "samples" / "sample_clip.mp4"
    (repo / "raw" / "sample_clip.mp4").write_bytes(sample.read_bytes())

    meta = {
        "clip_id": "sample_clip",
        "filename": "sample_clip.mp4",
        "fps": 30,
        "resolution": [96, 96],
        "orientation": "landscape",
    }
    (repo / "raw" / "sample_clip_meta.json").write_text(json.dumps(meta))

    manifest = pipeline.run("sample_clip", str(repo), quick=True)
    assert "stages" in manifest
    assert len(manifest["outputs"]) > 0

    # check log
    log = repo / "logs" / "pipeline_sample_clip.json"
    assert log.exists()
