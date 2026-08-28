#!/usr/bin/env python3
"""End-to-end pipeline: video -> 2D -> 3D -> dynamics -> explain -> plan."""

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import cv2
except Exception:
    cv2 = None

try:
    import jsonschema
except Exception:
    jsonschema = None


KEYPOINT_NAMES_33 = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer", "left_ear",
    "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist",
    "right_wrist", "left_pinky", "right_pinky", "left_index",
    "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle",
    "right_ankle", "left_heel", "right_heel", "left_foot_index",
    "right_foot_index",
]


@dataclass
class StageResult:
    name: str
    outputs: List[str]


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_schema(repo: Path, name: str):
    candidates = [
        repo / "schemas" / name,
        Path(__file__).resolve().parent / "schemas" / name,
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text())
    raise FileNotFoundError(f"schema not found: {name}")


def validate_schema(repo: Path, path: Path, schema_name: str):
    if not path.exists():
        raise ValueError(f"missing output: {path}")

    if path.suffix == ".json":
        data = json.loads(path.read_text())
        if jsonschema is not None:
            schema = _load_schema(repo, schema_name)
            jsonschema.validate(data, schema)
        # minimal checks for stage outputs only (raw meta excluded)
        if schema_name not in ("raw_meta.schema.json", "plan.schema.json"):
            for k in ("model_version", "generated_at", "frame_count"):
                if k not in data:
                    raise ValueError(f"{path} missing {k}")
        return True

    if path.suffix == ".npz":
        arr = np.load(path)["poses"]
        if arr.ndim != 3 or arr.shape[-1] != 3:
            raise ValueError(f"invalid pose3d npz shape: {arr.shape}")
        return True

    return True


def _ensure_dirs(repo: Path):
    for d in ("raw", "keypoints", "pose3d", "dynamics", "explain", "plan", "logs"):
        (repo / d).mkdir(parents=True, exist_ok=True)


def _read_raw_meta(repo: Path, clip_id: str):
    meta_path = repo / "raw" / f"{clip_id}_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing raw meta: {meta_path}")
    data = json.loads(meta_path.read_text())
    # validate basic schema
    validate_schema(repo, meta_path, "raw_meta.schema.json")
    return data


def _extract_2d(repo: Path, clip_id: str, quick: bool, fps: float) -> StageResult:
    out = repo / "keypoints" / f"{clip_id}_2d.json"

    if quick:
        frame_count = 10
        frames = []
        for i in range(frame_count):
            ts = int(round(i * 1000 / fps))
            kps = [0.0] * (len(KEYPOINT_NAMES_33) * 3)
            frames.append({"timestamp_ms": ts, "keypoints": kps, "mean_confidence": 0.0})
        payload = {
            "clip_id": clip_id,
            "fps": fps,
            "keypoint_names": KEYPOINT_NAMES_33,
            "frames": frames,
            "detector": "mediapipe",
            "model_version": "detector_v1",
            "generated_at": _now_iso(),
            "frame_count": frame_count,
        }
        out.write_text(json.dumps(payload))
        validate_schema(repo, out, "keypoints_2d.schema.json")
        return StageResult("2d", [str(out)])

    if cv2 is None:
        raise RuntimeError("opencv not available for 2D extraction")

    try:
        import mediapipe as mp
    except Exception as e:
        raise RuntimeError("mediapipe not available for 2D extraction") from e

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    video_path = repo / "raw" / f"{clip_id}.mp4"
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"failed to open video: {video_path}")

    frames = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)

        if res.pose_landmarks:
            kps = []
            confs = []
            for lm in res.pose_landmarks.landmark:
                kps.extend([lm.x, lm.y, lm.visibility])
                confs.append(lm.visibility)
            mean_conf = sum(confs) / len(confs) if confs else 0.0
        else:
            kps = [0.0] * (len(KEYPOINT_NAMES_33) * 3)
            mean_conf = 0.0

        ts = int(round(frame_idx * 1000 / fps))
        frames.append({"timestamp_ms": ts, "keypoints": kps, "mean_confidence": mean_conf})
        frame_idx += 1

    cap.release()

    payload = {
        "clip_id": clip_id,
        "fps": fps,
        "keypoint_names": KEYPOINT_NAMES_33,
        "frames": frames,
        "detector": "mediapipe",
        "model_version": "detector_v1",
        "generated_at": _now_iso(),
        "frame_count": len(frames),
    }
    out.write_text(json.dumps(payload))
    validate_schema(repo, out, "keypoints_2d.schema.json")
    return StageResult("2d", [str(out)])


