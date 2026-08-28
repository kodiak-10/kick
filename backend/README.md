# NeuroMiniGame

Minimal React Native component to run a target-hit game from a single joint keypoint stream.

## Integration
- Provide a `keypointStream` that emits `{x, y, confidence}` normalized to [0,1].
- Provide `apiEndpoint` for score upload (POST JSON).

## TF-Lite bridge (outline)
1. Use `react-native-vision-camera` for frame capture.
2. Run a TF-Lite pose model in native (Android/iOS) and expose a JS bridge.
3. Normalize a target joint to [0,1] and push to `keypointStream`.

## Example mock backend
See `mock_backend/server.js`.


## Pipeline

End-to-end pipeline (video -> 2D -> 3D -> dynamics -> explain -> plan).

Example:
```
python pipeline.py sample_clip --repo_path /Users/tim/coach.py --quick
```

Outputs are written under:
- raw/
- keypoints/
- pose3d/
- dynamics/
- explain/
- plan/
- logs/

Requirements:
- opencv-python, mediapipe (optional), numpy, jsonschema, reportlab


## Pipeline Improve

Example:
```
python cli/pipeline_improve.py --clip_id sample01 --repo_path /Users/tim/coach.py
```

Required inputs:
- raw/{clip_id}.mp4
- keypoints/{clip_id}_2d.json
- pose3d/{clip_id}_3d.npz


## Modular Refactor (Summary Card + Cleaning + Smoothing)

Examples:
```
python vision/clean_keypoints.py --in keypoints/sample01_2d.json --out keypoints/cleaned/sample01_2d_cleaned.json --threshold 0.6
python tools/smooth_pose3d.py --in pose3d/sample01_3d.npz --out pose3d/sample01_3d_smoothed.npz --cutoff 5
bash frontend/mock_render.sh --clip sample01 --keypoints keypoints/cleaned/sample01_2d_cleaned.json --pose pose3d/sample01_3d_smoothed.npz
python coach.py --clip_id sample01 --repo_path .
python coach.py --mode live --camera_index 0
python coach.py --mode live --camera_index 0 --sport_mode soccer_basic
python coach.py --mode calibrate --camera_index 0 --user_height_m 1.75 --calibration_path calibration/user_profile.json
python coach.py --mode live --camera_index 0 --sport_mode soccer_basic --calibration_path calibration/user_profile.json
python coach.py --mode collect --camera_index 0 --collect_dir captured
python coach.py --mode camera_check --max_index 6
```

Dependencies (core):
- numpy, scipy, opencv-python, matplotlib, pytest, reportlab


## Multi-Dataset Index (Human3.6M + Kinetics-700 + SoccerNet)

Build a unified index JSONL after downloading datasets:
```
python datasets/build_index.py \
  --h36m_root /path/to/Human3.6M \
  --kinetics_root /path/to/Kinetics-700 \
  --soccernet_labels datasets/soccernet_labels_template.csv \
  --out data/unified_index.jsonl
```

## Literature-backed soccer heuristics (no-training mode)

Run live soccer screening with biomechanical rule tags:
```
python coach.py --mode live --camera_index 0 --sport_mode soccer_basic
python coach.py --mode calibrate --camera_index 0 --user_height_m 1.75 --calibration_path calibration/user_profile.json
python coach.py --mode live --camera_index 0 --sport_mode soccer_basic --calibration_path calibration/user_profile.json
```

Live hotkeys:
- `q`: quit
- `d`: toggle developer mode
- `space`: confirm subject and start
- `r`: reset current session
- `c`: switch to next camera
- `0-5`: switch directly to camera index

Reference mapping:
- `docs/biomechanics_reference.md`
- `analysis/biomech_rules.py`
- `docs/product_overview.md`
- `docs/user_manual.md`
- `docs/xcode_migration_plan.md`
