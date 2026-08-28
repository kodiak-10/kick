#!/usr/bin/env python3
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL_VERSION = "improve_v1"


def _now():
    return datetime.now(timezone.utc).isoformat()


def clean_keypoints(in_path: Path, out_path: Path, threshold=0.6, max_gap_frames=5, window=5, log_path=None):
    data = json.loads(in_path.read_text())
    keypoint_names = data.get("keypoint_names", [])
    frames = data.get("frames", [])
    k = len(keypoint_names)
    if k == 0:
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            Path(log_path).write_text(json.dumps({"error": "keypoint_names missing or empty"}))
        raise SystemExit("keypoint_names missing or empty")
    if data.get("fps") is None:
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            Path(log_path).write_text(json.dumps({"error": "fps missing"}))
        raise SystemExit("fps missing")

    # compute mean_confidence if missing
    for fr in frames:
        if "mean_confidence" not in fr or fr["mean_confidence"] is None:
            confs = fr["keypoints"][2::3]
            fr["mean_confidence"] = float(sum(confs) / len(confs)) if confs else 0.0

    # mark valid frames
    valid = []
    for idx, fr in enumerate(frames):
        if fr["mean_confidence"] >= threshold:
            valid.append((idx, fr))

    out_frames = []
    gaps_interpolated = 0
    for i, (idx, fr) in enumerate(valid):
        out_frames.append({
            "timestamp_ms": fr["timestamp_ms"],
            "keypoints": fr["keypoints"],
            "mean_confidence": fr["mean_confidence"],
            "original_index": idx,
        })
        if i == len(valid) - 1:
            break
        next_idx, next_fr = valid[i + 1]
        gap = next_idx - idx - 1
        if gap <= 0:
            continue
        if gap <= max_gap_frames:
            # interpolate each missing frame
            prev_kp = np.array(fr["keypoints"], dtype=float)
            next_kp = np.array(next_fr["keypoints"], dtype=float)
            for g in range(1, gap + 1):
                alpha = g / (gap + 1)
                interp = prev_kp * (1 - alpha) + next_kp * alpha
                ts = frames[idx + g]["timestamp_ms"]
                out_frames.append({
                    "timestamp_ms": ts,
                    "keypoints": interp.tolist(),
                    "mean_confidence": float(np.mean(interp[2::3])),
                    "original_index": None,
                    "interpolated": True,
                })
                gaps_interpolated += 1
        else:
            # represent long gap with a null placeholder
            ts = frames[idx + 1]["timestamp_ms"]
            out_frames.append({
                "timestamp_ms": ts,
                "keypoints": None,
                "mean_confidence": None,
                "original_index": None,
                "note": "gap_longer_than_max",
            })

    # median filter on non-null frames
    if window > 1:
        arr = []
        for fr in out_frames:
            if fr["keypoints"] is None:
                arr.append([math.nan] * (k * 3))
            else:
                arr.append(fr["keypoints"])
        arr = np.array(arr, dtype=float).reshape(len(out_frames), k, 3)
        half = window // 2
        filtered = arr.copy()
        for i in range(len(out_frames)):
            s = max(0, i - half)
            e = min(len(out_frames), i + half + 1)
            filtered[i] = np.nanmedian(arr[s:e], axis=0)
        for i, fr in enumerate(out_frames):
            if fr["keypoints"] is not None:
                fr["keypoints"] = filtered[i].reshape(-1).tolist()

    # validate
    for fr in out_frames:
        if fr["keypoints"] is None:
            continue
        if len(fr["keypoints"]) != k * 3:
            raise SystemExit("keypoints length mismatch")
        if np.isnan(np.array(fr["keypoints"], dtype=float)).any():
            raise SystemExit("NaN in keypoints")

    payload = {
        "clip_id": data.get("clip_id", out_path.stem.replace("_2d_cleaned", "")),
        "fps": data.get("fps", 30),
        "keypoint_names": keypoint_names,
        "frames": out_frames,
        "original_frame_indices": [fr.get("original_index") for fr in out_frames],
        "metadata": {
            "model_version": MODEL_VERSION,
            "generated_at": _now(),
            "frame_count": len(out_frames),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload))

    summary = {
        "frames_in": len(frames),
        "frames_out": len(out_frames),
        "gaps_interpolated": gaps_interpolated,
    }
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text(json.dumps(summary))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--max_gap_frames", type=int, default=5)
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--clip", default=None)
    args = ap.parse_args()

    clip = args.clip or Path(args.inp).stem.replace("_2d", "")
    log_path = Path("logs") / f"clean_keypoints_{clip}.json"
    clean_keypoints(Path(args.inp), Path(args.out), args.threshold, args.max_gap_frames, args.window, log_path)


if __name__ == "__main__":
    main()
