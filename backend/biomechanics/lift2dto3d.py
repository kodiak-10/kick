import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL_VERSION = "improve_v1"


def lift2dto3d(cleaned_keypoints: Path, out_path: Path):
    """Placeholder 2D->3D lift: z=0, scaled to meters."""
    data = json.loads(Path(cleaned_keypoints).read_text())
    frames = data.get("frames", [])
    k = len(data.get("keypoint_names", []))
    poses = np.zeros((len(frames), k, 3), dtype=np.float32)
    for i, fr in enumerate(frames):
        kp = fr["keypoints"] or [0.0] * (k * 3)
        for j in range(k):
            x, y = kp[j * 3], kp[j * 3 + 1]
            poses[i, j, :] = [x * 0.001, y * 0.001, 0.0]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, poses=poses, meta={
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frame_count": len(frames),
    })
    return out_path
