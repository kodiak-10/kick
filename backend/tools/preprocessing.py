#!/usr/bin/env python3
"""Preprocess keypoints: threshold, median filter, interpolate short gaps."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL_VERSION = "improve_v1"


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _median_filter(data, window):
    # data: (T, K, 3)
    if window <= 1:
        return data
    half = window // 2
    out = data.copy()
    t, k, c = data.shape
    for i in range(t):
        s = max(0, i - half)
        e = min(t, i + half + 1)
        out[i] = np.nanmedian(data[s:e], axis=0)
    return out


def _interpolate_gaps(frames, max_gap):
    # frames: list of dict, some with keypoints=None
    # returns filled frames and gaps_interpolated count
    t = len(frames)
    gaps_interpolated = 0
    i = 0
    while i < t:
        if frames[i]["keypoints"] is not None:
            i += 1
            continue
        start = i
        while i < t and frames[i]["keypoints"] is None:
            i += 1
        end = i - 1
        gap_len = end - start + 1
        if gap_len <= max_gap and start > 0 and i < t:
            # linear interpolate between frames[start-1] and frames[i]
            prev = np.array(frames[start - 1]["keypoints"], dtype=float)
            nxt = np.array(frames[i]["keypoints"], dtype=float)
            for j in range(gap_len):
                alpha = (j + 1) / (gap_len + 1)
                interp = prev * (1 - alpha) + nxt * alpha
                frames[start + j]["keypoints"] = interp.tolist()
                frames[start + j]["interpolated"] = True
            gaps_interpolated += gap_len
        else:
            for j in range(start, end + 1):
                frames[j]["interpolated"] = False
    return frames, gaps_interpolated


def preprocess(in_path: Path, out_path: Path, threshold=0.6, window=5, max_gap_frames=5):
    t0 = time.time()
    data = json.loads(in_path.read_text())

    keypoint_names = data["keypoint_names"]
    k = len(keypoint_names)
    frames = data["frames"]

    # recompute mean_confidence
    for fr in frames:
        kp = fr["keypoints"]
        confs = kp[2::3]
        fr["mean_confidence"] = float(sum(confs) / len(confs)) if confs else 0.0

    # mark keep/drop
    kept = []
    for idx, fr in enumerate(frames):
        if fr["mean_confidence"] >= threshold:
            kept.append({
                "timestamp_ms": fr["timestamp_ms"],
                "keypoints": fr["keypoints"],
                "mean_confidence": fr["mean_confidence"],
                "original_frame_index": idx,
                "interpolated": False,
            })
        else:
            kept.append({
                "timestamp_ms": fr["timestamp_ms"],
                "keypoints": None,
                "mean_confidence": fr["mean_confidence"],
                "original_frame_index": idx,
                "interpolated": False,
            })

    # median filter on existing keypoints
    arr = []
    for fr in kept:
        if fr["keypoints"] is None:
            arr.append([np.nan] * (k * 3))
        else:
            arr.append(fr["keypoints"])
    arr = np.array(arr, dtype=float).reshape(len(kept), k, 3)
    arr_filtered = _median_filter(arr, window)

    # write filtered back
    for i, fr in enumerate(kept):
        if fr["keypoints"] is not None:
            fr["keypoints"] = arr_filtered[i].reshape(-1).tolist()

    # interpolate short gaps
    kept, gaps_interpolated = _interpolate_gaps(kept, max_gap_frames)

    # validate keypoint count and NaN
    for fr in kept:
        if fr["keypoints"] is None:
            continue
        if len(fr["keypoints"]) != k * 3:
            raise ValueError("keypoints length mismatch")
        if np.isnan(np.array(fr["keypoints"], dtype=float)).any():
            raise ValueError("NaN found in keypoints")

    out = {
        "clip_id": data["clip_id"],
        "fps": data["fps"],
        "keypoint_names": keypoint_names,
        "frames": kept,
        "detector": data.get("detector", "unknown"),
        "model_version": MODEL_VERSION,
        "generated_at": _now_iso(),
        "frame_count": len(kept),
        "original_frame_indices": [fr["original_frame_index"] for fr in kept],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out))

    summary = {
        "frames_in": len(frames),
        "frames_out": len(kept),
        "gaps_interpolated": gaps_interpolated,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--max_gap_frames", type=int, default=5)
    args = ap.parse_args()

    summary = preprocess(Path(args.inp), Path(args.out), args.threshold, args.window, args.max_gap_frames)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
