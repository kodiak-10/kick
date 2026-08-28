from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np


MODEL_VERSION = "calibration_v1"
mp_pose = mp.solutions.pose
DEFAULT_CALIBRATION_FALLBACK_INDICES = [3, 0, 1, 2, 4]
_CAMERA_BACKEND_NAMES = ("CAP_AVFOUNDATION", "CAP_ANY", "CAP_DSHOW", "CAP_MSMF", "CAP_V4L2")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _error_result(
    error_code: str,
    message: str,
    *,
    camera_index: Any = None,
    camera_source: Any = None,
    tried_sources: Optional[List[Dict[str, Any]]] = None,
    selected_source: Optional[Dict[str, Any]] = None,
    opened_source: Optional[Dict[str, Any]] = None,
    final_cap_opened: bool = False,
    final_read_succeeded: bool = False,
    suggested_index: Any = None,
) -> Dict[str, Any]:
    # Expected calibration failures should return structured JSON instead of raising.
    return {
        "ok": False,
        "mode": "calibrate",
        "error_code": error_code,
        "message": message,
        "camera_index": camera_index,
        "camera_source": camera_source,
        "attempts": tried_sources or [],
        "tried_sources": tried_sources or [],
        "selected_source": selected_source,
        "suggested_index": suggested_index,
        "opened_source": opened_source,
        "final_cap_opened": bool(final_cap_opened),
        "final_read_succeeded": bool(final_read_succeeded),
    }


def _success_result(
    profile: Dict[str, Any],
    *,
    camera_index: Any = None,
    camera_source: Any = None,
    tried_sources: Optional[List[Dict[str, Any]]] = None,
    selected_source: Optional[Dict[str, Any]] = None,
    opened_source: Optional[Dict[str, Any]] = None,
    final_cap_opened: bool = True,
    final_read_succeeded: bool = True,
    out_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "mode": "calibrate",
        "message": "Calibration completed successfully.",
        "camera_index": camera_index,
        "camera_source": camera_source,
        "attempts": tried_sources or [],
        "tried_sources": tried_sources or [],
        "selected_source": selected_source,
        "opened_source": opened_source,
        "final_cap_opened": bool(final_cap_opened),
        "final_read_succeeded": bool(final_read_succeeded),
        "saved_to": str(Path(out_path).resolve()) if out_path is not None else None,
        "profile": profile,
    }


def _camera_backends() -> List[Tuple[str, Any]]:
    backends: List[Tuple[str, Any]] = []
    seen_values = set()
    for name in _CAMERA_BACKEND_NAMES:
        val = getattr(cv2, name, None)
        if val is not None and val not in seen_values:
            backends.append((name, val))
            seen_values.add(val)
    return backends or [("default", None)]


def _source_label(kind: str, value: Any, backend_name: Optional[str] = None) -> str:
    if kind == "camera_source":
        return f"camera_source:{value}"
    if backend_name and backend_name != "default":
        return f"camera_index:{value} ({backend_name})"
    return f"camera_index:{value}"


def _build_attempt_record(
    *,
    kind: str,
    value: Any,
    backend_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "value": value,
        "backend": backend_name or "default",
        "source_label": _source_label(kind, value, backend_name),
        "probe_opened": False,
        "probe_readable": False,
        "probe_status": "pending",
        "probe_reads": 0,
        "probe_frame_mean": None,
        "final_opened": False,
        "final_read_succeeded": False,
        "final_status": "pending",
        "final_reads": 0,
        "final_frame_mean": None,
        "selected": False,
    }


def _open_capture_for_source(
    *,
    kind: str,
    value: Any,
    backend_name: Optional[str] = None,
    backend_value: Any = None,
):
    if kind == "camera_source":
        return cv2.VideoCapture(value)
    if backend_value is None:
        return cv2.VideoCapture(value)
    return cv2.VideoCapture(value, backend_value)


