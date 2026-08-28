from dataclasses import dataclass
from typing import Dict, List

from analysis.score_levels import score_level_from_overall


@dataclass(frozen=True)
class FootballIssue:
    code: str
    label: str
    severity: float
    summary: str
    cue: str


@dataclass(frozen=True)
class FootballActionQualityScore:
    template_code: str
    template_label: str
    score_name: str
    score_definition: str
    overall_score: float
    technical_execution_score: float
    control_stability_score: float
    action_safety_score: float
    level_code: str
    level_label: str
    key_issues: List[FootballIssue]
    one_line_summary: str
    core_problem: str
    next_step_advice: str
    positive_feedback: str
    phase_scores: Dict[str, float]


_TEMPLATES = {
    "passing_stability": {
        "label": "Passing Stability / 传球稳定性",
        "score_name": "Passing Quality Score / 传球动作质量分",
        "definition": "Measures how cleanly and consistently the current pass is executed, with risk screening kept separate from the main quality score. / 评估当前这一次传球动作完成得有多稳定、多清晰，风险筛查单独呈现，不混入主质量分。",
        "expected_actions": {"pass_like", "pass", "long_ball", "soccer_idle"},
        "ball_release_band": (0.10, 0.34, 0.02, 0.70),
        "support_band": (0.16, 0.32, 0.04, 0.60),
        "swing_band": (0.05, 0.18, 0.00, 0.40),
        "tech_weights": {"preparation": 0.18, "support": 0.30, "contact": 0.34, "follow_through": 0.18},
    },
    "shooting_quality": {
        "label": "Shooting Quality / 射门动作质量",
        "score_name": "Shooting Quality Score / 射门动作质量分",
        "definition": "Measures how effectively the body organizes the shot through setup, strike, and follow-through. / 评估射门在准备、发力、触球和随挥阶段的整体完成质量。",
        "expected_actions": {"shoot_like", "shot", "clearance", "jump_like", "soccer_idle"},
        "ball_release_band": (0.18, 0.52, 0.04, 0.90),
        "support_band": (0.18, 0.34, 0.06, 0.64),
        "swing_band": (0.06, 0.22, 0.00, 0.48),
        "tech_weights": {"preparation": 0.14, "support": 0.22, "contact": 0.38, "follow_through": 0.26},
    },
    "first_touch_control": {
        "label": "First-Touch Control / 停球控制",
        "score_name": "First-Touch Control Score / 停球控制分",
        "definition": "Measures whether the first touch is organized, controlled, and recoverable for the next action. / 评估停球动作是否具备良好的准备姿态、触球控制和后续衔接能力。",
        "expected_actions": {"pass_like", "first_touch", "first_touch_like", "soccer_idle"},
        "ball_release_band": (0.03, 0.18, 0.00, 0.50),
        "support_band": (0.14, 0.30, 0.04, 0.56),
        "swing_band": (0.02, 0.14, 0.00, 0.34),
        "tech_weights": {"preparation": 0.24, "support": 0.26, "contact": 0.34, "follow_through": 0.16},
    },
}


def get_template_catalog() -> List[Dict[str, str]]:
    return [
        {"code": code, "label": cfg["label"], "score_name": cfg["score_name"]}
        for code, cfg in _TEMPLATES.items()
    ]


def get_template_meta(template_code: str) -> Dict[str, str]:
    return _TEMPLATES.get(template_code, _TEMPLATES["passing_stability"])


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _ideal_band_score(value: float, ideal_low: float, ideal_high: float, worst_low: float, worst_high: float) -> float:
    value = float(value)
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        if value <= worst_low:
            return 0.0
        return (value - worst_low) / max(1e-6, ideal_low - worst_low)
    if value >= worst_high:
        return 0.0
    return (worst_high - value) / max(1e-6, worst_high - ideal_high)


def _issue_copy(code: str, severity: float, summary: str, cue: str) -> FootballIssue:
    labels = {
        "support_foot_spacing": "Support-foot spacing is off / 支撑脚距离不合适",
        "body_alignment": "Body alignment is unstable / 身体对线不稳定",
        "contact_quality": "Contact quality is weak / 触球质量不足",
        "follow_through": "Follow-through is incomplete / 随挥完成度不足",
        "balance_control": "Balance control is unstable / 平衡控制不稳定",
        "action_pattern_unclear": "Target action pattern is not clear / 目标动作模式不清晰",
        "stable_action": "Action quality is stable / 动作完成质量稳定",
    }
    return FootballIssue(
        code=code,
        label=labels[code],
        severity=_clamp(severity, 0.0, 1.0),
        summary=summary,
        cue=cue,
    )


