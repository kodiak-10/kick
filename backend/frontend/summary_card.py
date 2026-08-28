#!/usr/bin/env python3
import argparse
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None

PRIMARY = (145, 61, 11)
WARNING = (0, 140, 255)
TEXT = (240, 240, 240)
MUTED = (182, 182, 182)

_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

_LABEL_ZH = {
    "ready": "准备就绪",
    "awaiting_start": "等待开始",
    "full_body_required": "需要全身入镜",
    "target_locking": "正在锁定主目标",
    "target_lost": "主目标重新获取中",
    "locked": "已锁定",
    "no_pose": "未检测到姿态",
    "shoot_like": "射门动作",
    "pass_like": "传球动作",
    "shot_instep": "射门",
    "short_pass": "短传",
    "receive_control": "接球",
    "pass_receive_sequence": "传接球序列",
    "pass_receive_sequence_like": "传接球序列",
    "dribble_change_direction": "带球变向",
    "juggling": "颠球",
    "jump_like": "跳跃动作",
    "soccer_idle": "足球待机",
    "squat": "深蹲",
    "pushup": "俯卧撑",
    "capture_quality_low": "采集质量低",
    "knee_valgus_risk": "膝内扣风险",
    "trunk_control_risk": "躯干控制风险",
    "asymmetry_risk": "左右不对称风险",
    "support_foot_too_close": "支撑脚离球过近",
    "support_foot_too_far": "支撑脚离球过远",
    "contact_posture_unstable": "触球姿态不稳定",
    "knee_alignment_loss": "触球时膝线控制下降",
    "strike_through_insufficient": "摆腿完成度不足",
    "follow_through_unstable": "随挥后的身体控制不稳定",
    "stable_passing": "传球动作整体稳定",
    "stable_motion": "动作稳定",
    "set": "准备阶段",
    "approach": "接近阶段",
    "strike_swing": "摆腿阶段",
    "contact": "触球阶段",
    "follow_through": "随挥阶段",
    "airborne": "腾空阶段",
    "ready_to_score": "准备正式评分",
    "insufficient_evidence": "证据不足",
    "quality_fail": "质量未达标",
    "left": "左侧",
    "right": "右侧",
    "none": "无",
    "detected": "检测到",
    "predicted": "预测保持",
    "lost": "丢失",
}


def _to_rgb(bgr):
    return int(bgr[2]), int(bgr[1]), int(bgr[0])


def _from_rgb(rgb):
    return int(rgb[2]), int(rgb[1]), int(rgb[0])


@lru_cache(maxsize=128)
def _load_font(size):
    if ImageFont is None:
        return None
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