def _probe_camera_source(
    *,
    kind: str,
    value: Any,
    backend_name: Optional[str] = None,
    backend_value: Any = None,
    probe_reads: int = 12,
) -> Dict[str, Any]:
    attempt = _build_attempt_record(kind=kind, value=value, backend_name=backend_name)
    cap = _open_capture_for_source(kind=kind, value=value, backend_name=backend_name, backend_value=backend_value)
    attempt["probe_opened"] = bool(cap.isOpened())
    if not attempt["probe_opened"]:
        attempt["probe_status"] = "open_failed"
        cap.release()
        return attempt

    for probe_idx in range(probe_reads):
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        attempt["probe_reads"] = probe_idx + 1
        attempt["probe_frame_mean"] = round(float(frame.mean()), 2)
        if float(frame.mean()) > 3.0:
            attempt["probe_readable"] = True
            attempt["probe_status"] = "success"
            cap.release()
            return attempt

    attempt["probe_status"] = "frame_probe_failed"
    cap.release()
    return attempt


def _final_open_camera_source(
    source_record: Dict[str, Any],
    *,
    final_reads: int = 3,
) -> Tuple[Optional[Any], Dict[str, Any]]:
    attempt = dict(source_record)
    kind = attempt.get("kind")
    value = attempt.get("value")
    backend_name = attempt.get("backend")
    backend_value = None
    if kind == "camera_index" and backend_name not in (None, "default"):
        backend_value = getattr(cv2, backend_name, None)

    cap = _open_capture_for_source(
        kind=kind,
        value=value,
        backend_name=backend_name,
        backend_value=backend_value,
    )
    attempt["final_opened"] = bool(cap.isOpened())
    if not attempt["final_opened"]:
        attempt["final_status"] = "open_failed"
        cap.release()
        return None, attempt

    for final_idx in range(final_reads):
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        attempt["final_reads"] = final_idx + 1
        attempt["final_frame_mean"] = round(float(frame.mean()), 2)
        if float(frame.mean()) > 3.0:
            attempt["final_read_succeeded"] = True
            attempt["final_status"] = "success"
            return cap, attempt

    attempt["final_status"] = "frame_read_failed"
    cap.release()
    return None, attempt


def _open_camera_with_attempts(camera_index=None, camera_source=None) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    selected_source: Optional[Dict[str, Any]] = None
    opened_source: Optional[Dict[str, Any]] = None
    seen_candidates = set()

    ordered_candidates: List[Tuple[str, Any]] = []
    if camera_source is not None and str(camera_source).strip():
        ordered_candidates.append(("camera_source", camera_source))
    if camera_index is not None:
        ordered_candidates.append(("camera_index", int(camera_index)))
    for fallback_index in DEFAULT_CALIBRATION_FALLBACK_INDICES:
        ordered_candidates.append(("camera_index", int(fallback_index)))

    for kind, value in ordered_candidates:
        if kind == "camera_source":
            candidate_key = (kind, str(value), "default")
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)

            probe = _probe_camera_source(kind=kind, value=value, backend_name="default", backend_value=None)
            probe["attempt_order"] = len(attempts) + 1
            attempts.append(probe)
            if not probe.get("probe_readable"):
                continue

            selected_source = dict(probe)
            selected_source["selected"] = True
            final_cap, final_record = _final_open_camera_source(selected_source)
            selected_source.update(
                {
                    "final_opened": final_record.get("final_opened", False),
                    "final_read_succeeded": final_record.get("final_read_succeeded", False),
                    "final_status": final_record.get("final_status", "pending"),
                    "final_reads": final_record.get("final_reads", 0),
                    "final_frame_mean": final_record.get("final_frame_mean"),
                }
            )
            attempts[-1] = selected_source
            if final_cap is not None:
                opened_source = dict(selected_source)
                return {
                    "ok": True,
                    "cap": final_cap,
                    "selected_source": selected_source,
                    "opened_source": opened_source,
                    "attempts": attempts,
                }
            continue

        for backend_name, backend_value in _camera_backends():
            candidate_key = (kind, str(value), backend_name or "default")
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)

            probe = _probe_camera_source(
                kind=kind,
                value=value,
                backend_name=backend_name,
                backend_value=backend_value,
            )
            probe["attempt_order"] = len(attempts) + 1
            attempts.append(probe)
            if not probe.get("probe_readable"):
                continue

            selected_source = dict(probe)
            selected_source["selected"] = True
            final_cap, final_record = _final_open_camera_source(selected_source)
            selected_source.update(
                {
                    "final_opened": final_record.get("final_opened", False),
                    "final_read_succeeded": final_record.get("final_read_succeeded", False),
                    "final_status": final_record.get("final_status", "pending"),
                    "final_reads": final_record.get("final_reads", 0),
                    "final_frame_mean": final_record.get("final_frame_mean"),
                }
            )
            attempts[-1] = selected_source
            if final_cap is not None:
                opened_source = dict(selected_source)
                return {
                    "ok": True,
                    "cap": final_cap,
                    "selected_source": selected_source,
                    "opened_source": opened_source,
                    "attempts": attempts,
                }

    return {
        "ok": False,
        "cap": None,
        "selected_source": selected_source,
        "opened_source": opened_source,
        "attempts": attempts,
    }


