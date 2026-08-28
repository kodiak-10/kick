#!/usr/bin/env bash
set -euo pipefail

clip=""
keypoints=""
pose=""
video=""
out=""
min_frames=""
dev=""
preview=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clip)
      clip="$2"; shift 2;;
    --keypoints)
      keypoints="$2"; shift 2;;
    --pose)
      pose="$2"; shift 2;;
    --video)
      video="$2"; shift 2;;
    --out)
      out="$2"; shift 2;;
    --min_frames)
      min_frames="$2"; shift 2;;
    --dev)
      dev="--dev"; shift;;
    --preview)
      preview="--preview"; shift;;
    *)
      echo "Unknown arg: $1"; exit 1;;
  esac
 done

if [[ -z "$clip" || -z "$keypoints" || -z "$pose" ]]; then
  echo "Usage: $0 --clip <id> --keypoints <json> --pose <npz> [--video <mp4>] [--out <mp4>] [--min_frames N] [--dev]" >&2
  exit 1
fi

if [[ -z "$out" ]]; then
  out="reports/demo_with_summary_${clip}.mp4"
fi

cmd=(python frontend/summary_card.py --clip "$clip" --keypoints "$keypoints" --pose "$pose" --out "$out")
if [[ -n "$video" ]]; then
  cmd+=(--video "$video")
fi
if [[ -n "$min_frames" ]]; then
  cmd+=(--min_frames "$min_frames")
fi
if [[ -n "$dev" ]]; then
  cmd+=("$dev")
fi
if [[ -n "$preview" ]]; then
  cmd+=("$preview")
fi

"${cmd[@]}"

echo "Wrote $out"
