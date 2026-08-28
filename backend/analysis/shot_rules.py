from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ShotIssue:
    id: str
    title: str
    phase: str
    time: float
    short_hint: str
    explanation: str
    fix_advice: str
    training_advice: str
    severity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "phase": self.phase,
            "time": round(float(self.time), 3),
            "short_hint": self.short_hint,
            "explanation": self.explanation,
            "fix_advice": self.fix_advice,
            "training_advice": self.training_advice,
            "severity": round(float(self.severity), 3),
        }


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _cn(text: str) -> str:
    if not text:
        return text
    if " / " in text:
        return text.split(" / ", 1)[1].strip()
    return text


def _field_value(issue: Any, attr: str, default: Any = None) -> Any:
    if hasattr(issue, attr):
        return getattr(issue, attr)
    if isinstance(issue, dict):
        return issue.get(attr, default)
    return default


def _phase_for_code(code: str) -> str:
    return {
        "support_foot_spacing": "support",
        "support_foot_too_far": "support",
        "support_foot_too_close": "support",
        "body_alignment": "contact",
        "upper_body_back_lean": "contact",
        "contact_quality": "contact",
        "follow_through": "follow_through",
        "follow_through_incomplete": "follow_through",
        "balance_control": "support",
        "action_pattern_unclear": "setup",
        "stable_action": "follow_through",
        "capture_quality_low": "setup",
    }.get(code, "contact")


def _training_advice_for_code(code: str) -> str:
    return {
        "support_foot_spacing": "做固定球位支撑落点练习，每组 8-10 次，先把脚印位置标出来，再逐步加速。",
        "support_foot_too_far": "做固定球位支撑落点练习，每组 8-10 次，先把脚印位置标出来，再逐步加速。",
        "support_foot_too_close": "做原地定点摆腿练习，每组 8 次，重点感受脚到球之间的稳定间距。",
        "body_alignment": "做核心收紧和髋胸对齐分解练习，每组 6-8 次，先稳住上体再发力。",
        "upper_body_back_lean": "做靠墙摆腿或定点射门分解，每组 6-8 次，先练上体稳定再追求发力。",
        "contact_quality": "固定球位反复练脚背触球，每组 6-8 次，先把触球区域做稳定。",
        "follow_through": "做连续射门和延迟回收练习，每组 6-8 球，刻意把收尾动作做完整。",
        "follow_through_incomplete": "做连续射门和延迟回收练习，每组 6-8 球，刻意把收尾动作做完整。",
        "balance_control": "做单脚稳定和慢速射门分解，每组 6 次，先稳住支撑侧再提速。",
        "action_pattern_unclear": "先把动作分解清楚，再完整连贯执行，每组 5-6 次，保持节奏一致。",
        "stable_action": "用同一球位重复练 6-8 次，先保持一致性，再逐步增加速度。",
        "capture_quality_low": "先固定机位补拍 3-5 条全身入镜的视频，再做技术判断。",
    }.get(code, "先把动作放慢，重复做几次完整动作，再逐步提速。")


def _capture_issue(*, pose_frames: int, ball_frames: int, total_frames: int, analysis_confidence: float) -> ShotIssue:
    evidence_text = f"本次视频里只有 {pose_frames}/{total_frames} 帧姿态证据和 {ball_frames}/{total_frames} 帧球证据，分析会比较保守。"
    severity = _clamp(1.0 - float(analysis_confidence), 0.2, 1.0)
    return ShotIssue(
        id="capture_quality_low",
        title="视频证据不足",
        phase="setup",
        time=0.0,
        short_hint="请补拍全身清晰射门视频",
        explanation=evidence_text,
        fix_advice="尽量保证全身入镜，并让球、支撑脚和触球瞬间都清楚可见。",
        training_advice=_training_advice_for_code("capture_quality_low"),
        severity=severity,
    )


def _stable_issue(time_s: float) -> ShotIssue:
    return ShotIssue(
        id="stable_action",
        title="动作整体稳定",
        phase="follow_through",
        time=time_s,
        short_hint="保持当前节奏，先稳住再提速",
        explanation="当前射门结构整体稳定，没有看到特别突出的关键失误。",
        fix_advice="继续保持支撑、躯干和摆腿的协同节奏。",
        training_advice=_training_advice_for_code("stable_action"),
        severity=0.12,
    )


def _support_issue(support_ball_ratio: float, time_s: float, ball_evidence: bool) -> Optional[ShotIssue]:
    if not ball_evidence:
        return None

    if support_ball_ratio > 0.34:
        severity = _clamp((support_ball_ratio - 0.34) / 0.20)
        return ShotIssue(
            id="support_foot_too_far",
            title="支撑脚落点偏远",
            phase="support",
            time=time_s,
            short_hint="支撑脚再靠近球侧后方一点",
            explanation="支撑脚离球过远会拉长发力路径，力量更难直接传到球上，击球方向也更容易发飘。",
            fix_advice="落脚时把支撑脚收近到球侧后方半步，脚尖朝向目标，触球前先稳住支撑腿。",
            training_advice=_training_advice_for_code("support_foot_too_far"),
            severity=severity,
        )

    if support_ball_ratio < 0.16:
        severity = _clamp((0.16 - support_ball_ratio) / 0.12)
        return ShotIssue(
            id="support_foot_too_close",
            title="支撑脚落点偏近",
            phase="support",
            time=time_s,
            short_hint="支撑脚再离球远一点",
            explanation="支撑脚离球过近会挤压摆腿空间，容易影响击球角度和发力顺畅度。",
            fix_advice="把支撑脚向球侧外移一点，给摆腿留出更完整的通道。",
            training_advice=_training_advice_for_code("support_foot_too_close"),
            severity=severity,
        )

    return None


