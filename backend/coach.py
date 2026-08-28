#!/usr/bin/env python3
import argparse
import json
import os
import time
import sys
from pathlib import Path
import shutil

_MPL_CACHE = Path(__file__).resolve().parent / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

from analysis.shot_analysis import analyze_shot, analyze_video


def _run_legacy_offline_pipeline(clip_id, repo_path, preview=False):
    from vision.detect_pose import detect_pose
    from vision.clean_keypoints import clean_keypoints
    from biomechanics.lift2dto3d import lift2dto3d
    from tools.smooth_pose3d import smooth_pose3d
    from analysis.classify_action import classify_action
    from analysis.explain import explain
    from ui.render_summary import render_summary

    repo = Path(repo_path)
    log = {"clip_id": clip_id, "start_time": time.time(), "steps": [], "warnings": []}
    raw = repo / "raw" / f"{clip_id}.mp4"
    k2d = repo / "keypoints" / f"{clip_id}_2d.json"
    if not k2d.exists():
        log["warnings"].append("keypoints missing; detect_pose placeholder used")
        detect_pose(raw, k2d)
    cleaned = repo / "keypoints" / "cleaned" / f"{clip_id}_2d_cleaned.json"
    clean_log = repo / "logs" / f"clean_keypoints_{clip_id}.json"
    t = time.time(); s1 = clean_keypoints(k2d, cleaned, log_path=clean_log); log["steps"].append({"stage": "clean", **s1, "sec": time.time()-t})
    p3d = repo / "pose3d" / f"{clip_id}_3d.npz"
    if not p3d.exists():
        log["warnings"].append("pose3d missing; placeholder lift used")
        lift2dto3d(cleaned, p3d)
    p3d_sm = repo / "pose3d" / f"{clip_id}_3d_smoothed.npz"
    t = time.time(); s2 = smooth_pose3d(p3d, p3d_sm); log["steps"].append({"stage": "smooth", **s2, "sec": time.time()-t})
    action = classify_action(p3d_sm)
    explanation = explain(p3d_sm, action)
    render_summary(cleaned, p3d_sm, action, explanation, repo / "reports" / f"demo_with_summary_{clip_id}.mp4", preview=preview)
    log["end_time"] = time.time(); log["elapsed_s"] = log["end_time"] - log["start_time"]
    out = repo / "logs" / f"pipeline_improve_{clip_id}.json"; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log))
    return log


def run(clip_id, repo_path, preview=False):
    """Legacy offline pipeline kept for compatibility with existing tooling."""
    return _run_legacy_offline_pipeline(clip_id, repo_path, preview=preview)


def _print_json(payload, indent=2):
    print(json.dumps(payload, ensure_ascii=False, indent=indent))


def _print_debug(message: str) -> None:
    print(message, file=sys.stderr)


def _shot_output_path(repo: Path, video_path: Path):
    return repo / "logs" / f"shot_analysis_{video_path.stem}.json"


def _video_output_path(repo: Path, video_path: Path):
    return repo / "logs" / f"video_analysis_{video_path.stem}.json"


