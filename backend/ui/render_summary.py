from pathlib import Path
from frontend.summary_card import render_summary_card


def render_summary(cleaned_keypoints: Path, pose3d_smoothed: Path, action, explanation, out_video: Path, preview=False):
    # Minimal placeholder: render a single-frame summary card to video
    render_summary_card(cleaned_keypoints, pose3d_smoothed, action, explanation, out_video, preview=preview)
