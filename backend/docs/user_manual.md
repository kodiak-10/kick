# AI Coach User Manual

## 1. Product Summary

AI Coach is a computer-vision sports analysis system focused on football technique screening, live movement feedback, and offline review. It uses a camera to estimate body pose, track the ball, analyze movement quality, and present bilingual coaching feedback.

## 2. Main Capabilities

### 2.1 Live Mode

- real-time pose estimation
- primary target lock
- football phase recognition
- ball tracking and contact-side estimation
- football action-quality scoring with goal-specific templates
- bilingual user interface
- developer mode for raw diagnostics

### 2.2 Calibration Mode

- capture a stable full-body standing profile
- estimate pixel-to-meter scale
- support personalized stance and distance metrics

### 2.3 Offline Mode

- clean 2D keypoints
- smooth 3D pose
- generate demo overlays and logs

### 2.4 Collection Mode

- capture local labeled clips for future dataset building

## 3. System Requirements

- Python 3.10
- macOS with camera permission granted to Terminal or VS Code
- webcam or external camera
- recommended: Apple Silicon or modern laptop CPU/GPU

## 4. Installation

From the project root:

```bash
python -m pip install -r requirements.txt
```

## 5. Camera Permission

On macOS:

1. Open `System Settings`
2. Go to `Privacy & Security`
3. Open `Camera`
4. Enable access for the application you use to run the project:
   - `Terminal`
   - `Visual Studio Code`

If the camera was previously denied, reset permission:

```bash
tccutil reset Camera com.microsoft.VSCode
tccutil reset Camera com.apple.Terminal
```

Then fully restart the app and try again.

## 6. Recommended Shooting Setup

For better tracking and higher FPS:

- keep only one athlete in the main view
- keep the full body visible
- avoid very dark scenes
- keep the ball near the lower half of the frame
- avoid busy circular objects near the feet
- use landscape orientation
- keep the camera stable

## 7. Quick Start

### 7.1 Check Available Cameras

```bash
python coach.py --mode camera_check --max_index 6
```

### 7.2 Create Calibration Profile

Example for a 1.75m user:

```bash
python coach.py --mode calibrate --camera_index 0 --user_height_m 1.75 --calibration_path calibration/user_profile.json
```

During calibration:

- stand upright
- keep the full body in frame
- hold still for a short moment
- the system will capture stable samples automatically

### 7.3 Start Live Football Mode

```bash
python coach.py --mode live --camera_index 0 --sport_mode soccer_basic --calibration_path calibration/user_profile.json
```

If camera `0` is black or unavailable, try `1` or `2`.

### 7.3.1 Live Start Workflow

The product now uses a preparation-and-confirmation workflow before formal analysis starts.

Step-by-step:

1. open live mode
2. enter the home screen
3. press `1` for passing stability, `2` for shooting quality, or `3` for first-touch control
4. press `SPACE` to continue into setup
5. make sure only the main athlete is in the center of the frame
6. ensure full body is visible
7. wait for primary target lock
8. press `SPACE` again to start the formal session

Before `SPACE` is pressed:

- the product is in home or preparation mode
- it helps the user position the athlete correctly
- it does not start full football analysis yet

After `SPACE` is pressed:

- the product enters active analysis mode
- ball tracking, football phase analysis, and scoring become active

When `r` is pressed after an active session:

- the session is reset
- a short session review page is shown
- the session summary is also saved to `reports/sessions/`
- the product then returns to preparation mode for the next athlete or next repetition

### 7.4 Run Offline Demo

```bash
python coach.py --mode offline --clip_id sample01 --repo_path .
```

## 8. Keyboard Controls

Live mode hotkeys:

- `q`: quit
- `d`: toggle developer mode
- `space`: confirm subject and start session
- `1`: select passing stability
- `2`: select shooting quality
- `3`: select first-touch control
- `r`: reset current session and show a short review page
- `h`: return to home screen
- `c`: switch to next camera
- `0-5`: switch directly to a camera index

## 9. How To Read The Interface

### Left Panel

- `Action / 动作`: current detected football action style
- `Action Quality Score / 动作质量总分`: the main score for the selected football training template
- `Level / 等级`: excellent, good, fair, or needs correction
- `Summary / 一句话总结`: what this score means for the current action
- `Core Problem / 核心问题`: the main technique limitation
- `Next Cue / 下一步建议`: the next correction cue
- `Positive Feedback / 正向反馈`: what is already going well
- `Top Issues / 当前重点问题`: the 1-3 most important issues in training language

### Right Panel

- `Technical Execution / 技术执行分`
- `Control Stability / 控制稳定分`
- `Action Safety / 动作安全性分`

In football mode, the product score is now intentionally split:

1. `Action Quality Score`
   - the main performance score
   - evaluates how well the current football action is completed for the selected template
2. `Technical Execution`
   - reflects whether the action mechanics are executed cleanly
3. `Control Stability`
   - reflects balance, body organization, and repeatability
4. `Action Safety`
   - reflects whether the action stays within a safer movement pattern

The current product uses these fixed score weights:

- `Technical Execution`: 50%
- `Control Stability`: 30%
- `Action Safety`: 20%

Available football templates:

1. `Passing Stability / 传球稳定性`
2. `Shooting Quality / 射门动作质量`
3. `First-Touch Control / 停球控制`

### Bottom Panel

- severity timeline over recent frames

### Preparation Screen

Before the session starts, the system shows a centered preparation card:

- full-body readiness
- target-lock progress
- operator instructions
- start confirmation prompt

### Session Review Screen

After a session reset, the system briefly shows:

- primary action summary
- main issue summary
- average action-quality score
- average technical/control/safety scores
- peak risk

## 10. Performance Guide

The current build already includes several FPS optimizations:

- reduced pose model complexity
- reduced capture resolution target
- reduced pose inference resolution
- lower-frequency ball detection with predictive tracking between detections
- single-pass text rendering instead of repeated full-frame text conversion

To improve FPS further:

1. close other heavy applications
2. use a simpler background
3. keep one subject only
4. use a camera index with stable native output
5. keep lighting strong and even
6. avoid running in a high-resolution mirrored display setup

## 11. Troubleshooting

### 11.1 Black Camera Screen

- check `camera_check`
- switch camera using `c`
- try `0`, `1`, `2`
- verify macOS permission

### 11.2 Ball Tracking Is Wrong

- ensure the ball is visible near the lower body
- reduce other circular bright objects in frame
- avoid motion blur where possible
- keep the camera stable

### 11.3 Interface Changes Too Quickly

The system now includes display smoothing and event hold logic. If it still changes too quickly, improve camera framing and lighting so the model confidence becomes more stable.

### 11.4 FPS Is Still Low

Possible reasons:

- camera output too large
- low light causing noisy frames
- multiple monitors or screen mirroring overhead
- background software consuming CPU/GPU

## 12. Output Files

Common outputs:

- `logs/pipeline_improve_<clip_id>.json`
- `reports/demo_with_summary_<clip_id>.mp4`
- `reports/original_vs_smoothed_<clip_id>.png`
- `calibration/user_profile.json`

## 13. Limitations

- current system is coach-grade, not clinical diagnosis
- single-camera vision cannot fully recover true 3D biomechanics
- high-speed ball tracking is improved but still not equivalent to a dedicated sports tracking model

## 14. Recommended Next Upgrade Path

If you want a more advanced product:

1. dedicated football detector for the ball
2. event replay freeze card after kick/contact
3. multi-view camera support
4. stronger action classifier trained on football data
5. exportable PDF session report