def _seed_sample(repo: Path, clip_id: str):
    sample_dir = repo / "tests" / "samples"
    if not sample_dir.exists():
        return False
    (repo / "raw").mkdir(parents=True, exist_ok=True)
    (repo / "keypoints").mkdir(parents=True, exist_ok=True)
    (repo / "pose3d").mkdir(parents=True, exist_ok=True)
    if not (repo / "raw" / f"{clip_id}.mp4").exists() and (sample_dir / "sample_short.mp4").exists():
        shutil.copyfile(sample_dir / "sample_short.mp4", repo / "raw" / f"{clip_id}.mp4")
    if not (repo / "keypoints" / f"{clip_id}_2d.json").exists() and (sample_dir / "keypoints_sample.json").exists():
        shutil.copyfile(sample_dir / "keypoints_sample.json", repo / "keypoints" / f"{clip_id}_2d.json")
    if not (repo / "pose3d" / f"{clip_id}_3d.npz").exists() and (sample_dir / "pose3d_sample.npz").exists():
        shutil.copyfile(sample_dir / "pose3d_sample.npz", repo / "pose3d" / f"{clip_id}_3d.npz")
    return True


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip_id", default="sample01")
    ap.add_argument("--repo_path", default=".")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--mode", choices=["offline", "analyze_video", "shot", "live", "collect", "camera_check", "calibrate"], default="offline")
    ap.add_argument("--video_path", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--json_indent", type=int, default=2)
    ap.add_argument("--camera_index", type=int, default=None)
    ap.add_argument("--camera_source", default=None)
    ap.add_argument("--sport_label", default=None)
    ap.add_argument("--sport_mode", choices=["auto", "soccer_basic"], default="soccer_basic")
    ap.add_argument("--collect_dir", default="captured")
    ap.add_argument("--max_index", type=int, default=6)
    ap.add_argument("--calibration_path", default="calibration/user_profile.json")
    ap.add_argument("--user_height_m", type=float, default=1.70)
    ap.add_argument("--profile_output", default=None)
    ap.add_argument("--profile_label", default="live")
    ap.add_argument("--max_runtime_s", type=float, default=None)
    ap.add_argument("--headless", action="store_true")
    return ap


def _handle_shot_mode(args, repo: Path) -> None:
    if not args.video_path:
        raise SystemExit("--video_path is required when --mode shot")
    video_path = Path(args.video_path)
    # Keep `--mode shot` as a compatibility alias, but route through the
    # generic video analyzer instead of the legacy fixed shot entry.
    output_path = Path(args.output) if args.output else _video_output_path(repo, video_path)
    payload = analyze_video(video_path, output_path=output_path, calibration_path=args.calibration_path)
    _print_json(payload, indent=args.json_indent)


def _handle_video_mode(args, repo: Path) -> None:
    if not args.video_path:
        raise SystemExit("--video_path is required when --mode analyze_video")
    video_path = Path(args.video_path)
    output_path = Path(args.output) if args.output else _video_output_path(repo, video_path)
    payload = analyze_video(video_path, output_path=output_path, calibration_path=args.calibration_path)
    _print_json(payload, indent=args.json_indent)


def _handle_live_mode(args) -> None:
    from vision.live_mode import run_live

    run_live(
        camera_index=args.camera_index,
        camera_source=args.camera_source,
        sport_label=args.sport_label,
        sport_mode=args.sport_mode,
        calibration_path=args.calibration_path,
        profile_output=args.profile_output,
        max_runtime_s=args.max_runtime_s,
        headless=args.headless,
        profile_label=args.profile_label,
    )
def _handle_collect_mode(args) -> None:
    from tools.collect_dataset import collect

    collect(camera_index=args.camera_index, out_dir=args.collect_dir, fps=30)


def _handle_camera_check_mode(args) -> None:
    from vision.live_mode import diagnose_cameras

    _print_json(diagnose_cameras(max_index=args.max_index, camera_source=args.camera_source), indent=args.json_indent)


def _handle_calibrate_mode(args) -> None:
    from analysis.calibration import calibrate_live

    _print_debug(
        f"[calibrate] start camera_index={args.camera_index!r} camera_source={args.camera_source!r}"
    )
    try:
        result = calibrate_live(
            camera_index=args.camera_index,
            camera_source=args.camera_source,
            user_height_m=args.user_height_m,
            out_path=args.calibration_path,
        )
    except SystemExit as exc:
        result = {
            "ok": False,
            "mode": "calibrate",
            "error_code": "calibration_system_exit",
            "message": str(exc),
            "camera_index": args.camera_index,
            "camera_source": args.camera_source,
            "tried_sources": [],
            "suggested_index": 3,
            "opened_source": None,
        }
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        result = {
            "ok": False,
            "mode": "calibrate",
            "error_code": "calibration_unexpected_error",
            "message": f"{type(exc).__name__}: {exc}",
            "camera_index": args.camera_index,
            "camera_source": args.camera_source,
            "tried_sources": [],
            "suggested_index": 3,
            "opened_source": None,
        }

    if isinstance(result, dict):
        if result.get("ok"):
            _print_debug(
                f"[calibrate] opened_source={json.dumps(result.get('opened_source'), ensure_ascii=False)}"
            )
        else:
            _print_debug(
                f"[calibrate] failed error_code={result.get('error_code')} message={result.get('message')}"
            )
            _print_debug(
                f"[calibrate] tried_sources={json.dumps(result.get('tried_sources') or [], ensure_ascii=False)}"
            )
            if result.get("suggested_index") is not None:
                _print_debug(f"[calibrate] suggested_index={result.get('suggested_index')}")

    _print_json(
        result,
        indent=args.json_indent,
    )


def _handle_legacy_offline_mode(args, repo: Path) -> None:
    _seed_sample(repo, args.clip_id)
    _print_json(run(args.clip_id, args.repo_path, preview=args.preview), indent=args.json_indent)


def dispatch(args) -> None:
    repo = Path(args.repo_path)
    if args.mode == "shot":
        _handle_shot_mode(args, repo)
        return
    if args.video_path or args.mode == "analyze_video":
        _handle_video_mode(args, repo)
        return
    if args.mode == "live":
        _handle_live_mode(args)
        return
    if args.mode == "collect":
        _handle_collect_mode(args)
        return
    if args.mode == "camera_check":
        _handle_camera_check_mode(args)
        return
    if args.mode == "calibrate":
        _handle_calibrate_mode(args)
        return
    _handle_legacy_offline_mode(args, repo)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch(args)


if __name__ == "__main__":
    main()
