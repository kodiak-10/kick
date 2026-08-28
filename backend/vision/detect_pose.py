import json
from datetime import datetime, timezone
from pathlib import Path

MODEL_VERSION = "improve_v1"


def detect_pose(video_path: Path, out_json: Path):
    """Placeholder pose detector: creates empty frames if no detector is available."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    keypoint_names = []
    try:
        import mediapipe as mp
        keypoint_names = [lm.name.lower() for lm in mp.solutions.pose.PoseLandmark]
    except Exception:
        keypoint_names = [
            "nose","left_eye","right_eye","left_shoulder","right_shoulder","left_elbow","right_elbow",
            "left_wrist","right_wrist","left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle",
        ]
    payload = {
        "clip_id": out_json.stem.replace("_2d", ""),
        "fps": 30,
        "keypoint_names": keypoint_names,
        "frames": [],
        "metadata": {
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "frame_count": 0,
        },
    }
    out_json.write_text(json.dumps(payload))
    return out_json