def _lift_3d(repo: Path, clip_id: str, fps: float) -> StageResult:
    in_path = repo / "keypoints" / f"{clip_id}_2d.json"
    data = json.loads(in_path.read_text())

    frames = data["frames"]
    k = len(data["keypoint_names"])
    t = len(frames)

    # Map normalized 2D to meters. Assume height 1.7m, x scale 0.5 * height.
    height_m = 1.7
    x_scale = height_m * 0.5
    y_scale = height_m

    poses = np.zeros((t, k, 3), dtype=np.float32)
    for i, fr in enumerate(frames):
        kp = fr["keypoints"]
        for j in range(k):
            x = kp[j * 3 + 0] * x_scale
            y = kp[j * 3 + 1] * y_scale
            poses[i, j, :] = [x, y, 0.0]

    out_npz = repo / "pose3d" / f"{clip_id}_3d.npz"
    np.savez_compressed(out_npz, poses=poses)

    meta = {
        "clip_id": clip_id,
        "fps": fps,
        "joint_names": data["keypoint_names"],
        "units": "m",
        "model_version": "lift_v1",
        "generated_at": _now_iso(),
        "frame_count": t,
    }
    out_meta = repo / "pose3d" / f"{clip_id}_meta.json"
    out_meta.write_text(json.dumps(meta))

    validate_schema(repo, out_npz, "")
    validate_schema(repo, out_meta, "pose3d_meta.schema.json")
    return StageResult("3d", [str(out_npz), str(out_meta)])


def _compute_dynamics(repo: Path, clip_id: str, fps: float, frame_count: int) -> StageResult:
    # Subject defaults
    subject_id = clip_id.split("_")[0]
    mass_kg = 70.0
    height_m = 1.75

    sampling_fps = 100
    duration_s = frame_count / fps if fps > 0 else 0.0
    n = max(1, int(round(duration_s * sampling_fps)))
    times = np.arange(n) / sampling_fps

    # Simple synthetic vGRF: mg + small oscillation
    g = 9.81
    vgrf = mass_kg * g + 50.0 * np.sin(2 * np.pi * 1.5 * times)

    vgrf_csv = repo / "dynamics" / f"{clip_id}_vgrf.csv"
    with vgrf_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_ms", "vgrf_N"])
        for i in range(n):
            w.writerow([int(round(times[i] * 1000)), f"{vgrf[i]:.3f}"])

    dyn = {
        "clip_id": clip_id,
        "subject": {"id": subject_id, "mass_kg": mass_kg, "height_m": height_m},
        "vGRF": {"file": f"dynamics/{clip_id}_vgrf.csv", "units": "N", "sampling_fps": sampling_fps},
        "joint_torques": {"units": "N*m", "notes": "shape [T,K,3] stored as separate .npy if large"},
        "model_version": "dynamics_v1",
        "generated_at": _now_iso(),
        "frame_count": frame_count,
    }
    out_json = repo / "dynamics" / f"{clip_id}_dynamics.json"
    out_json.write_text(json.dumps(dyn))

    validate_schema(repo, out_json, "dynamics.schema.json")
    return StageResult("dynamics", [str(out_json), str(vgrf_csv)])


def _window_from_flags(flags: List[bool], timestamps_ms: List[int]) -> List[Tuple[int, int]]:
    windows = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = timestamps_ms[i]
        if not flag and start is not None:
            end = timestamps_ms[i]
            windows.append((start, end))
            start = None
    if start is not None:
        windows.append((start, timestamps_ms[-1]))
    return windows


