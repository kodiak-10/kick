<div align="center">

<img src="ios/KickAI/KickAI/Assets.xcassets/AppIcon.appiconset/KickIcon-120.png" alt="Kick app icon" width="88" />

# Kick

**English** · [简体中文](README.zh-CN.md)

### Turn every training session into visible progress.

Football video analysis connecting movement assessment, video review, and training feedback.

**SwiftUI · FastAPI · Computer Vision**

[Quick Start](#quick-start) · [iOS Client](ios/KickAI/README.md) · [Backend & API](backend/README.md)

</div>

---

## Overview

Kick combines video upload and playback on iOS with a Python backend for pose detection, football movement rules, and scoring. It helps users review their movements, understand feedback, and keep track of training.

This repository includes the primary app, the analysis service, and exploratory implementations. The capabilities below describe the current code; they do not imply production readiness or independently validated accuracy.

## Core Experience

| Area | Current implementation |
| --- | --- |
| Movement analysis | Selection flows and backend routes for passing, shooting, receiving, and pass-receive sequences |
| Training feedback | Movement scores, issue descriptions, and analysis status presented in the client |
| Video review | Video playback alongside feedback, with a training history entry point |
| Long-video exploration | A single-player long-video flow, target tracking, and action-window localization |
| Football discovery | Interfaces and screens for community posts, venue search, coach listings, and bookings |

Results depend on camera angle, occlusion, video quality, and movement type. Scores reflect the current rules and vision pipeline and should be interpreted alongside the original footage. Long-video and discovery features require validation for each intended use case.

## How It Works

```text
Select an action and video
          ↓
Upload from the SwiftUI client
          ↓
FastAPI receives the request and selects an analysis route
          ↓
Pose & ball tracking → Movement rules & scoring → Quality status & feedback
          ↓
Client report and video review
```

The service returns status and warning information. Integrations should inspect both the result and its analysis status; a successful HTTP request alone does not establish a valid analysis.

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
