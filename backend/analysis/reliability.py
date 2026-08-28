from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReliabilityReport:
    overall: float
    pose: float
    ball: float
    stage: float
    environment: float
    should_score: bool
    gate_reason: str
    user_message: str


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def evaluate_reliability(
    *,
    visibility: float,
    lock_score: float,
    full_body: bool,
    target_locked: bool,
    body_fill_ratio: float,
    brightness: float,
    switch_risk: float,
    appearance_score: float = 1.0,
    ball_confidence: float,
    ball_detected: bool,
    phase_confidence: float,
    phase_locked: bool,
    sequence_ready: bool,
) -> ReliabilityReport:
    pose_score = _clamp(
        0.42 * visibility
        + 0.36 * lock_score
        + 0.22 * _clamp((body_fill_ratio - 0.28) / 0.30)
    )
    if not full_body or not target_locked:
        pose_score *= 0.55

    ball_score = _clamp(ball_confidence * (1.0 if ball_detected else 0.72))
    stage_score = _clamp(
        0.45 * phase_confidence
        + 0.25 * (1.0 if phase_locked else 0.0)
        + 0.30 * (1.0 if sequence_ready else 0.0)
    )
    brightness_score = _clamp((brightness - 18.0) / 70.0)
    environment_score = _clamp(
        0.46 * (1.0 - switch_risk) + 0.28 * brightness_score + 0.26 * _clamp(appearance_score)
    )

    overall = _clamp(
        0.34 * pose_score
        + 0.22 * ball_score
        + 0.28 * stage_score
        + 0.16 * environment_score
    )

    should_score = (
        full_body
        and target_locked
        and pose_score >= 0.58
        and stage_score >= 0.54
        and environment_score >= 0.46
        and overall >= 0.58
        and ball_score >= 0.30
    )

    if not full_body or pose_score < 0.45:
        gate_reason = "pose_unstable"
        user_message = "Body capture is not reliable enough yet. / 当前人体捕捉质量不足，系统暂不输出可信评分。"
    elif not target_locked or environment_score < 0.46:
        gate_reason = "target_unstable"
        user_message = "Primary athlete lock is still unstable. / 当前主目标仍不稳定，系统暂不输出确定性结论。"
    elif ball_score < 0.30:
        gate_reason = "ball_unstable"
        user_message = "Ball tracking is not stable enough for a football-grade score. / 当前足球跟踪不稳定，系统暂不输出足球专项评分。"
    elif stage_score < 0.54:
        gate_reason = "phase_unlocked"
        user_message = "The action phase is not locked yet. / 当前动作阶段尚未锁定，系统暂不输出最终评分。"
    elif not should_score:
        gate_reason = "analysis_provisional"
        user_message = "The evidence is still provisional, so the score is withheld. / 当前证据仍属参考级，系统暂不输出最终分数。"
    else:
        gate_reason = "ready"
        user_message = "Analysis confidence is sufficient for scoring. / 当前识别置信度足以支持专项评分。"

    return ReliabilityReport(
        overall=overall,
        pose=pose_score,
        ball=ball_score,
        stage=stage_score,
        environment=environment_score,
        should_score=should_score,
        gate_reason=gate_reason,
        user_message=user_message,
    )
