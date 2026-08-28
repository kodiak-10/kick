#!/usr/bin/env python3
"""Convert videos to frame-level 2D keypoints + summary CSV.

Outputs:
  - dst/keypoints/<video>.json (COCO-like keypoints per frame)
  - dst/<video>_summary.csv (frame,timestamp,mean_confidence)
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2


def _safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _iter_videos(src: Path):
    for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv"):
        for f in src.glob(ext):
            yield f


def _mediapipe_pose():
    try:
        import mediapipe as mp
        return mp
    except Exception:
        return None


def _extract_with_mediapipe(video_path: Path, out_json: Path, out_csv: Path):
    mp = _mediapipe_pose()
    if mp is None:
        raise RuntimeError("mediapipe not available; use --use_openpose or install mediapipe")

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    frames = []

    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "timestamp", "mean_confidence"])

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)

            if res.pose_landmarks:
                kps = []
                vis = []
                for lm in res.pose_landmarks.landmark:
                    # COCO-like: x,y,confidence
                    kps.extend([lm.x, lm.y, lm.visibility])
                    vis.append(lm.visibility)
                mean_conf = sum(vis) / len(vis) if vis else 0.0
            else:
                # 33 landmarks * 3 values
                kps = [0.0] * (33 * 3)
                mean_conf = 0.0

            frames.append({"frame": frame_idx, "keypoints": kps})
            writer.writerow([frame_idx, frame_idx / fps, f"{mean_conf:.4f}"])
            frame_idx += 1

    cap.release()

    payload = {
        "video": video_path.name,
        "format": "mediapipe_pose_33",
        "frames": frames,
    }
    out_json.write_text(json.dumps(payload))


def _extract_with_openpose(video_path: Path, out_json: Path, out_csv: Path):
    # Expect OPENPOSE_BIN or OPENPOSE_DOCKER_CMD to be provided by user.
    openpose_bin = os.environ.get("OPENPOSE_BIN")
    openpose_docker = os.environ.get("OPENPOSE_DOCKER_CMD")

    if not openpose_bin and not openpose_docker:
        raise RuntimeError(
            "OpenPose not configured. Set OPENPOSE_BIN or OPENPOSE_DOCKER_CMD environment variable."
        )

    tmp_dir = out_json.parent / f"_tmp_{video_path.stem}"
    _safe_mkdir(tmp_dir)

    if openpose_docker:
        cmd = openpose_docker.format(video=str(video_path), out=str(tmp_dir))
        cmd = cmd.split()
    else:
        cmd = [
            openpose_bin,
            "--video",
            str(video_path),
            "--write_json",
            str(tmp_dir),
            "--display",
            "0",
            "--render_pose",
            "0",
        ]

    subprocess.run(cmd, check=True)

    # Parse OpenPose JSONs
    frames = []
    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "timestamp", "mean_confidence"])

        json_files = sorted(tmp_dir.glob("*.json"))
        for i, jf in enumerate(json_files):
            data = json.loads(jf.read_text())
            if data.get("people"):
                kps = data["people"][0].get("pose_keypoints_2d", [])
                confs = kps[2::3] if kps else []
                mean_conf = sum(confs) / len(confs) if confs else 0.0
            else:
                kps = [0.0] * (25 * 3)
                mean_conf = 0.0

            frames.append({"frame": i, "keypoints": kps})
            writer.writerow([i, i, f"{mean_conf:.4f}"])

    payload = {
        "video": video_path.name,
        "format": "openpose_25",
        "frames": frames,
    }
    out_json.write_text(json.dumps(payload))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="video folder")
    ap.add_argument("--dst", required=True, help="output folder")
    ap.add_argument("--use_mediapipe", action="store_true")
    ap.add_argument("--use_openpose", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    if not src.exists():
        raise SystemExit(f"src not found: {src}")

    _safe_mkdir(dst)
    kp_dir = dst / "keypoints"
    _safe_mkdir(kp_dir)
    had_failure = False

    if not args.use_mediapipe and not args.use_openpose:
        # Prefer mediapipe if available
        args.use_mediapipe = _mediapipe_pose() is not None
        args.use_openpose = not args.use_mediapipe

    for video in _iter_videos(src):
        out_json = kp_dir / f"{video.stem}.json"
        out_csv = dst / f"{video.stem}_summary.csv"
        try:
            if args.use_mediapipe:
                _extract_with_mediapipe(video, out_json, out_csv)
            else:
                _extract_with_openpose(video, out_json, out_csv)
            print(f"Processed: {video.name}")
        except Exception as e:
            had_failure = True
            print(f"Failed: {video.name}: {e}", file=sys.stderr)

    if had_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
