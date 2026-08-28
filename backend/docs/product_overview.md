# AI Coach Product Overview

## Product Purpose

AI Coach is a computer-vision-based sports technique analysis product for live coaching, offline review, and structured performance reporting. It is designed to turn ordinary camera input into interpretable movement feedback for sports training, with an emphasis on football skill execution, movement quality, and biomechanical risk screening.

## Target Users

- Individual athletes who need real-time technical feedback
- Coaches who need fast visual review and risk cues
- Sports training studios that want low-cost movement analysis
- Researchers and student teams building sports-analytics prototypes

## Core Use Cases

1. Live training feedback
   - Open a laptop or external camera
   - Lock onto the primary athlete
   - Track pose, ball interaction, movement phase, and risk cues in real time

2. Offline clip review
   - Import recorded video
   - Clean 2D keypoints and smooth 3D pose
   - Generate timeline-based visual summaries and report assets

3. Technique screening
   - Detect visible movement deviations such as knee valgus tendency, trunk control deficit, asymmetry, and unstable stance
   - Convert raw metrics into ranked coaching cues

4. Dataset collection
   - Record labeled clips for football actions such as pass, shoot, jump, and cut
   - Build a local training dataset for future supervised models

## Current Functional Modules

### 1. Real-Time Vision Analysis

- Live camera input from laptop or external camera
- Full-body readiness gate before analysis starts
- Primary-target lock to reduce subject switching and multi-person interference
- Ball candidate detection near the lower limbs
- Ball-contact side estimation
- Action-phase inference for football-like motion

### 2. Biomechanics Layer

- Joint-angle estimation from pose landmarks
- Symmetry, balance, trunk lean, depth, and valgus proxy metrics
- Literature-backed rule engine for coaching-grade risk screening
- Optional calibration profile for pixel-to-meter scale estimation

### 3. UI Layer

- Default user mode with bilingual summary card
- Development mode for raw diagnostic output
- Severity timeline
- Football-specific status fields:
  - action
  - phase
  - support leg
  - swing leg
  - technique score
  - control score
  - risk score
  - target lock status

### 4. Offline Pipeline

- Keypoint confidence filtering
- Gap interpolation and median filtering
- 3D pose smoothing with Butterworth filtering
- Plot generation and demo video rendering
- Structured logs for each pipeline step

### 5. Data Collection

- Camera-based local clip capture
- Action labeling for future training
- CSV label export

## Output Value

- Faster coaching feedback than manual frame-by-frame review
- More consistent cues than subjective observation alone
- Better training traceability through logs, scores, and visual outputs
- A practical bridge between sports technique coaching and biomechanical screening

## Current Technical Positioning

This product currently provides coach-grade screening and visual analytics using monocular vision. It is not a medical device and should not be presented as clinical diagnosis. Clinical-grade interpretation would require stronger calibration, multi-view or depth sensing, and formal validation against instrumented biomechanics systems.

## Planned Next Steps

1. Stronger football event recognition with learned models
2. Better ball tracking and contact timing
3. Person re-identification and more robust multi-person handling
4. Personalized threshold adaptation using calibration and anthropometrics
5. Exportable PDF session report with evidence frames and intervention plan