def _landmark_xy(lm, idx, w, h):
    p = lm[idx]
    return np.array([p.x * w, p.y * h], dtype=np.float32)


def _collect_snapshot(lm, w, h):
    ids = {
        "nose": mp_pose.PoseLandmark.NOSE,
        "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER,
        "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER,
        "left_hip": mp_pose.PoseLandmark.LEFT_HIP,
        "right_hip": mp_pose.PoseLandmark.RIGHT_HIP,
        "left_knee": mp_pose.PoseLandmark.LEFT_KNEE,
        "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE,
        "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE,
        "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE,
    }
    return {name: _landmark_xy(lm, idx, w, h) for name, idx in ids.items()}


def _is_ready(lm):
    ids = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.RIGHT_KNEE,
        mp_pose.PoseLandmark.LEFT_ANKLE,
        mp_pose.PoseLandmark.RIGHT_ANKLE,
    ]
    vis = [lm[idx].visibility for idx in ids]
    ys = [lm[idx].y for idx in ids]
    return min(vis) > 0.55 and (max(ys) - min(ys)) > 0.45


def _build_profile(samples, user_height_m):
    data = {}
    for key in samples[0].keys():
        stacked = np.stack([s[key] for s in samples], axis=0)
        data[key] = stacked.mean(axis=0)

    top_y = min(data["nose"][1], data["left_shoulder"][1], data["right_shoulder"][1])
    bottom_y = max(data["left_ankle"][1], data["right_ankle"][1])
    body_height_px = max(1.0, float(bottom_y - top_y))
    shoulder_width_px = float(np.linalg.norm(data["left_shoulder"] - data["right_shoulder"]))
    hip_width_px = float(np.linalg.norm(data["left_hip"] - data["right_hip"]))
    stance_width_px = float(np.linalg.norm(data["left_ankle"] - data["right_ankle"]))
    scale_m_per_px = float(user_height_m / body_height_px)
    return {
        "model_version": MODEL_VERSION,
        "generated_at": _now_iso(),
        "user_height_m": float(user_height_m),
        "body_height_px": body_height_px,
        "scale_m_per_px": scale_m_per_px,
        "shoulder_width_px": shoulder_width_px,
        "hip_width_px": hip_width_px,
        "stance_width_px": stance_width_px,
    }


