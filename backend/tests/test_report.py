from pathlib import Path

from reports.generate_explain_report import generate_report


def test_report(tmp_path):
    repo = tmp_path
    (repo / "raw").mkdir(parents=True, exist_ok=True)
    (repo / "explain").mkdir(parents=True, exist_ok=True)
    (repo / "reports" / "plots").mkdir(parents=True, exist_ok=True)

    # copy sample assets
    sample_dir = Path(__file__).parent / "samples"
    kp = sample_dir / "keypoints_sample.json"
    pose = sample_dir / "pose3d_sample_smoothed.npz"

    # fake plot for embedding
    (repo / "reports" / "plots" / "pose3d_sample_smoothed_original_vs_smoothed.png").write_bytes(
        (sample_dir / "plot_sample.png").read_bytes()
    )

    out = generate_report("sample01", str(repo), str(kp), str(pose), None)
    assert Path(out["pdf"]).exists()
    summary_txt = repo / "reports" / "sample01_summary.txt"
    assert summary_txt.exists()
