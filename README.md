<div align="center">

<img src="docs/assets/kick-banner.svg" alt="Kick — Football video intelligence. See the movement. Understand the next move." width="100%" />

# Kick

**Football video intelligence. Built around the player.**

Movement analysis, video review, and training feedback — connected in a native iOS experience.

**English** · [简体中文](README.zh-CN.md)

[Explore the Product](#the-training-loop) · [Quick Start](#quick-start) · [iOS Guide](ios/KickAI/README.md) · [Backend & API](backend/README.md)

<sub>SwiftUI · iOS 17+ · Python · FastAPI · OpenCV · MediaPipe</sub>

</div>

---

## From Footage to Feedback

A training video captures what happened. Kick brings movement assessment and feedback into the same review workflow, helping players look closer at how an action was performed and what to work on next.

The project connects a SwiftUI app with a Python computer-vision backend: select a movement, upload a clip, and review the analysis alongside the footage.

<table>
<tr>
<td width="33%" valign="top"><strong>01 / ANALYZE</strong><br /><br />Football-specific movement routes and rule-based scoring for technique and control.</td>
<td width="33%" valign="top"><strong>02 / UNDERSTAND</strong><br /><br />Issue descriptions, phase scores, and quality signals that put a result in context.</td>
<td width="33%" valign="top"><strong>03 / REVIEW</strong><br /><br />Video playback, training feedback, and history in one native iOS workflow.</td>
</tr>
</table>

## The Training Loop

1. **Choose the focus.** Select passing, shooting, receiving, a pass-receive sequence, or the single-player long-video flow.
2. **Bring the footage.** Upload a training clip from the iOS client to the analysis service.
3. **Inspect the movement.** The backend combines pose and ball processing with movement rules, scoring, and quality checks.
4. **Review the feedback.** Return to the footage with scores, issue descriptions, and training cues.

| Product area | What is in the repository |
| --- | --- |
| **Movement analysis** | Explicit action selection and dedicated backend analysis routes |
| **Training feedback** | Technical execution, control stability, phase scores, and next-step advice |
| **Video review** | Playback feedback views and training history |
| **Long-video exploration** | A single-player flow, target tracking, and candidate action-window localization |
| **Football discovery** | Community, venue search, coach listings, and booking interfaces |

## Engineering Behind the Experience

| Design choice | Implementation |
| --- | --- |
| **Explicit movement routing** | The selected action determines the analysis template, with route metadata returned for inspection. [Routing](backend/analysis/analyzer_router.py) |
| **Football-specific scoring** | Movement templates describe preparation, support, contact, and follow-through, with issue explanations and training cues. [Scoring](backend/analysis/football_scoring.py) |
| **Quality signals alongside scores** | Quality checks evaluate frame rate, pose visibility, and ball-track coverage. [Quality checks](backend/quality_gate.py) |
| **Target continuity** | Target-lock logic compares position, body scale, and appearance across frames. [Tracking](backend/analysis/target_tracking.py) |
| **Client and API separation** | SwiftUI handles the app experience; FastAPI exposes analysis and discovery services. [iOS](ios/KickAI/README.md) · [Backend](backend/README.md) |

### Project Status

Kick is under active development. The table above describes code present in the repository, rather than independently validated accuracy or production readiness. Long-video and discovery flows require scenario-specific validation; coaching and booking interfaces do not establish live service fulfillment.

Analysis depends on camera angle, occlusion, footage quality, and action type. Review scores with the original video and inspect analysis status and warnings, including when HTTP requests succeed.

## Quick Start

### 1. Start the Analysis Service

Requires Python 3.10 or later. Dependencies are not pinned; verify compatibility in your local environment.

```bash
git clone https://github.com/kodiak-10/kick.git
cd kick/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Once running, open the [health endpoint](http://127.0.0.1:8000/health) and [interactive API documentation](http://127.0.0.1:8000/docs). Confirm that video analysis is available in the health response and inspect startup warnings.

See the [backend guide](backend/README.md) for map configuration, upload examples, and analysis status details.

### 2. Run the iOS App

1. On macOS, open `ios/KickAI/Kick.xcodeproj` in Xcode with support for the iOS 17 SDK.
2. Select the `KickAI` scheme and a simulator or device running iOS 17 or later.
3. The simulator connects to `http://127.0.0.1:8000` by default. For a physical device, set the following under **Edit Scheme → Run → Arguments → Environment Variables**:

```text
KICKAI_ANALYZE_DEVICE_BASE_URL=http://<your-Mac-LAN-IP>:8000
```

The device and Mac must be able to reach each other over the network. See the [iOS guide](ios/KickAI/README.md) for full configuration.

## Repository Guide

```text
kick/
├── ios/KickAI/          Primary SwiftUI app, Xcode project, and tests
├── ios/AICoach/         Earlier iOS implementation retained for reference
├── backend/
│   ├── main.py         FastAPI entry point
│   ├── analysis/       Action routing, video analysis, tracking, and scoring
│   ├── vision/         Pose detection and keypoint processing
│   ├── tests/          Backend tests and samples
│   ├── docs/           Research, usage guides, and plans
│   └── schemas/        Data structure definitions
└── docs/               Web demos
```

The code and current API define implemented behavior. Planning documents in `backend/docs/` also include ideas that have not yet been implemented.

## Development & Validation

Backend tests:

```bash
cd backend
python -m pytest
```

For iOS tests, select the `KickAI` scheme in Xcode and choose **Product → Test**.

The test directories cover action routing, scoring, video result consistency, and client models, among other areas. Test results must be established by running the relevant checks.

## Feedback & Contributions

Report problems through [Issues](https://github.com/kodiak-10/kick/issues). Include reproduction steps, your environment, the selected action, and the actual result. Remove personal information and credentials before sharing footage or logs.

For changes, describe the purpose and validation performed. Keep map credentials, user videos, local databases, and generated reports out of the repository.