def load_calibration(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def calibrate_live(camera_index=None, camera_source=None, user_height_m=1.70, out_path="calibration/user_profile.json"):
    open_result = _open_camera_with_attempts(camera_index=camera_index, camera_source=camera_source)
    if not open_result["ok"] or open_result["cap"] is None:
        return _error_result(
            "camera_open_failed",
            "Failed to open camera for calibration",
            camera_index=camera_index,
            camera_source=camera_source,
            tried_sources=open_result.get("attempts") or open_result.get("tried_sources") or [],
            selected_source=open_result.get("selected_source"),
            opened_source=open_result.get("opened_source"),
            final_cap_opened=bool((open_result.get("opened_source") or {}).get("final_opened")),
            final_read_succeeded=bool((open_result.get("opened_source") or {}).get("final_read_succeeded")),
            suggested_index=DEFAULT_CALIBRATION_FALLBACK_INDICES[0],
        )

    cap = open_result["cap"]
    selected_source = open_result.get("selected_source")
    opened_source = open_result.get("opened_source")
    final_cap_opened = bool((opened_source or {}).get("final_opened"))
    final_read_succeeded = bool((opened_source or {}).get("final_read_succeeded"))

    if not selected_source or not opened_source or not final_cap_opened or not final_read_succeeded:
        return _error_result(
            "camera_open_failed",
            "Failed to open camera for calibration",
            camera_index=camera_index,
            camera_source=camera_source,
            tried_sources=open_result.get("attempts") or open_result.get("tried_sources") or [],
            selected_source=selected_source,
            opened_source=opened_source,
            final_cap_opened=final_cap_opened,
            final_read_succeeded=final_read_succeeded,
            suggested_index=DEFAULT_CALIBRATION_FALLBACK_INDICES[0],
        )

    pose = mp_pose.Pose(
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    samples = []
    stable_frames = 0
    last_snapshot = None

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        h, w = frame.shape[:2]
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        message = "Stand upright, full body in frame, press q to cancel"

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            if _is_ready(lm):
                snap = _collect_snapshot(lm, w, h)
                if last_snapshot is not None:
                    diffs = [np.linalg.norm(snap[k] - last_snapshot[k]) for k in snap]
                    if float(np.mean(diffs)) < 6.0:
                        stable_frames += 1
                    else:
                        stable_frames = 0
                last_snapshot = snap
                if stable_frames >= 8:
                    samples.append(snap)
                message = f"Calibration capture / 标定采样: {len(samples)}/24"
                if len(samples) >= 24:
                    break
            else:
                stable_frames = 0

        cv2.putText(frame, message, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow("AI Coach Calibration", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return _error_result(
                "calibration_cancelled",
                "Calibration cancelled.",
                camera_index=camera_index,
                camera_source=camera_source,
                tried_sources=open_result.get("attempts") or open_result.get("tried_sources") or [],
                selected_source=selected_source,
                opened_source=opened_source,
                final_cap_opened=final_cap_opened,
                final_read_succeeded=final_read_succeeded,
                suggested_index=DEFAULT_CALIBRATION_FALLBACK_INDICES[0],
            )

    cap.release()
    cv2.destroyAllWindows()

    if len(samples) < 12:
        return _error_result(
            "insufficient_calibration_samples",
            "Calibration failed: not enough stable full-body samples.",
            camera_index=camera_index,
            camera_source=camera_source,
            tried_sources=open_result.get("attempts") or open_result.get("tried_sources") or [],
            selected_source=selected_source,
            opened_source=opened_source,
            final_cap_opened=final_cap_opened,
            final_read_succeeded=final_read_succeeded,
            suggested_index=DEFAULT_CALIBRATION_FALLBACK_INDICES[0],
        )

    profile = _build_profile(samples, user_height_m=user_height_m)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2))
    return _success_result(
        profile,
        camera_index=camera_index,
        camera_source=camera_source,
        tried_sources=open_result.get("attempts") or open_result.get("tried_sources") or [],
        selected_source=selected_source,
        opened_source=opened_source,
        final_cap_opened=final_cap_opened,
        final_read_succeeded=final_read_succeeded,
        out_path=out,
    )
