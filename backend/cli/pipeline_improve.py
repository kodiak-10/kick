#!/usr/bin/env python3
"""Improved pipeline: preprocessing -> smooth pose3d -> report."""

import argparse
import json
import time
from pathlib import Path
import sys

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.preprocessing import preprocess
from tools.smooth_pose3d import smooth_pose
from reports.generate_explain_report import generate_report


def run(clip_id: str, repo_path: str, quick: bool = False):
    repo = Path(repo_path)
    logs_dir = repo / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"pipeline_{clip_id}.json"

    t0 = time.time()
    log = {"clip_id": clip_id, "status": "running", "steps": []}

    try:
        keypoints_in = repo / "keypoints" / f"{clip_id}_2d.json"
        cleaned_out = repo / "keypoints" / "cleaned" / f"{clip_id}_2d_cleaned.json"
        summary_a = preprocess(keypoints_in, cleaned_out, threshold=0.6, window=5, max_gap_frames=5)
        log["steps"].append({"stage": "preprocessing", **summary_a})

        pose_in = repo / "pose3d" / f"{clip_id}_3d.npz"
        pose_out = repo / "pose3d" / f"{clip_id}_3d_smoothed.npz"
        summary_b = smooth_pose(pose_in, pose_out, cutoff_hz=5.0, upsample_fps=None, original_fps=30)
        log["steps"].append({"stage": "smooth_pose3d", **summary_b})

        report = generate_report(clip_id, repo_path, str(cleaned_out), str(pose_out), None)
        log["steps"].append({"stage": "report", **report})

        log["status"] = "success"
        log["elapsed_ms"] = int((time.time() - t0) * 1000)
        log_path.write_text(json.dumps(log))
        return log

    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
        log["elapsed_ms"] = int((time.time() - t0) * 1000)
        log_path.write_text(json.dumps(log))
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip_id", required=True)
    ap.add_argument("--repo_path", required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    out = run(args.clip_id, args.repo_path, quick=args.quick)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