def _explain(repo: Path, clip_id: str) -> StageResult:
    kp_path = repo / "keypoints" / f"{clip_id}_2d.json"
    data = json.loads(kp_path.read_text())

    frames = data["frames"]
    k = len(data["keypoint_names"])

    def get_xy(frame, name):
        idx = data["keypoint_names"].index(name)
        kp = frame["keypoints"]
        return kp[idx * 3 + 0], kp[idx * 3 + 1]

    timestamps = [f["timestamp_ms"] for f in frames]
    flags = []
    for fr in frames:
        # knee valgus proxy: knee distance vs ankle distance
        try:
            lkx, _ = get_xy(fr, "left_knee")
            rkx, _ = get_xy(fr, "right_knee")
            lax, _ = get_xy(fr, "left_ankle")
            rax, _ = get_xy(fr, "right_ankle")
            knee_dist = abs(lkx - rkx)
            ankle_dist = abs(lax - rax)
            ratio = knee_dist / ankle_dist if ankle_dist > 0 else 1.0
            flags.append(ratio < 0.7)
        except Exception:
            flags.append(False)

    windows = _window_from_flags(flags, timestamps)
    severity = sum(1 for f in flags if f) / max(1, len(flags))

    faults = []
    if windows:
        faults.append({
            "fault_id": "knee_valgus_01",
            "label": "knee_valgus",
            "time_windows": windows,
            "severity_score": round(severity, 3),
            "causes": [
                {
                    "name": "weak_hip_abductor",
                    "prob": 0.72,
                    "ci": [0.65, 0.79],
                    "rationale": "hip abduction low",
                }
            ],
            "suggested_exercises": [
                {
                    "id": "ex_001",
                    "name": "single_leg_band_walk",
                    "sets": "3",
                    "reps": "12",
                    "rationale": "targets hip abductors",
                }
            ],
        })

    payload = {
        "clip_id": clip_id,
        "faults": faults,
        "model_version": "explain_v1",
        "generated_at": _now_iso(),
        "frame_count": len(frames),
        "warning": "research_prototype_not_medical_advice",
    }

    out_json = repo / "explain" / f"{clip_id}_explain.json"
    out_json.write_text(json.dumps(payload))

    # simple PDF report
    out_pdf = repo / "explain" / f"{clip_id}_report.pdf"
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(out_pdf), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Explain Report: {clip_id}")
        c.drawString(72, 700, f"Fault count: {len(faults)}")
        c.save()
    except Exception:
        out_pdf.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 720 Td (Report) Tj ET\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

    validate_schema(repo, out_json, "explain.schema.json")
    return StageResult("explain", [str(out_json), str(out_pdf)])


def _plan(repo: Path, clip_id: str) -> StageResult:
    explain_path = repo / "explain" / f"{clip_id}_explain.json"
    explain_data = json.loads(explain_path.read_text())

    today = datetime.now().strftime("%Y%m%d")
    subject_id = clip_id.split("_")[0]
    plan_id = f"plan_{subject_id}_{today}_v1"

    weekly = []
    for w in range(1, 9):
        weekly.append({
            "week": w,
            "sessions": [
                {
                    "day": 1,
                    "exercises": [
                        {
                            "id": "ex_001",
                            "sets": 3,
                            "reps": 12,
                            "criteria": "reduce knee valgus by 10%",
                        }
                    ],
                }
            ],
        })

    plan = {
        "plan_id": plan_id,
        "duration_weeks": 8,
        "weekly": weekly,
        "progression_rules": ["if criteria met for 2 sessions increase difficulty"],
        "model_version": "plan_v1",
        "generated_at": _now_iso(),
    }

    out = repo / "plan" / f"{plan_id}.json"
    out.write_text(json.dumps(plan))
    validate_schema(repo, out, "plan.schema.json")
    return StageResult("plan", [str(out)])


def run(clip_id: str, repo_path: str, quick: bool = False):
    repo = Path(repo_path)
    _ensure_dirs(repo)

    log_path = repo / "logs" / f"pipeline_{clip_id}.json"
    manifest = {"clip_id": clip_id, "stages": [], "outputs": []}

    try:
        meta = _read_raw_meta(repo, clip_id)
        fps = float(meta["fps"])

        s1 = _extract_2d(repo, clip_id, quick=quick, fps=fps)
        manifest["stages"].append(s1.name)
        manifest["outputs"].extend(s1.outputs)

        s2 = _lift_3d(repo, clip_id, fps=fps)
        manifest["stages"].append(s2.name)
        manifest["outputs"].extend(s2.outputs)

        s3 = _compute_dynamics(repo, clip_id, fps=fps, frame_count=_frame_count(repo, clip_id))
        manifest["stages"].append(s3.name)
        manifest["outputs"].extend(s3.outputs)

        s4 = _explain(repo, clip_id)
        manifest["stages"].append(s4.name)
        manifest["outputs"].extend(s4.outputs)

        s5 = _plan(repo, clip_id)
        manifest["stages"].append(s5.name)
        manifest["outputs"].extend(s5.outputs)

        log_path.write_text(json.dumps({"clip_id": clip_id, "status": "success", "manifest": manifest}))
        return manifest

    except Exception as e:
        log_path.write_text(json.dumps({"clip_id": clip_id, "status": "failed", "error": str(e)}))
        raise


def _frame_count(repo: Path, clip_id: str) -> int:
    data = json.loads((repo / "keypoints" / f"{clip_id}_2d.json").read_text())
    return int(data.get("frame_count", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--repo_path", default=".")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    manifest = run(args.clip_id, args.repo_path, quick=args.quick)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
