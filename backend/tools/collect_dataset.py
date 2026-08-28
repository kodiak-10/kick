#!/usr/bin/env python3
import argparse
import csv
import time
from pathlib import Path

import cv2


LABEL_MAP = {
    ord("1"): "dribble",
    ord("2"): "pass",
    ord("3"): "shoot",
    ord("4"): "jump",
    ord("5"): "cut",
}


def _open_camera(camera_index=None):
    if camera_index is not None:
        cap = cv2.VideoCapture(camera_index)
        return cap if cap.isOpened() else None
    for idx in [0, 1, 2, 3]:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            return cap
        cap.release()
    return None


def collect(camera_index=None, out_dir="captured", fps=30):
    cap = _open_camera(camera_index)
    if cap is None:
        raise SystemExit("Failed to open camera for dataset capture.")

    out_root = Path(out_dir)
    clips_dir = out_root / "clips"
    labels_dir = out_root / "labels"
    clips_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    labels_csv = labels_dir / "local_soccer_labels.csv"
    if not labels_csv.exists():
        with labels_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["clip_id", "video_path", "action", "start_ms", "end_ms", "fps", "split"])

    current_label = "dribble"
    recording = False
    writer = None
    clip_id = ""
    clip_path = None
    start_ts = 0.0

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        h, w = frame.shape[:2]
        status = "REC" if recording else "IDLE"
        cv2.putText(frame, f"status: {status}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
        cv2.putText(frame, f"label: {current_label}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "1-5 label  r start/stop  q quit", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow("Soccer Data Collector", frame)

        if recording and writer is not None:
            writer.write(frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key in LABEL_MAP:
            current_label = LABEL_MAP[key]
        if key == ord("r"):
            if not recording:
                ts = int(time.time() * 1000)
                clip_id = f"{current_label}_{ts}"
                clip_path = clips_dir / f"{clip_id}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(clip_path), fourcc, float(fps), (w, h))
                start_ts = time.time()
                recording = True
            else:
                end_ts = time.time()
                recording = False
                if writer is not None:
                    writer.release()
                    writer = None
                with labels_csv.open("a", newline="") as f:
                    csv.writer(f).writerow([
                        clip_id,
                        str(clip_path),
                        current_label,
                        int(start_ts * 1000),
                        int(end_ts * 1000),
                        fps,
                        "local_train",
                    ])

    if writer is not None:
        writer.release()
    cap.release()
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera_index", type=int, default=None)
    ap.add_argument("--out_dir", default="captured")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()
    collect(camera_index=args.camera_index, out_dir=args.out_dir, fps=args.fps)


if __name__ == "__main__":
    main()
