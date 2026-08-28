from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


@dataclass(frozen=True)
class VideoWindow:
    start_s: float
    end_s: float
    contact_time_s: Optional[float]
    peak_time_s: Optional[float]
    score: float
    confidence: float
    source: str
    reason: str
    debug: Dict[str, Any]

    @property
    def duration_s(self) -> float:
        return max(0.0, float(self.end_s) - float(self.start_s))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_s": round(float(self.start_s), 3),
            "end_s": round(float(self.end_s), 3),
            "duration_s": round(float(self.duration_s), 3),
            "contact_time_s": round(float(self.contact_time_s), 3) if self.contact_time_s is not None else None,
            "peak_time_s": round(float(self.peak_time_s), 3) if self.peak_time_s is not None else None,
            "score": round(float(self.score), 3),
            "confidence": round(float(self.confidence), 3),
            "source": self.source,
            "reason": self.reason,
            "debug": dict(self.debug),
        }


def build_window_from_contact(
    contact_time_s: Optional[float],
    *,
    duration_s: float,
    peak_time_s: Optional[float] = None,
    pre_buffer_s: float = 1.5,
    post_buffer_s: float = 2.5,
    min_duration_s: float = 4.0,
    max_duration_s: float = 6.0,
) -> Tuple[float, float]:
    center_time = float(contact_time_s if contact_time_s is not None else (peak_time_s if peak_time_s is not None else 0.0))
    if duration_s <= 0.0:
        return 0.0, 0.0

    start = center_time - float(pre_buffer_s)
    end = center_time + float(post_buffer_s)
    target_duration = end - start

    if target_duration < min_duration_s:
        pad = (min_duration_s - target_duration) * 0.5
        start -= pad
        end += pad
    elif target_duration > max_duration_s:
        shrink = (target_duration - max_duration_s) * 0.5
        start += shrink
        end -= shrink

    if start < 0.0:
        end = min(duration_s, end - start)
        start = 0.0
    if end > duration_s:
        shift = end - duration_s
        start = max(0.0, start - shift)
        end = duration_s

    if end - start < min_duration_s and duration_s >= min_duration_s:
        center_time = min(duration_s, max(0.0, center_time))
        start = max(0.0, center_time - min_duration_s * 0.5)
        end = min(duration_s, start + min_duration_s)
        if end - start < min_duration_s:
            start = max(0.0, end - min_duration_s)

    if end - start > max_duration_s:
        start = max(0.0, end - max_duration_s)

    return round(float(start), 3), round(float(end), 3)


def normalize_candidate_windows(
    windows: Sequence[Dict[str, Any]],
    *,
    duration_s: float,
    max_windows: int = 3,
    min_gap_s: float = 0.75,
) -> List[VideoWindow]:
    candidates: List[VideoWindow] = []
    for index, raw in enumerate(windows):
        if not isinstance(raw, dict):
            continue
        start_s = float(raw.get("start_s") or raw.get("window_start_s") or 0.0)
        end_s = float(raw.get("end_s") or raw.get("window_end_s") or start_s)
        if end_s <= start_s:
            continue
        contact_time_s = raw.get("contact_time_s")
        peak_time_s = raw.get("peak_time_s")
        score = float(raw.get("score") or raw.get("coarse_score") or 0.0)
        confidence = float(raw.get("confidence") or raw.get("coarse_confidence") or 0.0)
        reason = str(raw.get("reason") or raw.get("label") or f"candidate_{index}")
        source = str(raw.get("source") or "locator")
        debug = dict(raw.get("debug") or {})
        candidates.append(
            VideoWindow(
                start_s=_clamp(start_s, 0.0, duration_s),
                end_s=_clamp(end_s, 0.0, duration_s),
                contact_time_s=float(contact_time_s) if contact_time_s is not None else None,
                peak_time_s=float(peak_time_s) if peak_time_s is not None else None,
                score=float(score),
                confidence=float(confidence),
                source=source,
                reason=reason,
                debug=debug,
            )
        )

    candidates.sort(key=lambda item: (-float(item.score), float(item.start_s), float(item.end_s)))
    selected: List[VideoWindow] = []
    for candidate in candidates:
        overlaps = False
        for chosen in selected:
            if candidate.end_s + min_gap_s <= chosen.start_s:
                continue
            if chosen.end_s + min_gap_s <= candidate.start_s:
                continue
            overlaps = True
            break
        if overlaps:
            continue
        selected.append(candidate)
        if len(selected) >= max_windows:
            break
    return selected


def expand_locator_windows(
    candidate_windows: Sequence[Dict[str, Any]],
    *,
    duration_s: float,
    fps: float,
    pre_buffer_s: float = 1.5,
    post_buffer_s: float = 2.5,
    min_duration_s: float = 4.0,
    max_duration_s: float = 6.0,
    max_windows: int = 3,
) -> List[Dict[str, Any]]:
    normalized = normalize_candidate_windows(candidate_windows, duration_s=duration_s, max_windows=max_windows)
    final_windows: List[Dict[str, Any]] = []
    for index, candidate in enumerate(normalized):
        center = candidate.contact_time_s if candidate.contact_time_s is not None else candidate.peak_time_s
        start_s, end_s = build_window_from_contact(
            center,
            duration_s=duration_s,
            peak_time_s=candidate.peak_time_s,
            pre_buffer_s=pre_buffer_s,
            post_buffer_s=post_buffer_s,
            min_duration_s=min_duration_s,
            max_duration_s=max_duration_s,
        )
        start_frame = int(round(start_s * fps)) if fps > 0.0 else 0
        end_frame = int(round(end_s * fps)) if fps > 0.0 else 0
        final_windows.append(
            {
                "index": index,
                "start_s": round(float(start_s), 3),
                "end_s": round(float(end_s), 3),
                "duration_s": round(float(max(0.0, end_s - start_s)), 3),
                "contact_time_s": round(float(candidate.contact_time_s), 3) if candidate.contact_time_s is not None else None,
                "peak_time_s": round(float(candidate.peak_time_s), 3) if candidate.peak_time_s is not None else None,
                "score": round(float(candidate.score), 3),
                "confidence": round(float(candidate.confidence), 3),
                "source": candidate.source,
                "reason": candidate.reason,
                "frame_range": [start_frame, end_frame],
                "debug": dict(candidate.debug),
            }
        )
    return final_windows

