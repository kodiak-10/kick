import numpy as np
from pathlib import Path

from tools.smooth_pose3d import smooth_pose


def test_smoothing(tmp_path):
    # synthetic noisy pose
    T, K = 30, 5
    poses = np.zeros((T, K, 3), dtype=np.float32)
    noise = np.random.randn(T, K, 3).astype(np.float32) * 0.1
    poses_noisy = poses + noise
    in_path = tmp_path / "pose3d_sample.npz"
    np.savez(in_path, poses=poses_noisy)

    out_path = tmp_path / "pose3d_smoothed.npz"
    summary = smooth_pose(in_path, out_path, cutoff_hz=5.0, upsample_fps=None, original_fps=30)

    out = np.load(out_path)
    smoothed = out["poses"]
    assert smoothed.shape == poses_noisy.shape
    assert not np.isnan(smoothed).any()
    assert summary["rmse_mean"] >= 0.0
