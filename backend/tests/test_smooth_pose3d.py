from pathlib import Path

import numpy as np

from tools.smooth_pose3d import smooth_pose3d


def test_smooth_pose3d(tmp_path):
    sample = Path(__file__).parent / "samples" / "pose3d_sample.npz"
    clean = np.load(sample)["poses"]
    t = clean.shape[0]
    noise = 0.05 * np.sin(np.linspace(0, 20 * np.pi, t))[:, None, None]
    noisy = clean + noise

    noisy_path = tmp_path / "sample01_3d.npz"
    np.savez_compressed(noisy_path, poses=noisy)
    out_path = tmp_path / "sample01_3d_smoothed.npz"

    summary = smooth_pose3d(noisy_path, out_path, cutoff=5.0, original_fps=30)
    smoothed = np.load(out_path)["poses"]

    rmse_noisy = float(np.sqrt(np.mean((noisy - clean) ** 2)))
    rmse_smoothed = float(np.sqrt(np.mean((smoothed[: clean.shape[0]] - clean) ** 2)))

    assert rmse_smoothed < rmse_noisy
    plot = Path("reports") / "original_vs_smoothed_sample01.png"
    assert plot.exists()
    assert summary["frames_out"] >= summary["frames_in"]
