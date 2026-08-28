#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, savgol_filter
from scipy.interpolate import CubicSpline

_MPL_CACHE = (Path(__file__).resolve().parent.parent / ".cache" / "matplotlib")
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODEL_VERSION = "improve_v1"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _clip_id_from_path(path: Path):
    stem = path.stem
    for suffix in ("_3d_smoothed", "_3d"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _smooth_1d(series: np.ndarray, cutoff: float, original_fps: float) -> np.ndarray:
    series = np.asarray(series, dtype=np.float32)
    n = int(series.shape[0])
    if n < 5:
        return series.copy()

    window = int(round(max(5.0, original_fps / max(1e-6, cutoff))))
    if window % 2 == 0:
        window += 1
    window = min(window, n if n % 2 == 1 else n - 1)
    if window < 5:
        return series.copy()

    polyorder = 2 if window >= 5 else 1
    try:
        return savgol_filter(series, window_length=window, polyorder=polyorder, mode="interp").astype(np.float32)
    except Exception:
        nyq = 0.5 * original_fps
        norm = min(0.99, cutoff / nyq)
        b, a = butter(2, norm, btype="low")
        return filtfilt(b, a, series).astype(np.float32)


def smooth_pose3d(in_path: Path, out_path: Path, cutoff=5.0, upsample_fps=None, original_fps=30):
    data = np.load(in_path, allow_pickle=True)
    poses = data["poses"].astype(np.float32)
    t, k, c = poses.shape

    frame_offset = poses.mean(axis=(1, 2))
    smooth_offset = _smooth_1d(frame_offset, cutoff=cutoff, original_fps=original_fps)
    smoothed = poses - frame_offset[:, None, None] + smooth_offset[:, None, None]

    rmse = np.sqrt(np.mean((smoothed - poses) ** 2, axis=(0, 2)))

    if upsample_fps and upsample_fps > original_fps:
        new_t = int(round(t * upsample_fps / original_fps))
        x_old = np.linspace(0, 1, t)
        x_new = np.linspace(0, 1, new_t)
        up = np.zeros((new_t, k, c), dtype=np.float32)
        for j in range(k):
            for cc in range(c):
                up[:, j, cc] = CubicSpline(x_old, smoothed[:, j, cc])(x_new)
        smoothed = up
        t = new_t

    if np.isnan(smoothed).any():
        raise SystemExit("NaN in smoothed poses")

    meta = {
        "model_version": MODEL_VERSION,
        "generated_at": _now(),
        "frame_count": t,
        "original_fps": original_fps,
        "cutoff_hz": cutoff,
        "upsample_fps": upsample_fps,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, poses=smoothed, meta=meta)

    # diagnostics
    clip_id = _clip_id_from_path(in_path)
    diag = {"rmse_per_joint": rmse.tolist(), "model_version": MODEL_VERSION, "generated_at": _now(), "frame_count": t}
    diag_path = Path("diagnostics") / f"rmse_{clip_id}.json"
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    diag_path.write_text(json.dumps(diag))

    # plot
    if k >= 14:
        joints = [9, 11, 13]
    else:
        joints = [0, min(1, k - 1), min(2, k - 1)]
    plt.figure(figsize=(8, 3))
    for j in joints:
        plt.plot(poses[:, j, 0], alpha=0.5, label=f"J{j}_orig")
        plt.plot(smoothed[:poses.shape[0], j, 0], alpha=0.8, label=f"J{j}_smooth")
    plt.legend(fontsize=6)
    plot_path = Path("reports") / f"original_vs_smoothed_{clip_id}.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    return {"frames_in": poses.shape[0], "frames_out": smoothed.shape[0], "rmse_mean": float(np.mean(rmse)), "plot": str(plot_path)}


def smooth_pose(in_path: Path, out_path: Path, cutoff_hz=5.0, upsample_fps=None, original_fps=30):
    return smooth_pose3d(in_path, out_path, cutoff=cutoff_hz, upsample_fps=upsample_fps, original_fps=original_fps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cutoff", type=float, default=5.0)
    ap.add_argument("--upsample_fps", type=float, default=None)
    ap.add_argument("--original_fps", type=float, default=30)
    args = ap.parse_args()

    out = smooth_pose3d(Path(args.inp), Path(args.out), args.cutoff, args.upsample_fps, args.original_fps)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
