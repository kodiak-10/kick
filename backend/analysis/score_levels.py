from __future__ import annotations

from typing import Tuple


def score_level_from_overall(overall_score: float) -> Tuple[str, str]:
    score = float(overall_score or 0.0)
    if score >= 90.0:
        return "excellent", "优秀"
    if score >= 75.0:
        return "good", "良好"
    if score >= 60.0:
        return "fair", "一般"
    if score >= 40.0:
        return "needs_improve", "待提高"
    return "needs_strengthen", "需加强"
