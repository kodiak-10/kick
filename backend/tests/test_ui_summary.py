import subprocess
from pathlib import Path

from vision.clean_keypoints import clean_keypoints
from tools.smooth_pose3d import smooth_pose3d


def test_ui_summary(tmp_path):
    sample_kp = Path(__file__).parent / "samples" / "keypoints_sample.json"
    cleaned = tmp_path / "cleaned.json"
    clean_keypoints(sample_kp, cleaned, threshold=0.6, max_gap_frames=5, window=5)

    sample_pose = Path(__file__).parent / "samples" / "pose3d_sample.npz"
    pose_in = tmp_path / "sample01_3d.npz"
    pose_in.write_bytes(sample_pose.read_bytes())
    pose_out = tmp_path / "sample01_3d_smoothed.npz"
    smooth_pose3d(pose_in, pose_out, cutoff=5.0, original_fps=30)

    out_video = tmp_path / "demo_with_summary_sample01.mp4"
    cmd = [
        "bash",
        "frontend/mock_render.sh",
        "--clip",
        "sample01",
        "--keypoints",
        str(cleaned),
        "--pose",
        str(pose_out),
        "--out",
        str(out_video),
        "--min_frames",
        "60",
    ]
    subprocess.run(cmd, check=True)

    assert out_video.exists()
    assert out_video.stat().st_size > 50 * 1024