def _build_issue_candidates(template_code: str, metrics: Dict[str, float], phase_scores: Dict[str, float], action_label: str) -> List[FootballIssue]:
    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28))
    trunk_lean_deg = float(metrics.get("trunk_lean_deg", 0.0))
    valgus_ratio = float(metrics.get("valgus_ratio", 1.0))
    symmetry = float(metrics.get("symmetry", 0.0))
    balance = float(metrics.get("balance", 0.0))
    ball_contact = float(metrics.get("ball_contact", 0.0))
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.0))
    stability = float(metrics.get("stability", 0.0))

    issues: List[FootballIssue] = []

    if support_ball_ratio < 0.16:
        issues.append(
            _issue_copy(
                "support_foot_spacing",
                (0.16 - support_ball_ratio) / 0.12,
                "The support foot lands too close to the ball, so the kicking path gets crowded before contact. / 支撑脚离球过近，导致摆腿空间不足。",
                "Move the support foot slightly farther from the ball and keep the toe line facing the target. / 支撑脚适当远离球，并让脚尖朝向目标。",
            )
        )
    elif support_ball_ratio > 0.34:
        issues.append(
            _issue_copy(
                "support_foot_spacing",
                (support_ball_ratio - 0.34) / 0.20,
                "The support foot lands too far from the ball, which weakens force transfer and directional control. / 支撑脚离球过远，影响出球方向和力量传递。",
                "Tighten the plant distance so the body can transfer force more directly into the ball. / 收紧支撑脚落位，让力量更直接传到球上。",
            )
        )

    if trunk_lean_deg > 12.0 or balance > 0.15:
        issues.append(
            _issue_copy(
                "body_alignment",
                max((trunk_lean_deg - 12.0) / 14.0, (balance - 0.15) / 0.25),
                "The torso and pelvis do not stay aligned enough through the action, so the body loses direction and structure. / 动作中躯干和骨盆对线不足，影响动作方向和整体结构。",
                "Quiet the chest and pelvis through the strike so the body stays aligned toward the target. / 发力和触球时让胸廓与骨盆更稳定，保持身体朝向目标。",
            )
        )

    if phase_scores["contact"] < 62.0 or ball_contact < 0.5:
        issues.append(
            _issue_copy(
                "contact_quality",
                max((62.0 - phase_scores["contact"]) / 28.0, 0.4 if ball_contact < 0.5 else 0.0),
                "The decisive contact moment is not clean enough, so the action loses quality where it matters most. / 决定动作质量的触球瞬间不够干净，关键输出环节失分明显。",
                "Stabilize the plant side first, then let the striking leg accelerate into a cleaner contact. / 先稳住支撑侧，再让摆腿更干净地完成触球。",
            )
        )

    if phase_scores["follow_through"] < 60.0 or (template_code != "first_touch_control" and ball_speed_ratio < 0.10):
        issues.append(
            _issue_copy(
                "follow_through",
                max((60.0 - phase_scores["follow_through"]) / 24.0, 0.0 if template_code == "first_touch_control" else (0.10 - ball_speed_ratio) / 0.08),
                "The action does not finish smoothly after contact, so the technique looks unfinished and less repeatable. / 触球后的动作收尾不够自然，导致整体完成度和可重复性不足。",
                "Finish the swing or recovery path fully instead of stopping right around contact. / 不要在触球附近停住，完整做完摆腿或回收动作。",
            )
        )

    if stability < 0.58 or symmetry > 10.0 or valgus_ratio < 0.88:
        issues.append(
            _issue_copy(
                "balance_control",
                max((0.58 - stability) / 0.28, (symmetry - 10.0) / 12.0, (0.88 - valgus_ratio) / 0.18),
                "The action loses balance or left-right control, which reduces repeatable technique quality. / 动作中的平衡或左右控制下降，影响专项动作的一致性。",
                "Keep the support side quieter and reduce left-right drift before trying to add speed. / 先稳住支撑侧，减少左右晃动，再考虑继续提速。",
            )
        )

    expected = _TEMPLATES[template_code]["expected_actions"]
    if action_label not in expected:
        issues.append(
            _issue_copy(
                "action_pattern_unclear",
                0.45,
                "The current sequence does not strongly match the intended training template, so the score should be read as provisional. / 当前动作与目标训练模板匹配度不高，因此本次评分应视为参考结果。",
                "Repeat the target action more clearly so the scoring template can evaluate the intended technique. / 让目标动作更明确，系统才能按对应专项模板给出更稳定的评分。",
            )
        )

    if not issues:
        issues.append(
            _issue_copy(
                "stable_action",
                0.12,
                "The current football action is mechanically stable for the chosen training goal. / 当前动作在所选训练目标下整体完成较稳定。",
                "Keep the same rhythm and only increase speed after the structure stays repeatable. / 保持当前节奏，等动作结构稳定后再增加速度。",
            )
        )

    issues.sort(key=lambda item: item.severity, reverse=True)
    return issues[:3]


