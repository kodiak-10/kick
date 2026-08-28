# Repo Structure (Modular Refactor)

## High-Level Flow
`coach.py` orchestrates the pipeline:
1. `vision.detect_pose.detect_pose()`
2. `vision.clean_keypoints.clean_keypoints()`
3. `biomechanics.lift2dto3d.lift2dto3d()`
4. `tools.smooth_pose3d.smooth_pose3d()`
5. `analysis.classify_action.classify_action()`
6. `analysis.explain.explain()`
7. `ui.render_summary.render_summary()`

Each stage writes metadata with `{model_version, generated_at, frame_count}` and logs are stored in `logs/`.

## Modules and Interfaces

### `vision/`
- `detect_pose(video_path: Path, out_json: Path) -> Path`
  - Output: COCO-like 2D keypoints JSON
  - Example: `keypoints/{clip_id}_2d.json`
- `clean_keypoints(in_path: Path, out_path: Path, threshold=0.6, max_gap_frames=5, window=5, log_path=None) -> dict`
  - Returns summary `{frames_in, frames_out, gaps_interpolated}`
  - Output: `keypoints/cleaned/{clip_id}_2d_cleaned.json`

### `biomechanics/`
- `lift2dto3d(cleaned_keypoints: Path, out_path: Path) -> Path`
  - Output: `pose3d/{clip_id}_3d.npz` with `poses (T,K,3)` in meters

### `tools/`
- `smooth_pose3d(in_path: Path, out_path: Path, cutoff=5.0, upsample_fps=None, original_fps=30) -> dict`
  - Output: `pose3d/{clip_id}_3d_smoothed.npz`
  - Diagnostics: `diagnostics/rmse_{clip_id}.json`
  - Plot: `reports/original_vs_smoothed_{clip_id}.png`

### `analysis/`
- `classify_action(pose3d_path: Path) -> dict`
  - Example return: `{label: "squat", confidence: 0.9}`
- `explain(pose3d_path: Path, action: dict) -> dict`
  - Example return: `{severity: 0.3, suggestion: "ex_001 3x12"}`

### `ui/`
- `render_summary(cleaned_keypoints: Path, pose3d_smoothed: Path, action: dict, explanation: dict, out_video: Path) -> None`
  - Uses `frontend/summary_card.py` for the Summary Card overlay

### `frontend/`
- `summary_card.py` renders the Summary Card overlay and can create a demo video.
- `mock_render.sh` is a simple CLI wrapper for producing `reports/demo_with_summary_{clip_id}.mp4`.

### `reports/`
- `generate_report(...)` (placeholder)
  - Reserved for PDF or narrative reporting

## Orchestrator
- `coach.py` (≤80 lines, orchestrator only)
  - CLI: `python coach.py --clip_id <id> --repo_path <path>`
  - Outputs: `logs/pipeline_improve_<clip_id>.json`

## Files & Outputs
- `keypoints/cleaned/{clip_id}_2d_cleaned.json`
- `pose3d/{clip_id}_3d_smoothed.npz`
- `reports/original_vs_smoothed_{clip_id}.png`
- `reports/demo_with_summary_{clip_id}.mp4`
- `logs/pipeline_improve_{clip_id}.json`