@lru_cache(maxsize=2048)
def _measure_text(text, size):
    if ImageFont is None or ImageDraw is None or Image is None:
        return int(len(text) * size * 0.56)
    font = _load_font(size)
    tmp = Image.new("RGB", (10, 10), (0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return max(0, box[2] - box[0])
    except Exception:
        return int(len(text) * size * 0.56)


def _wrap_text(text, max_width, size):
    if not text:
        return [""]
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if _measure_text(cand, size) <= max_width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def _make_text_ctx(img):
    if Image is None or ImageDraw is None:
        return None
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return {"pil_img": pil_img, "draw": ImageDraw.Draw(pil_img)}


def _flush_text_ctx(img, ctx):
    if ctx is None:
        return
    img[:] = cv2.cvtColor(np.array(ctx["pil_img"]), cv2.COLOR_RGB2BGR)


def _draw_text(img, text, org, size=20, color=(255, 255, 255), shadow=True, ctx=None):
    if not text:
        return
    if ctx is None and (Image is None or ImageDraw is None):
        scale = max(0.45, size / 34.0)
        if shadow:
            cv2.putText(img, text, (org[0] + 1, org[1] + 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (10, 10, 10), 2, cv2.LINE_AA)
        cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
        return

    if ctx is None:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
    else:
        pil_img = ctx["pil_img"]
        draw = ctx["draw"]
    font = _load_font(size)
    if shadow:
        draw.text((org[0] + 1, org[1] + 1), text, fill=(16, 16, 16), font=font)
    draw.text(org, text, fill=_to_rgb(color), font=font)
    if ctx is None:
        img[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _blend_box(img, x, y, w, h, color=(18, 18, 18), alpha=0.58, border=(80, 80, 80)):
    x = max(0, x)
    y = max(0, y)
    w = max(1, w)
    h = max(1, h)
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    cv2.rectangle(img, (x, y), (x + w, y + h), border, 1, cv2.LINE_AA)


def _severity_color(v):
    v = max(0.0, min(1.0, float(v)))
    if v < 0.35:
        return (72, 186, 92)
    if v < 0.65:
        return (54, 188, 222)
    return WARNING


def _draw_bar(img, x, y, w, h, val):
    cv2.rectangle(img, (x, y), (x + w, y + h), (74, 74, 74), 1)
    fill = int(w * max(0.0, min(1.0, val)))
    if fill > 0:
        cv2.rectangle(img, (x, y), (x + fill, y + h), _severity_color(val), -1)


def _draw_heatmap_timeline(img, values, x, y, w, h, title_size, ctx=None):
    _blend_box(img, x, y, w, h, alpha=0.52)
    _draw_text(img, "Severity Timeline / 严重度时间轴", (x + 12, y + 8), size=title_size, color=MUTED, ctx=ctx)
    if not values:
        _draw_text(img, "no data", (x + 12, y + 32), size=max(14, title_size - 2), color=MUTED, ctx=ctx)
        return
    arr = np.array(values, dtype=float)
    arr = np.clip(arr, 0.0, 1.0)
    n = len(arr)
    bar_w = max(2, int((w - 20) / max(1, n)))
    for i, v in enumerate(arr):
        bx = x + 10 + i * bar_w
        cv2.rectangle(img, (bx, y + 28), (bx + bar_w - 1, y + h - 10), _severity_color(v), -1)


def _bilingual_label(label):
    return f"{label} ({_LABEL_ZH.get(label, label)})"


def _bilingual_issue(issue):
    return f"{issue} ({_LABEL_ZH.get(issue, issue)})"


def _bilingual_cue(cue):
    cue_map = {
        "step back and include full body": "后退并保证全身入镜",
        "step back until shoulders, hips, knees, ankles are visible": "后退直到肩髋膝踝都清晰可见",
        "start movement to begin analysis": "开始动作后再进入分析",
        "hold center frame until primary target locks": "保持在画面中央直到主目标锁定",
        "plant foot and lock ankle through contact": "支撑脚稳定，触球时锁定踝关节",
        "open hips and finish toward target": "打开髋部并朝目标完成随挥",
        "land softly, knees over toes": "轻柔落地，膝盖对准脚尖方向",
        "scan and keep center of mass stable": "保持观察并稳定重心",
        "maintain posture and tempo": "保持姿态与节奏",
    }
    zh = cue_map.get(cue, cue)
    return f"{cue} | {zh}"


def _safe_layout(w_img, h_img):
    m = max(14, int(w_img * 0.012))
    top_h = max(58, int(h_img * 0.085))
    timeline_h = max(88, int(h_img * 0.12))
    main_y = top_h + 10
    available_h = h_img - main_y - timeline_h - m - 6

    gap = max(12, int(w_img * 0.012))
    left_w = int(w_img * 0.34)
    right_w = int(w_img * 0.24)
    max_total = w_img - 2 * m - gap
    if left_w + right_w > max_total:
        scale = max_total / float(left_w + right_w)
        left_w = int(left_w * scale)
        right_w = int(right_w * scale)

    left_x = m
    right_x = w_img - m - right_w

    left_h = min(available_h, max(230, int(h_img * 0.34)))
    right_h = min(available_h, max(250, int(h_img * 0.42)))

    return {
        "margin": m,
        "top_h": top_h,
        "left": (left_x, main_y, left_w, min(available_h, left_h + max(18, int(h_img * 0.03)))),
        "right": (right_x, main_y, right_w, right_h),
        "timeline": (m, h_img - timeline_h - m, w_img - 2 * m, timeline_h),
    }


def _draw_session_end_stage(img, data, fps, clip_name, text_ctx):
    h_img, w_img = img.shape[:2]
    m = max(18, int(w_img * 0.018))
    title_size = max(24, int(w_img * 0.018))
    text_size = max(15, int(w_img * 0.0105))
    small_size = max(12, int(w_img * 0.0088))

    summary = data.get("session_summary") or {}
    scoring_state = str(summary.get("scoring_state", "insufficient_evidence"))
    quality_status = str(summary.get("quality_status", "pass"))
    quality_gate_pass = bool(summary.get("quality_gate_pass", False))
    action_label = summary.get("action_label") or _bilingual_label(summary.get("mapped_rule_key", summary.get("action", "soccer_idle")))
    status_map = {
        "ready_to_score": ("正式评分 / Ready to Score", (76, 180, 108)),
        "insufficient_evidence": ("证据不足 / Insufficient Evidence", (0, 140, 255)),
        "quality_fail": ("质量未达标 / Quality Fail", WARNING),
    }
    status_text, status_color = status_map.get(scoring_state, ("分析中 / Reviewing", MUTED))

    grad = np.zeros((max(70, int(h_img * 0.10)), w_img, 3), dtype=np.uint8)
    for i in range(w_img):
        t = i / max(1, w_img - 1)
        grad[:, i, :] = (int(16 + 18 * t), int(18 + 12 * t), int(20 + 10 * t))
    img[: grad.shape[0], :, :] = cv2.addWeighted(img[: grad.shape[0], :, :], 0.34, grad, 0.66, 0)

    _draw_text(img, "AI Coach Football / 足球智能分析", (m, 12), size=title_size, color=TEXT, ctx=text_ctx)
    _draw_text(img, f"Clip / 片段: {clip_name}", (m, 16 + title_size), size=text_size, color=MUTED, ctx=text_ctx)
    if fps is not None:
        _draw_text(img, f"FPS: {fps:.1f}", (w_img - m - 120, 12), size=title_size, color=TEXT, ctx=text_ctx)

    card_w = min(int(w_img * 0.84), 1120)
    card_h = min(int(h_img * 0.78), 680)
    x = (w_img - card_w) // 2
    y = int(h_img * 0.12)
    _blend_box(img, x, y, card_w, card_h, color=(14, 18, 24), alpha=0.84, border=(70, 120, 180))

    _draw_text(img, "Result Review / 结果回顾", (x + 24, y + 18), size=title_size, color=TEXT, ctx=text_ctx)
    _draw_text(img, f"Action / 动作: {action_label}", (x + 24, y + 56), size=text_size, color=MUTED, ctx=text_ctx)
    tag_w = max(180, int(card_w * 0.19))
    tag_h = max(30, int(text_size * 1.8))
    tag_x = x + card_w - tag_w - 24
    tag_y = y + 16
    _blend_box(img, tag_x, tag_y, tag_w, tag_h, color=(18, 24, 30), alpha=0.90, border=status_color)
    _draw_text(img, status_text, (tag_x + 12, tag_y + 6), size=small_size, color=TEXT, ctx=text_ctx)

    left_x = x + 24
    left_y = y + 92
    left_w = int(card_w * 0.44)
    left_h = int(card_h * 0.36)
    right_x = left_x + left_w + 18
    right_w = card_w - 48 - left_w - 18
    metric_cards = list(summary.get("primary_metrics") or [])

    if scoring_state == "ready_to_score":
        score = float(summary.get("avg_main_score", summary.get("overall_score", 0.0)) or 0.0)
        _blend_box(img, left_x, left_y, left_w, left_h, color=(18, 22, 30), alpha=0.82, border=(76, 180, 108))
        _draw_text(img, "正式总分 / Formal Score", (left_x + 16, left_y + 14), size=small_size, color=MUTED, ctx=text_ctx)
        _draw_text(img, f"{score:.0f}", (left_x + 16, left_y + 42), size=max(54, title_size + 32), color=TEXT, ctx=text_ctx)
        _draw_text(img, "/100", (left_x + 122, left_y + 80), size=text_size, color=MUTED, ctx=text_ctx)
        _draw_text(img, summary.get("level_label", ""), (left_x + 190, left_y + 74), size=text_size + 1, color=(205, 235, 210), ctx=text_ctx)
        _draw_bar(img, left_x + 16, left_y + 118, left_w - 32, 14, score / 100.0)
        _draw_text(img, summary.get("coach_summary", "-"), (left_x + 16, left_y + 146), size=small_size, color=TEXT, ctx=text_ctx)
    else:
        _blend_box(img, left_x, left_y, left_w, left_h, color=(18, 22, 30), alpha=0.82, border=status_color)
        title = "当前检测到的观察结果 / Current Observations" if scoring_state == "insufficient_evidence" else "视频质量问题 / Video Quality"
        _draw_text(img, title, (left_x + 16, left_y + 14), size=small_size, color=MUTED, ctx=text_ctx)
        message = summary.get("scoring_state_message") or summary.get("status_message") or summary.get("coach_summary") or summary.get("quality_hint") or "-"
        for idx, line in enumerate(_wrap_text(message, left_w - 32, small_size)[:3]):
            _draw_text(img, line, (left_x + 16, left_y + 40 + idx * (small_size + 6)), size=small_size, color=TEXT, ctx=text_ctx)
        if scoring_state == "quality_fail":
            _draw_text(img, "请重拍更清晰的视频，再重新分析。", (left_x + 16, left_y + left_h - 42), size=small_size, color=WARNING, ctx=text_ctx)
        else:
            obs = summary.get("observations") or summary.get("quality_result", {}).get("observed", {})
            obs_line = f"Observation / 观察: fps {float(obs.get('fps', 0.0) or 0.0):.1f}, pose {float(obs.get('pose_visibility', 0.0) or 0.0):.2f}, ball {float(obs.get('ball_track_missing_ratio', 0.0) or 0.0):.2f}"
            _draw_text(img, obs_line, (left_x + 16, left_y + left_h - 42), size=small_size, color=MUTED, ctx=text_ctx)

    _blend_box(img, right_x, left_y, right_w, left_h, color=(18, 22, 30), alpha=0.82, border=(70, 120, 180))
    _draw_text(img, "关键指标 / Metrics", (right_x + 16, left_y + 14), size=small_size, color=MUTED, ctx=text_ctx)
    if not metric_cards:
        metric_cards = [
            {"metric": "endpoint_error_m", "label": "endpoint_error", "raw_value": None, "score": None, "band": "missing"},
            {"metric": "execution_time_s", "label": "execution_time", "raw_value": None, "score": None, "band": "missing"},
            {"metric": "penalty_events", "label": "penalty_events", "raw_value": None, "score": None, "band": "missing"},
        ]
    card_gap = 10
    metric_w = max(110, int((right_w - 32 - 2 * card_gap) / 3))
    for idx, metric in enumerate(metric_cards[:3]):
        bx = right_x + 16 + idx * (metric_w + card_gap)
        metric_name = str(metric.get("label") or metric.get("metric") or "metric")
        raw_value = metric.get("raw_value")
        score_value = metric.get("score")
        band = str(metric.get("band", "unknown"))
        border = (80, 110, 160)
        if band in {"excellent", "good"}:
            border = (76, 180, 108)
        elif band in {"needs_work", "warn"}:
            border = (0, 140, 255)
        elif band in {"poor", "fail"}:
            border = WARNING
        _blend_box(img, bx, left_y + 38, metric_w, 106, color=(20, 26, 34), alpha=0.82, border=border)
        _draw_text(img, metric_name, (bx + 10, left_y + 50), size=small_size, color=TEXT, ctx=text_ctx)
        value_text = "—" if raw_value is None else f"{float(raw_value):.2f}" if isinstance(raw_value, (int, float)) else str(raw_value)
        _draw_text(img, value_text, (bx + 10, left_y + 78), size=max(22, text_size - 1), color=TEXT, ctx=text_ctx)
        if score_value is not None:
            _draw_text(img, f"score {float(score_value):.0f}", (bx + 10, left_y + 104), size=small_size, color=MUTED, ctx=text_ctx)
        if band != "unknown":
            _draw_text(img, band, (bx + metric_w - 48, left_y + 104), size=small_size, color=MUTED, ctx=text_ctx)

    bottom_y = left_y + left_h + 18
    bottom_h = card_h - (bottom_y - y) - 18
    _blend_box(img, x + 24, bottom_y, card_w - 48, bottom_h, color=(16, 20, 28), alpha=0.80, border=(70, 120, 180))

    text_left_x = x + 40
    text_right_x = x + card_w - 420
    section_y = bottom_y + 16
    sections = [
        ("Summary / 一句话总结", summary.get("coach_summary", "-"), TEXT),
        (summary.get("issue_title", "Core Problem / 核心问题"), summary.get("core_problem", "-"), TEXT),
        ("Next Cue / 下一步建议", summary.get("suggestion", "-"), TEXT),
    ]
    for title, content, color in sections:
        _draw_text(img, title, (text_left_x, section_y), size=small_size, color=MUTED, ctx=text_ctx)
        section_y += small_size + 4
        for line in _wrap_text(str(content), int(card_w * 0.48), small_size)[:2]:
            _draw_text(img, line, (text_left_x, section_y), size=small_size, color=color, ctx=text_ctx)
            section_y += small_size + 4
        section_y += 6

    quality_observed = summary.get("quality_result", {}).get("observed", {})
    observed_lines = [
        f"Quality / 质量状态: {quality_status} | pass={quality_gate_pass}",
        f"Detected / 识别动作: {summary.get('detected_action', '-')}",
        f"Mapped Rule / 规则映射: {summary.get('mapped_rule_key', '-')}",
    ]
    error_timestamps = summary.get("error_timestamps") or []
    if error_timestamps:
        top_errors = []
        for item in error_timestamps[:3]:
            phase = str(item.get("phase", "contact"))
            time_value = float(item.get("time", 0.0) or 0.0)
            top_errors.append(f"{phase}@{time_value:.2f}s")
        observed_lines.append(f"Error Timestamps / 错误时间点: {', '.join(top_errors)}")
    else:
        observed_lines.append("Error Timestamps / 错误时间点: -")

    for idx, line in enumerate(observed_lines):
        _draw_text(img, line, (text_right_x, bottom_y + 20 + idx * (small_size + 8)), size=small_size, color=TEXT, ctx=text_ctx)

    triggered_rules = summary.get("triggered_rules") or []
    fail_reasons = summary.get("fail_reasons") or []
    trig_text = "Triggered Rules / 触发规则: " + (", ".join(str(item.get("id") or item.get("metric") or "") for item in triggered_rules[:3]) if triggered_rules else "-")
    fail_text = "Fail Reasons / 失败原因: " + (", ".join(str(item) for item in fail_reasons[:2]) if fail_reasons else "-")
    _draw_text(img, trig_text, (text_right_x, bottom_y + 20 + 4 * (small_size + 8)), size=small_size, color=TEXT, ctx=text_ctx)
    _draw_text(img, fail_text, (text_right_x, bottom_y + 20 + 5 * (small_size + 8)), size=small_size, color=TEXT, ctx=text_ctx)

    if dev:
        debug_y = bottom_y + 92
        debug_h = max(96, bottom_h - 110)
        _blend_box(img, text_right_x, debug_y, card_w - 64 - (text_right_x - (x + 40)), debug_h, color=(18, 18, 22), alpha=0.78, border=WARNING)
        debug_lines = [
            f"detected_action: {summary.get('detected_action', '-')}",
            f"mapped_rule_key: {summary.get('mapped_rule_key', '-')}",
            f"score_source: {summary.get('score_source', '-')}",
            f"scoring_state: {scoring_state}",
            f"quality_gate_pass: {quality_gate_pass}",
        ]
        _draw_text(img, "DEV DEBUG / 调试信息", (text_right_x + 12, debug_y + 10), size=small_size, color=WARNING, ctx=text_ctx)
        ty = debug_y + 32
        for line in debug_lines:
            _draw_text(img, line, (text_right_x + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
            ty += small_size + 4
        pm = summary.get("primary_metrics") or []
        pm_text = "primary_metrics: " + ", ".join(str(item.get("metric") or item.get("label") or "") for item in pm[:4]) if pm else "primary_metrics: -"
        _draw_text(img, pm_text, (text_right_x + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
        ty += small_size + 4
        trig = "triggered_rules: " + ", ".join(str(item.get("id") or item.get("metric") or "") for item in triggered_rules[:4]) if triggered_rules else "triggered_rules: -"
        _draw_text(img, trig, (text_right_x + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
        ty += small_size + 4
        fails = "fail_reasons: " + ", ".join(str(item) for item in fail_reasons[:3]) if fail_reasons else "fail_reasons: -"
        _draw_text(img, fails, (text_right_x + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
    else:
        _draw_text(img, "Quality / 视频质量", (text_right_x, bottom_y + 20 + 6 * (small_size + 8)), size=small_size, color=MUTED, ctx=text_ctx)
        quality_line = f"{quality_status} | pass={quality_gate_pass}"
        _draw_text(img, quality_line, (text_right_x, bottom_y + 20 + 7 * (small_size + 8)), size=small_size, color=TEXT, ctx=text_ctx)

    can_continue = bool(summary.get("can_continue", False))
    hold_left = float(summary.get("hold_left_s", 0.0))
    continue_hint = summary.get("continue_hint", "")
    footer_y = y + card_h - 30
    if summary.get("saved_path"):
        saved_line = f"Saved / 已保存: {Path(summary['saved_path']).name}"
        _draw_text(img, saved_line, (x + 24, footer_y - 20), size=small_size, color=MUTED, ctx=text_ctx)
    if continue_hint:
        hint_color = (210, 240, 220) if can_continue else (255, 210, 160)
        _draw_text(img, continue_hint, (x + 24, footer_y), size=small_size, color=hint_color, ctx=text_ctx)
    elif can_continue:
        _draw_text(img, "Press SPACE for next session / 按空格开始下一次检测", (x + 24, footer_y), size=small_size, color=(210, 240, 220), ctx=text_ctx)
    else:
        _draw_text(img, f"Review lock: {hold_left:.1f}s remaining / 结果展示中：剩余 {hold_left:.1f} 秒", (x + 24, footer_y), size=small_size, color=(255, 210, 160), ctx=text_ctx)


def _draw_home_stage(img, data, fps, clip_name, text_ctx):
    h_img, w_img = img.shape[:2]
    m = max(18, int(w_img * 0.018))
    title_size = max(26, int(w_img * 0.020))
    text_size = max(16, int(w_img * 0.011))
    small_size = max(13, int(w_img * 0.009))

    grad = np.zeros((h_img, w_img, 3), dtype=np.uint8)
    for i in range(h_img):
        t = i / max(1, h_img - 1)
        grad[i, :, :] = (int(10 + 20 * t), int(12 + 24 * t), int(18 + 30 * t))
    img[:] = cv2.addWeighted(img, 0.35, grad, 0.65, 0)

    _draw_text(img, "AI Coach", (m, 18), size=title_size + 8, color=TEXT, ctx=text_ctx)
    _draw_text(img, "Football capture flow / 足球采集流程", (m, 30 + title_size), size=text_size, color=MUTED, ctx=text_ctx)
    if fps is not None:
        _draw_text(img, f"FPS: {fps:.1f}", (w_img - m - 120, 18), size=title_size, color=TEXT, ctx=text_ctx)

    left_w = min(430, int(w_img * 0.34))
    left_h = min(340, int(h_img * 0.46))
    left_x = m
    left_y = int(h_img * 0.20)
    _blend_box(img, left_x, left_y, left_w, left_h, color=(16, 18, 24), alpha=0.78, border=PRIMARY)
    _draw_text(img, "Capture Flow / 录制流程", (left_x + 18, left_y + 18), size=text_size + 2, color=TEXT, ctx=text_ctx)
    bullets = [
        "1. Choose a template / 选择训练模板",
        "2. Enter ready state and lock one athlete / 进入准备页并锁定单人",
        "3. Press SPACE to start recording / 按空格开始录制",
        "4. Review happens after recording / 录制结束后再离线分析",
    ]
    ty = left_y + 62
    for line in bullets:
        _draw_text(img, line, (left_x + 18, ty), size=text_size, color=TEXT, ctx=text_ctx)
        ty += text_size + 16

    current = data.get("selected_template", "passing_stability")
    templates = data.get("templates") or [
        {"code": "passing_stability", "label": "Passing Stability / 传球稳定性"},
        {"code": "shooting_quality", "label": "Shooting Quality / 射门动作质量"},
        {"code": "first_touch_control", "label": "First-Touch Control / 停球控制"},
    ]
    card_w = min(360, int(w_img * 0.26))
    card_h = 148
    gap = 16
    start_x = w_img - m - (card_w * len(templates) + gap * (len(templates) - 1))
    cy = int(h_img * 0.26)
    subtitles = {
        "passing_stability": "Support foot, contact posture, and repeatable passing quality / 支撑脚、触球姿态与传球一致性",
        "shooting_quality": "Strike mechanics, body alignment, and shot completion / 发力触球、身体朝向与射门完成度",
        "first_touch_control": "First touch control, body organization, and next-action readiness / 停球控制、身体组织与下一步衔接",
    }
    for idx, item in enumerate(templates):
        hotkey = str(idx + 1)
        title = item["label"]
        subtitle = subtitles.get(item["code"], item["label"])
        selected = item["code"] == current
        x = start_x + idx * (card_w + gap)
        border = (80, 180, 120) if selected else (70, 90, 120)
        _blend_box(img, x, cy, card_w, card_h, color=(18, 22, 30), alpha=0.76, border=border)
        _draw_text(img, hotkey, (x + 16, cy + 14), size=title_size + 2, color=_from_rgb((255, 214, 90)) if selected else MUTED, ctx=text_ctx)
        _draw_text(img, title, (x + 52, cy + 18), size=text_size + 2, color=TEXT, ctx=text_ctx)
        sub_lines = _wrap_text(subtitle, card_w - 24, small_size)
        for j, line in enumerate(sub_lines[:2]):
            _draw_text(img, line, (x + 16, cy + 62 + j * (small_size + 6)), size=small_size, color=MUTED, ctx=text_ctx)
        if selected:
            _draw_text(img, "Selected / 已选中", (x + 16, cy + card_h - 28), size=small_size, color=(205, 245, 220), ctx=text_ctx)

    footer_y = h_img - 110
    _blend_box(img, m, footer_y, w_img - 2 * m, 74, color=(14, 18, 22), alpha=0.66, border=(80, 90, 100))
    _draw_text(img, data.get("home_hint", "Choose a template, then press SPACE to record"), (m + 16, footer_y + 16), size=text_size, color=TEXT, ctx=text_ctx)
    last_path = data.get("last_session_path")
    if last_path:
        _draw_text(img, f"Last Session / 上次结果: {Path(last_path).name}", (m + 16, footer_y + 42), size=small_size, color=MUTED, ctx=text_ctx)


def _draw_event_card(img, event_card, text_ctx):
    if not event_card:
        return
    h_img, w_img = img.shape[:2]
    card_w = min(420, int(w_img * 0.30))
    card_h = max(108, int(h_img * 0.15))
    x = (w_img - card_w) // 2
    y = max(76, int(h_img * 0.10))
    _blend_box(img, x, y, card_w, card_h, color=(22, 20, 18), alpha=0.72, border=WARNING)
    title_size = max(15, int(w_img * 0.010))
    text_size = max(13, int(w_img * 0.0090))
    _draw_text(img, event_card.get("title", "Latest Event / 最近事件"), (x + 14, y + 10), size=text_size, color=MUTED, ctx=text_ctx)
    _draw_text(
        img,
        _bilingual_label(event_card.get("label", "soccer_idle")),
        (x + 14, y + 34),
        size=title_size + 2,
        color=TEXT,
        ctx=text_ctx,
    )
    issue = f"Issue / 问题: {_bilingual_issue(event_card.get('issue', 'stable_motion'))}"
    for idx, line in enumerate(_wrap_text(issue, card_w - 28, text_size)[:2]):
        _draw_text(img, line, (x + 14, y + 60 + idx * (text_size + 3)), size=text_size, color=TEXT, ctx=text_ctx)
    cue = _wrap_text(_bilingual_cue(event_card.get("cue", "-")), card_w - 28, text_size)
    if cue:
        _draw_text(img, cue[0], (x + 14, y + card_h - 28), size=text_size, color=MUTED, ctx=text_ctx)


def _draw_setup_stage(img, data, fps, clip_name, text_ctx):
    h_img, w_img = img.shape[:2]
    m = max(18, int(w_img * 0.018))
    title_size = max(24, int(w_img * 0.018))
    text_size = max(16, int(w_img * 0.011))
    small_size = max(13, int(w_img * 0.009))

    grad = np.zeros((max(70, int(h_img * 0.10)), w_img, 3), dtype=np.uint8)
    for i in range(w_img):
        t = i / max(1, w_img - 1)
        grad[:, i, :] = (int(14 + 26 * t), int(14 + 18 * t), int(16 + 10 * t))
    img[: grad.shape[0], :, :] = cv2.addWeighted(img[: grad.shape[0], :, :], 0.32, grad, 0.68, 0)

    _draw_text(img, f"AI Coach Football / 足球智能分析", (m, 12), size=title_size, color=TEXT, ctx=text_ctx)
    _draw_text(img, f"Clip / 片段: {clip_name}", (m, 16 + title_size), size=text_size, color=MUTED, ctx=text_ctx)
    if fps is not None:
        _draw_text(img, f"FPS: {fps:.1f}", (w_img - m - 120, 12), size=title_size, color=TEXT, ctx=text_ctx)

    card_w = min(int(w_img * 0.54), 760)
    card_h = min(int(h_img * 0.52), 360)
    x = (w_img - card_w) // 2
    y = int(h_img * 0.16)
    _blend_box(img, x, y, card_w, card_h, color=(14, 18, 24), alpha=0.72, border=(70, 120, 180))

    title = "Prepare Athlete And Confirm Recording / 准备被检测人物并开始录制"
    _draw_text(img, title, (x + 22, y + 20), size=title_size, color=TEXT, ctx=text_ctx)

    lock_score = float(data.get("lock_score", 0.0))
    full_body = bool(data.get("full_body", False))
    subject_ready = bool(data.get("subject_ready", False))
    start_ready = bool(data.get("start_ready", False))
    one_athlete = bool(lock_score >= 0.25 or subject_ready)
    steps = [
        ("1. Keep one athlete in frame / 画面中仅保留一位被检测者", one_athlete),
        ("2. Full body visible / 肩髋膝踝全部入镜", full_body),
        ("3. Lock primary target / 锁定主检测对象", lock_score >= 0.85),
        ("4. Press SPACE to start recording / 按空格开始录制", start_ready),
    ]
    ty = y + 70
    for line, done in steps:
        color = (90, 210, 120) if done else TEXT
        prefix = "[OK]" if done else "[ ]"
        _draw_text(img, f"{prefix} {line}", (x + 24, ty), size=text_size, color=color, ctx=text_ctx)
        ty += text_size + 12

    _draw_text(img, "Target Lock / 主目标锁定", (x + 24, ty + 6), size=text_size, color=MUTED, ctx=text_ctx)
    _draw_bar(img, x + 24, ty + 34, card_w - 48, 16, lock_score)
    _draw_text(img, f"{lock_score:.2f}", (x + card_w - 70, ty + 24), size=text_size, color=TEXT, ctx=text_ctx)

    ty += 76
    status_text = data.get("setup_hint", "Move into position")
    _draw_text(img, f"Status / 状态: {status_text}", (x + 24, ty), size=text_size, color=TEXT, ctx=text_ctx)
    ty += text_size + 10
    _draw_text(img, "Keys: space=record  r=reset  c=next cam  0-5=direct cam  q=quit", (x + 24, ty), size=small_size, color=MUTED, ctx=text_ctx)

    if subject_ready:
        tip_w = min(420, int(w_img * 0.34))
        tip_h = 52
        tx = (w_img - tip_w) // 2
        ty2 = y + card_h + 20
        _blend_box(img, tx, ty2, tip_w, tip_h, color=(22, 44, 30), alpha=0.80, border=(60, 170, 105))
        _draw_text(img, "Ready. Press SPACE to begin recording / 已就绪，按空格开始录制", (tx + 16, ty2 + 14), size=text_size, color=(220, 245, 220), ctx=text_ctx)


def render_card(img, data, dev=False, severity_hist=None, metrics=None, fps=None, clip_name="Live Camera"):
    h_img, w_img = img.shape[:2]
    ly = _safe_layout(w_img, h_img)
    m = ly["margin"]
    text_ctx = _make_text_ctx(img)
    ui_stage = data.get("ui_stage", "active")

    # top bar
    grad = np.zeros((ly["top_h"], w_img, 3), dtype=np.uint8)
    for i in range(w_img):
        t = i / max(1, w_img - 1)
        grad[:, i, :] = (int(12 + 28 * t), int(12 + 16 * t), int(12 + 8 * t))
    img[: ly["top_h"], :, :] = cv2.addWeighted(img[: ly["top_h"], :, :], 0.30, grad, 0.70, 0)

    title_size = max(18, int(w_img * 0.015))
    text_size = max(14, int(w_img * 0.0105))
    small_size = max(12, int(w_img * 0.0090))

    if ui_stage == "setup":
        _draw_setup_stage(img, data, fps, clip_name, text_ctx)
        _flush_text_ctx(img, text_ctx)
        return
    if ui_stage == "home":
        _draw_home_stage(img, data, fps, clip_name, text_ctx)
        _flush_text_ctx(img, text_ctx)
        return
    if ui_stage == "session_end":
        _draw_session_end_stage(img, data, fps, clip_name, text_ctx)
        _flush_text_ctx(img, text_ctx)
        return

    _draw_text(img, f"Clip / 片段: {clip_name}", (m, 10), size=title_size, color=TEXT, ctx=text_ctx)
    _draw_text(img, f"Mode / 模式: {data.get('mode_name', 'soccer_basic / 足球基础')}", (m, 10 + title_size + 4), size=text_size, color=MUTED, ctx=text_ctx)
    if fps is not None:
        _draw_text(img, f"FPS: {fps:.1f}", (w_img - m - max(120, int(w_img * 0.12)), 10), size=title_size, color=TEXT, ctx=text_ctx)

    # left summary
    lx, ly0, lw, lh = ly["left"]
    _blend_box(img, lx, ly0, lw, lh, alpha=0.62, border=PRIMARY)

    y = ly0 + 12
    _draw_text(img, "Capture Status / 采集状态", (lx + 12, y), size=text_size, color=MUTED, ctx=text_ctx)
    badge_w = 0
    y += text_size + 4
    if data.get("calibrated"):
        badge_w = max(150, int(lw * 0.23))
        badge_h = max(28, int(text_size * 1.7))
        bx = lx + lw - badge_w - 12
        by = ly0 + 12
        _blend_box(img, bx, by, badge_w, badge_h, color=(24, 50, 34), alpha=0.78, border=(70, 160, 110))
        _draw_text(img, "Calibrated / 已标定", (bx + 10, by + 6), size=small_size, color=(210, 245, 220), ctx=text_ctx)
    action_lines = _wrap_text(_bilingual_label(data.get("label", "unknown")), lw - 24 - badge_w - 8, max(16, title_size - 1))
    for line in action_lines[:2]:
        _draw_text(img, line, (lx + 12, y), size=title_size, color=TEXT, ctx=text_ctx)
        y += title_size + 3

    overall_score = float(data.get("overall_score", 0.0))
    _draw_text(img, data.get("score_name", "Overall Score / 综合评分"), (lx + 12, y + 4), size=small_size, color=MUTED, ctx=text_ctx)
    _draw_text(img, f"{overall_score:.0f}", (lx + 12, y + 24), size=max(40, title_size + 18), color=TEXT, ctx=text_ctx)
    _draw_text(img, "/100", (lx + 94, y + 44), size=text_size, color=MUTED, ctx=text_ctx)
    _draw_text(img, data.get("level_label", ""), (lx + 136, y + 38), size=text_size, color=(205, 235, 210), ctx=text_ctx)
    _draw_bar(img, lx + 12, y + 82, lw - 24, 14, overall_score / 100.0)
    y += 106

    _draw_text(img, f"Training Goal / 本次目标: {data.get('task_title', 'Training Session / 训练会话')}", (lx + 12, y + 4), size=small_size, color=MUTED, ctx=text_ctx)
    y += small_size + 10
    _draw_text(
        img,
        f"Progress / 训练进度: {int(data.get('task_completed', 0))}/{int(data.get('task_target', 12))}",
        (lx + 12, y),
        size=text_size,
        color=TEXT,
        ctx=text_ctx,
    )
    progress = 0.0 if int(data.get('task_target', 12)) <= 0 else float(data.get('task_completed', 0)) / float(data.get('task_target', 12))
    _draw_bar(img, lx + 12, y + 28, lw - 24, 12, progress)
    y += 56

    def _draw_block(title, content, color=TEXT, max_lines=2):
        nonlocal y
        if y > ly0 + lh - 44:
            return
        _draw_text(img, title, (lx + 12, y), size=small_size, color=MUTED, ctx=text_ctx)
        y += small_size + 6
        for line in _wrap_text(content, lw - 24, small_size)[:max_lines]:
            if y > ly0 + lh - 20:
                break
            _draw_text(img, line, (lx + 12, y), size=small_size, color=color, ctx=text_ctx)
            y += small_size + 4
        y += 6

    _draw_block("Summary / 一句话总结", data.get("coach_summary", "-"), color=TEXT, max_lines=2)
    _draw_block(data.get("problem_title", "Core Problem / 核心问题"), data.get("core_problem", "-"), color=TEXT, max_lines=2)
    _draw_block("Next Cue / 下一步建议", _bilingual_cue(data.get("suggestion", "-")), color=TEXT, max_lines=2)
    _draw_block("Positive Feedback / 正向反馈", data.get("positive_feedback", "-"), color=(205, 235, 210), max_lines=1)

    metrics = metrics or {}
    if dev:
        rx, ry, rw, rh = ly["right"]
        _blend_box(img, rx, ry, rw, rh, alpha=0.60, border=(80, 110, 160))
        _draw_text(img, "Football + Biomechanics / 足球专项与生物力学", (rx + 12, ry + 12), size=text_size + 1, color=TEXT, ctx=text_ctx)
        lines = [
            f"Phase 阶段: {metrics.get('phase', 'set')} ({_LABEL_ZH.get(metrics.get('phase', 'set'), metrics.get('phase', 'set'))})",
            f"Target 主目标: {metrics.get('target_status', 'locked')} ({_LABEL_ZH.get(metrics.get('target_status', 'locked'), metrics.get('target_status', 'locked'))})",
            f"Tech 技术: {metrics.get('technique_score', 0):.2f}",
            f"Control 控制: {metrics.get('control_score', 0):.2f}",
            f"Risk 风险: {metrics.get('risk_score', 0):.2f}",
            f"Knee L/R 膝: {metrics.get('knee_l', 0):.1f} / {metrics.get('knee_r', 0):.1f} deg",
            f"Hip  L/R 髋: {metrics.get('hip_l', 0):.1f} / {metrics.get('hip_r', 0):.1f} deg",
            f"Symmetry 对称: {metrics.get('symmetry', 0):.2f}",
            f"Balance 平衡: {metrics.get('balance', 0):.2f}",
            f"Trunk Lean 躯干倾斜: {metrics.get('trunk_lean_deg', 0):.1f} deg",
            f"Valgus Ratio 膝内扣比: {metrics.get('valgus_ratio', 1):.2f}",
            f"Depth 深度: {metrics.get('depth', 0):.2f}",
            f"Visibility 可见度: {metrics.get('visibility', 0):.2f}",
            f"Stability 稳定性: {metrics.get('stability', 0):.2f}",
            f"Motion Ratio 运动比: {metrics.get('move_ratio', 0):.3f}",
            f"Target Lock 主目标锁定: {metrics.get('target_lock_score', 0):.2f}",
            f"Switch Risk 切换风险: {metrics.get('target_switch_risk', 0):.2f}",
            f"Ball Conf 球置信: {metrics.get('ball_confidence', 0):.2f}",
            f"Ball Track 球跟踪: {metrics.get('ball_track_source', 'lost')} ({_LABEL_ZH.get(metrics.get('ball_track_source', 'lost'), metrics.get('ball_track_source', 'lost'))})",
            f"Ball Contact 触球: {metrics.get('contact_side', 'none')} / {metrics.get('ball_contact', 0):.0f}",
        ]
        if "ball_distance_m" in metrics:
            lines.append(f"Ball Dist 球距: {metrics.get('ball_distance_m', 0):.2f} m")
        if "stance_width_m" in metrics:
            lines.append(f"Stance Width 站距: {metrics.get('stance_width_m', 0):.2f} m")
        if "pixel_scale_cm" in metrics:
            lines.append(f"Scale 比例: {metrics.get('pixel_scale_cm', 0):.2f} cm/px")
        ty = ry + text_size + 22
        for line in lines:
            if ty > ry + rh - text_size - 4:
                break
            _draw_text(img, line, (rx + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
            ty += small_size + 6
    else:
        chip_w = min(300, int(w_img * 0.20))
        chip_h = 146
        chip_x = w_img - m - chip_w
        chip_y = ly["top_h"] + 12
        _blend_box(img, chip_x, chip_y, chip_w, chip_h, alpha=0.58, border=(80, 110, 160))
        _draw_text(img, "Quality Breakdown / 质量分项", (chip_x + 12, chip_y + 12), size=text_size, color=TEXT, ctx=text_ctx)
        phase = data.get("issue_phase_label", data.get("phase", "set"))
        chip_lines = [
            f"Template 模板: {data.get('template_label', '-')}",
            f"Issue Location 问题阶段: {phase} ({_LABEL_ZH.get(phase, phase)})",
            f"Technical 技术执行: {float(data.get('technical_execution_score', 0.0)):.0f}/100",
            f"Control 控制稳定: {float(data.get('control_stability_score', 0.0)):.0f}/100",
            f"Safety 动作安全: {float(data.get('action_safety_score', 0.0)):.0f}/100",
        ]
        ty = chip_y + text_size + 18
        for line in chip_lines:
            _draw_text(img, line, (chip_x + 12, ty), size=small_size, color=TEXT, ctx=text_ctx)
            ty += small_size + 8

    # timeline
    tx, ty0, tw, th = ly["timeline"]
    _draw_heatmap_timeline(img, severity_hist or [], tx, ty0, tw, th, title_size=small_size, ctx=text_ctx)

    if not dev and data.get("show_event_card", False):
        _draw_event_card(img, data.get("event_card"), text_ctx)

    if dev:
        dw = min(720, w_img - 2 * m)
        dh = max(110, int(h_img * 0.13))
        dx = m
        dy = max(ly["top_h"] + 8, ty0 - dh - 8)
        _blend_box(img, dx, dy, dw, dh, alpha=0.52, border=(80, 80, 80))
        _draw_text(img, "DEV MODE / 开发模式", (dx + 12, dy + 10), size=text_size, color=WARNING, ctx=text_ctx)
        raw_lines = _wrap_text(f"RAW: {data.get('raw', '-')}", dw - 24, small_size)
        ry0 = dy + text_size + 16
        for line in raw_lines[:3]:
            _draw_text(img, line, (dx + 12, ry0), size=small_size, color=TEXT, ctx=text_ctx)
            ry0 += small_size + 4

    _flush_text_ctx(img, text_ctx)


def render_summary_card(cleaned_kp: Path, pose3d: Path, action, explanation, out_video: Path, video_path=None, dev=False, min_frames=None, preview=False):
    data = json.loads(cleaned_kp.read_text())
    frames = data.get("frames", [])
    if not frames:
        raise SystemExit("no frames")

    cap = cv2.VideoCapture(str(video_path)) if video_path else None
    w, h = (640, 360)
    if cap and cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out_video), fourcc, 30.0, (w, h))

    total = len(frames)
    if min_frames:
        total = max(total, int(min_frames))

    severity_hist = []
    for i in range(total):
        if cap and cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((h, w, 3), dtype=np.uint8)
        else:
            frame = np.zeros((h, w, 3), dtype=np.uint8)

        sev = float(explanation.get("severity", 0.2))
        severity_hist.append(sev)
        summary = {
            "label": action.get("label", "squat"),
            "confidence": action.get("confidence", 0.5),
            "set": 1,
            "reps": i % 12,
            "rep_target": 12,
            "severity": sev,
            "suggestion": explanation.get("suggestion", "maintain posture and tempo"),
            "raw": f"frame {i}",
            "mode_name": "offline_demo / 离线演示",
        }
        render_card(frame, summary, dev=dev, severity_hist=severity_hist[-120:], metrics={}, fps=30.0)
        writer.write(frame)
        if preview:
            cv2.imshow("AI Coach Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    if cap and cap.isOpened():
        cap.release()
    writer.release()
    if preview:
        cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--pose", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--video", default=None)
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--min_frames", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    render_summary_card(
        Path(args.keypoints),
        Path(args.pose),
        {"label": "squat", "confidence": 0.92},
        {"severity": 0.3, "suggestion": "maintain posture and tempo"},
        Path(args.out),
        args.video,
        args.dev,
        args.min_frames,
        args.preview,
    )


if __name__ == "__main__":
    main()