def score_football_action(metrics: Dict[str, float], action_label: str, template_code: str = "passing_stability") -> FootballActionQualityScore:
    template = _TEMPLATES.get(template_code, _TEMPLATES["passing_stability"])
    normalized_action_label = {
        "pass": "pass_like",
        "shot": "shoot_like",
        "first_touch": "first_touch_like",
        "clearance": "shoot_like",
        "long_ball": "pass_like",
    }.get(str(action_label or "").strip(), str(action_label or "").strip())

    balance = float(metrics.get("balance", 0.0))
    trunk_lean_deg = float(metrics.get("trunk_lean_deg", 0.0))
    valgus_ratio = float(metrics.get("valgus_ratio", 1.0))
    symmetry = float(metrics.get("symmetry", 0.0))
    stability = float(metrics.get("stability", 0.0))
    support_ball_ratio = float(metrics.get("support_ball_ratio", 0.28))
    swing_ball_ratio = float(metrics.get("swing_ball_ratio", 0.16))
    ball_speed_ratio = float(metrics.get("ball_speed_ratio", 0.12))
    ball_contact = float(metrics.get("ball_contact", 0.0))
    visibility = float(metrics.get("visibility", 0.0))
    sequence_confidence = float(metrics.get("sequence_confidence", 0.0))
    phase_locked = float(metrics.get("phase_locked", 0.0))

    preparation_alignment = _ideal_band_score(balance, 0.0, 0.12, 0.0, 0.48)
    preparation_posture = _ideal_band_score(trunk_lean_deg, 0.0, 10.0, 0.0, 28.0)
    preparation_score = 100.0 * (0.55 * preparation_alignment + 0.45 * preparation_posture)

    support_spacing = _ideal_band_score(support_ball_ratio, *template["support_band"])
    support_control = _ideal_band_score(valgus_ratio, 0.90, 1.10, 0.72, 1.35)
    support_score = 100.0 * (0.62 * support_spacing + 0.38 * support_control)

    contact_body = _ideal_band_score(trunk_lean_deg, 0.0, 9.0, 0.0, 26.0)
    contact_alignment = _ideal_band_score(valgus_ratio, 0.92, 1.08, 0.72, 1.30)
    contact_certainty = _clamp(0.48 + 0.28 * sequence_confidence + 0.24 * (1.0 if ball_contact > 0.5 else 0.0), 0.0, 1.0)
    contact_score = 100.0 * (0.35 * contact_body + 0.40 * contact_alignment + 0.25 * contact_certainty)

    follow_path = _ideal_band_score(swing_ball_ratio, *template["swing_band"])
    follow_release = _ideal_band_score(ball_speed_ratio, *template["ball_release_band"])
    follow_control = _ideal_band_score(stability, 0.62, 1.0, 0.22, 1.0)
    follow_sequence = _ideal_band_score(sequence_confidence, 0.62, 1.0, 0.18, 1.0)
    follow_score = 100.0 * (0.28 * follow_path + 0.30 * follow_release + 0.24 * follow_control + 0.18 * follow_sequence)

    technical_execution_score = 0.0
    tech_weights = template["tech_weights"]
    technical_execution_score = (
        tech_weights["preparation"] * preparation_score
        + tech_weights["support"] * support_score
        + tech_weights["contact"] * contact_score
        + tech_weights["follow_through"] * follow_score
    )

    symmetry_control = _ideal_band_score(symmetry, 0.0, 8.0, 0.0, 24.0)
    stability_control = _ideal_band_score(stability, 0.64, 1.0, 0.20, 1.0)
    balance_control = _ideal_band_score(balance, 0.0, 0.12, 0.0, 0.45)
    phase_control = _ideal_band_score(sequence_confidence, 0.62, 1.0, 0.18, 1.0)
    control_stability_score = 100.0 * (
        0.28 * balance_control
        + 0.26 * stability_control
        + 0.22 * symmetry_control
        + 0.24 * (0.55 * phase_control + 0.45 * phase_locked)
    )

    knee_safety = _ideal_band_score(valgus_ratio, 0.92, 1.08, 0.72, 1.30)
    trunk_safety = _ideal_band_score(trunk_lean_deg, 0.0, 10.0, 0.0, 30.0)
    visibility_safety = _ideal_band_score(visibility, 0.78, 1.0, 0.40, 1.0)
    action_safety_score = 100.0 * (0.44 * knee_safety + 0.34 * trunk_safety + 0.22 * visibility_safety)

    if action_label not in template["expected_actions"]:
        technical_execution_score *= 0.90

    overall_score = (
        0.50 * technical_execution_score
        + 0.30 * control_stability_score
        + 0.20 * action_safety_score
    )

    overall_score = _clamp(overall_score, 0.0, 100.0)
    technical_execution_score = _clamp(technical_execution_score, 0.0, 100.0)
    control_stability_score = _clamp(control_stability_score, 0.0, 100.0)
    action_safety_score = _clamp(action_safety_score, 0.0, 100.0)

    phase_scores = {
        "preparation": _clamp(preparation_score, 0.0, 100.0),
        "support": _clamp(support_score, 0.0, 100.0),
        "contact": _clamp(contact_score, 0.0, 100.0),
        "follow_through": _clamp(follow_score, 0.0, 100.0),
    }

    level_code, level_label = score_level_from_overall(overall_score)

    issues = _build_issue_candidates(template_code, metrics, phase_scores, normalized_action_label)
    primary_issue = issues[0]

    if overall_score >= 90.0:
        one_line_summary = (
            f"{template['label']} is excellent at {overall_score:.0f}/100, with one optimization focus on {primary_issue.label.lower().split(' / ')[0]}. "
            f"/ 当前{template['label'].split(' / ')[1]}为 {overall_score:.0f}/100，完成度很高，当前可继续保持的重点是{primary_issue.label.split(' / ')[1]}。"
        )
    elif overall_score >= 75.0:
        one_line_summary = (
            f"{template['label']} is good at {overall_score:.0f}/100, with one optimization focus on {primary_issue.label.lower().split(' / ')[0]}. "
            f"/ 当前{template['label'].split(' / ')[1]}为 {overall_score:.0f}/100，整体表现良好，仍需优化{primary_issue.label.split(' / ')[1]}。"
        )
    elif overall_score >= 60.0:
        one_line_summary = (
            f"{template['label']} is moderate at {overall_score:.0f}/100, mainly limited by {primary_issue.label.lower().split(' / ')[0]}. "
            f"/ 当前{template['label'].split(' / ')[1]}为 {overall_score:.0f}/100，当前主要问题是{primary_issue.label.split(' / ')[1]}。"
        )
    elif overall_score >= 40.0:
        one_line_summary = (
            f"{template['label']} needs improvement at {overall_score:.0f}/100, mainly limited by {primary_issue.label.lower().split(' / ')[0]}. "
            f"/ 当前{template['label'].split(' / ')[1]}为 {overall_score:.0f}/100，仍有待提高，当前主要问题是{primary_issue.label.split(' / ')[1]}，建议先把这个环节稳定下来。"
        )
    else:
        one_line_summary = (
            f"{template['label']} needs strengthening at {overall_score:.0f}/100, mainly limited by {primary_issue.label.lower().split(' / ')[0]}. "
            f"/ 当前{template['label'].split(' / ')[1]}为 {overall_score:.0f}/100，仍需加强，当前主要问题是{primary_issue.label.split(' / ')[1]}，建议优先纠正。"
        )

    positive_feedback = (
        "The motion pattern is visible and usable for coaching. / 当前动作模式已经清晰，具备继续教练化训练的基础。"
        if primary_issue.code != "stable_action"
        else "The action already shows stable football-specific structure. / 当前动作已经展现出较稳定的足球专项结构。"
    )

    return FootballActionQualityScore(
        template_code=template_code,
        template_label=template["label"],
        score_name=template["score_name"],
        score_definition=template["definition"],
        overall_score=overall_score,
        technical_execution_score=technical_execution_score,
        control_stability_score=control_stability_score,
        action_safety_score=action_safety_score,
        level_code=level_code,
        level_label=level_label,
        key_issues=issues,
        one_line_summary=one_line_summary,
        core_problem=primary_issue.summary,
        next_step_advice=primary_issue.cue,
        positive_feedback=positive_feedback,
        phase_scores=phase_scores,
    )