def _trunk_issue(trunk_lean_deg: float, balance: float, time_s: float) -> Optional[ShotIssue]:
    severity = max(_clamp((trunk_lean_deg - 15.0) / 12.0), _clamp((balance - 0.16) / 0.24))
    if severity < 0.15:
        return None
    return ShotIssue(
        id="upper_body_back_lean",
        title="上体后仰明显",
        phase="contact",
        time=time_s,
        short_hint="触球前把胸口稳住，别向后倒",
        explanation="上体后仰过大时，重心容易落在球后方，力量传导会变散，射门更容易抬高或打飘。",
        fix_advice="进入触球时让胸口略压向球，保持髋胸整体朝向目标，不要提前仰身。",
        training_advice=_training_advice_for_code("upper_body_back_lean"),
        severity=severity,
    )


def _follow_issue(follow_through_score: float, ball_speed_ratio: float, time_s: float) -> Optional[ShotIssue]:
    severity = max(
        _clamp((60.0 - follow_through_score) / 24.0),
        _clamp((0.10 - ball_speed_ratio) / 0.08),
    )
    if severity < 0.15:
        return None
    return ShotIssue(
        id="follow_through_incomplete",
        title="随摆不完整",
        phase="follow_through",
        time=time_s,
        short_hint="触球后把摆腿继续送出去",
        explanation="随摆太早刹车会让发力链条在触球后突然中断，球速和方向稳定性都会受影响。",
        fix_advice="触球后继续朝目标方向送腿和送髋，不要在碰球瞬间急停。",
        training_advice=_training_advice_for_code("follow_through_incomplete"),
        severity=severity,
    )


def _convert_scoring_issue(issue: Any, time_s: float) -> ShotIssue:
    code = _field_value(issue, "code", "action_pattern_unclear")
    label = _field_value(issue, "label", str(code))
    summary = _field_value(issue, "summary", "")
    cue = _field_value(issue, "cue", "")
    severity = float(_field_value(issue, "severity", 0.0) or 0.0)

    return ShotIssue(
        id=str(code or "action_pattern_unclear"),
        title=_cn(str(label or code or "动作问题")),
        phase=_phase_for_code(str(code or "")),
        time=time_s,
        short_hint=_cn(str(cue or "")) or "先把动作节奏放慢一点",
        explanation=_cn(str(summary or "")) or "当前视频的规则结果提示动作还需要进一步整理。",
        fix_advice=_cn(str(cue or "")) or "先把动作结构做完整，再考虑提速。",
        training_advice=_training_advice_for_code(str(code or "action_pattern_unclear")),
        severity=_clamp(severity),
    )


def build_shot_issues(
    *,
    metrics: Dict[str, float],
    phase_scores: Dict[str, float],
    evidence: Dict[str, float],
    event_times: Dict[str, float],
    issue_times: Optional[Dict[str, float]] = None,
    fallback_issue: Optional[Any] = None,
) -> List[ShotIssue]:
    issue_times = issue_times or {}
    pose_frames = int(evidence.get("pose_frames", 0))
    ball_frames = int(evidence.get("ball_frames", 0))
    total_frames = int(evidence.get("total_frames", 0))
    analysis_confidence = float(evidence.get("analysis_confidence", 0.0))

    if pose_frames < 4 or ball_frames < 1 or total_frames < 1:
        return [
            _capture_issue(
                pose_frames=pose_frames,
                ball_frames=ball_frames,
                total_frames=max(1, total_frames),
                analysis_confidence=analysis_confidence,
            )
        ]

    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28))
    trunk_lean_deg = float(metrics.get("trunk_lean_deg", 0.0))
    balance = float(metrics.get("balance", 0.0))
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.0))
    follow_through_score = float(phase_scores.get("follow_through", 0.0))
    ball_evidence = ball_frames >= 2

    issues: List[ShotIssue] = []

    support_time = float(
        issue_times.get(
            "support_foot_too_far" if support_ball_ratio > 0.34 else "support_foot_too_close",
            event_times.get("support", 0.0),
        )
    )
    support = _support_issue(support_ball_ratio, support_time, ball_evidence)
    if support is not None:
        issues.append(support)

    trunk = _trunk_issue(trunk_lean_deg, balance, float(issue_times.get("upper_body_back_lean", event_times.get("contact", 0.0))))
    if trunk is not None:
        issues.append(trunk)

    follow = _follow_issue(
        follow_through_score,
        ball_speed_ratio,
        float(issue_times.get("follow_through_incomplete", event_times.get("follow_through", event_times.get("contact", 0.0)))),
    )
    if follow is not None:
        issues.append(follow)

    if not issues and fallback_issue is not None:
        fallback_code = str(_field_value(fallback_issue, "code", "action_pattern_unclear"))
        fallback_time = float(issue_times.get(fallback_code, event_times.get("contact", 0.0)))
        issues.append(_convert_scoring_issue(fallback_issue, fallback_time))

    if not issues:
        stable_time = float(issue_times.get("stable_action", event_times.get("contact", 0.0)))
        issues.append(_stable_issue(stable_time))

    issues.sort(key=lambda item: item.severity, reverse=True)
    return issues[:3]
