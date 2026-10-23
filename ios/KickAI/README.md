# Kick · iOS Client

**English** · [简体中文](README.zh-CN.md)

A SwiftUI football video-analysis app with movement selection, video upload, training feedback, playback, and history, plus entry points for community, venues, and coaching services.

[Project Home](../../README.md) · [Analysis Backend](../../backend/README.md)

## Requirements

- macOS and Xcode with support for the iOS 17 SDK.
- An iOS 17 or later simulator or device.
- A reachable Kick analysis backend.

## Local Setup

1. Open `Kick.xcodeproj` in this directory.
2. Select the `KickAI` scheme and target device.
3. Start the analysis backend and confirm that video analysis is available in `/health`.
4. Configure the address below, then run the app. Physical-device builds also require your own signing team in Xcode.

## Analysis Service Address

Configure variables under **Product → Scheme → Edit Scheme → Run → Arguments → Environment Variables**:

| Scenario | Variable | Value |
| --- | --- | --- |
| Simulator using the local backend | No configuration needed | Defaults to `http://127.0.0.1:8000` |
| Simulator using another backend | `KICKAI_ANALYZE_SIMULATOR_BASE_URL` | Reachable service base URL |
| Physical device connecting to a Mac | `KICKAI_ANALYZE_DEVICE_BASE_URL` | `http://<your-Mac-LAN-IP>:8000` |
| Shared override | `KICKAI_ANALYZE_BASE_URL` | Takes precedence over device and simulator settings |

Use the service base URL without `/analyze_video`; the client appends the endpoint.

The device and Mac must be reachable over the network, with the backend listening on `0.0.0.0:8000`. On a physical device, `127.0.0.1` refers to the phone itself. The code retains the original developer's default device address, so explicitly configure your own.

See [VideoAnalysisService.swift](KickAI/Services/VideoAnalysisService.swift) for configuration logic.

## Features & Analysis Status

The app includes entry points for passing, shooting, receiving, pass-receive sequences, and single-player long videos. See [AnalysisActionChoice.swift](KickAI/Models/AnalysisActionChoice.swift) for movement and template mappings.

The backend returns analysis status, warnings, and feedback. A successful request does not establish a valid analysis. Check compatibility between the receiving flow and the backend route during integration.

Configure map credentials through backend environment variables; keep them out of the client and repository. Coaching, subscription, and discovery screens do not imply that their commercial services are live.

## Validation

Select the `KickAI` scheme in Xcode and choose **Product → Test**. Unit and UI tests are located in `KickAITests/` and `KickAIUITests/`, respectively.

Keep `xcuserdata`, build caches, personal device settings, and local credentials out of Git.
