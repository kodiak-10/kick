#!/usr/bin/env bash
set -euo pipefail

clip_id="${1:-sample01}"
repo_path="${2:-.}"

mkdir -p "$repo_path/raw" "$repo_path/keypoints" "$repo_path/pose3d"
cp "tests/samples/sample_short.mp4" "$repo_path/raw/${clip_id}.mp4"
cp "tests/samples/keypoints_sample.json" "$repo_path/keypoints/${clip_id}_2d.json"
cp "tests/samples/pose3d_sample.npz" "$repo_path/pose3d/${clip_id}_3d.npz"

python coach.py --clip_id "$clip_id" --repo_path "$repo_path"
