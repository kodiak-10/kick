# Xcode Migration Plan

## Goal

Move the current Python-based AI Coach prototype toward a ship-ready macOS or iOS application that can be developed, packaged, and distributed from Xcode.

## Current State

The current system is a Python prototype focused on:

- real-time camera input
- pose estimation
- football analysis logic
- bilingual UI overlay
- calibration
- offline pipeline and reporting

This is useful for fast iteration, but it is not a final App Store-grade architecture.

## What Can Be Reused

The following layers can largely be reused conceptually:

1. product flow
   - preparation stage
   - subject lock
   - session start confirmation
   - active analysis
   - reset and review

2. analysis logic
   - football phases
   - risk rules
   - target lock logic
   - calibration rules
   - event freeze logic

3. data model
   - session state
   - scores
   - metrics
   - event summaries

## What Should Eventually Be Rewritten

For Xcode shipping, these parts should move to native implementation:

1. camera pipeline
   - use `AVFoundation`

2. UI
   - use `SwiftUI` or `UIKit/AppKit`

3. rendering
   - use native layered rendering instead of OpenCV window drawing

4. real-time inference
   - use Core ML, TensorFlow Lite, or a native runtime

5. threading
   - use native dispatch queues / structured concurrency

## Recommended Xcode Product Path

### Phase 1. Stable Prototype

Keep using Python to validate:

- live product flow
- interaction design
- scoring logic
- target lock behavior
- football event behavior

### Phase 2. Native Shell

Build an Xcode app shell with:

- camera preview
- start / stop flow
- calibration screen
- analysis dashboard
- local session storage

At this stage the Python prototype is still the reference behavior.

### Phase 3. Native Inference + Native UI

Replace Python real-time parts with:

- native camera capture
- native overlay rendering
- native model inference
- native event logic

### Phase 4. Productization

Add:

- settings
- onboarding
- permissions flow
- session export
- privacy handling
- crash reporting
- performance profiling

## Architecture Recommendation

For a final Xcode app:

1. `CameraService`
   - owns camera stream

2. `AnalysisService`
   - owns pose, ball, and rule logic

3. `SessionCoordinator`
   - owns app state machine

4. `OverlayRenderer`
   - draws skeleton, target box, ball, and event cards

5. `ReportService`
   - exports summaries and reports

## Recommended Native Tech Choices

### macOS-first route

- `SwiftUI`
- `AVFoundation`
- `Core ML`
- optional `Metal` for overlay acceleration

### iPhone / iPad route

- `SwiftUI`
- `AVCaptureSession`
- `Vision` + `Core ML`
- optional `ARKit` if future depth support is needed

## Immediate Development Strategy

Do not try to jump directly from current Python code to App Store packaging.

The correct sequence is:

1. make prototype behavior stable
2. freeze the UX and state machine
3. freeze the scoring contract
4. then migrate to Xcode-native implementation

See also:

- [Product Rebuild Taskbook](./product_rebuild_taskbook.md)

That document defines what the prototype must become before native migration should be frozen.

## Current Priority For The Prototype

Before migration, the Python build still needs:

1. a product-grade training flow instead of a debug-style overlay
2. consistent 30+ FPS real-time flow
3. stronger football-specific action and event understanding
4. stable event freeze display and session-end review
5. session summary export and history-ready data model

## Bottom Line

Current code is the product logic prototype.
Xcode shipping will require a native app layer and likely a native inference path.
That is normal. The current work is not wasted; it is defining the behavior contract of the final product.
