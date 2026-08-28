#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


def _iter_kinetics(root: Path):
    records = []
    for split in ["train", "val", "test"]:
        base = root / split
        if not base.exists():
            continue
        for label_dir in base.iterdir():
            if not label_dir.is_dir():
                continue
            label = label_dir.name
            for vid in label_dir.rglob("*.mp4"):
                records.append({
                    "dataset": "kinetics700",
                    "split": split,
                    "clip_id": vid.stem,
                    "video_path": str(vid),
                    "label": label,
                    "start_ms": None,
                    "end_ms": None,
                    "fps": None,
                    "extra": {},
                })
    return records


def _iter_h36m(root: Path):
    records = []
    for npz in root.rglob("*.npz"):
        records.append({
            "dataset": "h36m",
            "split": "unknown",
            "clip_id": npz.stem,
            "video_path": str(npz),
            "label": "pose3d",
            "start_ms": None,
            "end_ms": None,
            "fps": None,
            "extra": {},
        })
    return records


def _iter_soccernet(labels_csv: Path):
    records = []
    with labels_csv.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "dataset": "soccernet",
                "split": row.get("split", "train") or "train",
                "clip_id": row["clip_id"],
                "video_path": row["video_path"],
                "label": row["action"],
                "start_ms": int(row["start_ms"]) if row.get("start_ms") else None,
                "end_ms": int(row["end_ms"]) if row.get("end_ms") else None,
                "fps": float(row["fps"]) if row.get("fps") else None,
                "extra": {},
            })
    return records


def build_index(h36m_root, kinetics_root, soccernet_labels, out_path: Path):
    records = []
    if h36m_root:
        records.extend(_iter_h36m(Path(h36m_root)))
    if kinetics_root:
        records.extend(_iter_kinetics(Path(kinetics_root)))
    if soccernet_labels:
        records.extend(_iter_soccernet(Path(soccernet_labels)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    return {"count": len(records), "out": str(out_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h36m_root", default=None)
    ap.add_argument("--kinetics_root", default=None)
    ap.add_argument("--soccernet_labels", default=None)
    ap.add_argument("--out", default="data/unified_index.jsonl")
    args = ap.parse_args()

    summary = build_index(args.h36m_root, args.kinetics_root, args.soccernet_labels, Path(args.out))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
