import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from frontend.components.timeline import draw_timeline

PRIMARY = (0x91, 0x3D, 0x0B)  # BGR
WARNING = (0x00, 0x8C, 0xFF)
GOOD = (0x2E, 0xCC, 0x71)
MID = (0x00, 0xC3, 0xFF)


def _font(size=20):
    # Try common CJK fonts on macOS, fallback to default
    for p in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _draw_text(image, text, pos, size=20, color=(255, 255, 255)):
    # Draw unicode text with PIL
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil)
    draw.text(pos, text, font=_font(size), fill=(color[2], color[1], color[0]))
    out = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    image[:, :, :] = out


def draw_top_bar(image, clip_name, fps, mode3d="OFF"):
    h, w = image.shape[:2]
    cv2.rectangle(image, (0, 0), (w, 40), PRIMARY, -1)
    _draw_text(image, f"Clip: {clip_name}", (12, 8), size=18)
    _draw_text(image, f"FPS: {fps:.1f}", (w - 260, 8), size=18)
    _draw_text(image, f"3D: {mode3d}", (w - 140, 8), size=18)
    # Export button (visual only)
    cv2.rectangle(image, (w - 300, 8), (w - 170, 32), WARNING, -1)
    _draw_text(image, "Export Report", (w - 295, 8), size=14, color=(0, 0, 0))


def _severity_color(v):
    if v < 0.4:
        return GOOD
    if v < 0.7:
        return MID
    return WARNING


def render_user_mode(image, clip_name, fps, data, timeline_values):
    h, w = image.shape[:2]
    draw_top_bar(image, clip_name, fps, data.get("mode3d", "OFF"))

    # Summary card
    x, y, cw, ch = 20, 60, 520, 170
    overlay = image.copy()
    cv2.rectangle(overlay, (x, y), (x + cw, y + ch), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
    cv2.rectangle(image, (x, y), (x + cw, y + ch), PRIMARY, 2)

    _draw_text(image, f"动作类型: {data['mode']}", (x + 12, y + 8), size=20)
    _draw_text(image, f"组次: 第{data['set_idx']}组", (x + 12, y + 36), size=16)
    _draw_text(image, f"次数: {data['reps']}/{data['rep_target']}", (x + 12, y + 58), size=16)

    # Severity bar
    bar_x, bar_y, bar_w, bar_h = x + 12, y + 85, cw - 24, 14
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), 1)
    fill = int(bar_w * max(0.0, min(1.0, data["severity"])))
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), _severity_color(data["severity"]), -1)
    _draw_text(image, f"严重度: {data['severity']:.2f}", (x + 12, y + 105), size=16)
    _draw_text(image, f"建议动作: {data['exercise']}", (x + 12, y + 130), size=16)

    # Left bottom: errors / causes
    ex_x, ex_y, ex_w, ex_h = 20, h - 250, 520, 170
    overlay = image.copy()
    cv2.rectangle(overlay, (ex_x, ex_y), (ex_x + ex_w, ex_y + ex_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
    cv2.rectangle(image, (ex_x, ex_y), (ex_x + ex_w, ex_y + ex_h), PRIMARY, 1)
    _draw_text(image, "错误/风险提示", (ex_x + 10, ex_y + 6), size=16)
    ty = ex_y + 30
    for e in data["errors"][:4]:
        col = _severity_color(e["severity"])
        cv2.circle(image, (ex_x + 14, ty + 5), 5, col, -1)
        _draw_text(image, f"{e['label']}  {e['severity']:.2f}", (ex_x + 26, ty - 2), size=14)
        ty += 22

    _draw_text(image, "原因分析", (ex_x + 260, ex_y + 6), size=16)
    ty = ex_y + 30
    for c in data["causes"][:3]:
        cue = c.get("cue", "")
        _draw_text(image, f"{c['name']} {c['prob']:.2f}", (ex_x + 260, ty - 2), size=14)
        if cue:
            _draw_text(image, f"提示: {cue}", (ex_x + 260, ty + 14), size=12)
            ty += 10
        ty += 22

    # Suggestions
    _draw_text(image, "训练建议", (ex_x + 10, ex_y + 110), size=16)
    ty = ex_y + 130
    for s in data.get("suggestions", [])[:2]:
        _draw_text(image, f"{s['exercise']} {s['sets']}x{s['reps']}  {s['cue']}", (ex_x + 10, ty), size=13)
        ty += 18

    # Right bottom: trends/timeline
    draw_timeline(image, (w - 520, h - 120, 500, 90), timeline_values)
    _draw_text(image, "严重度趋势", (w - 520, h - 135), size=14)

    # Timeline at bottom
    # (already drawn in right-bottom)


def render_dev_mode(image, debug_lines):
    # Simple dev overlay
    x, y = 20, 60
    w, h = 380, 180
    overlay = image.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
    cv2.rectangle(image, (x, y), (x + w, y + h), PRIMARY, 1)

    ty = y + 10
    for line in debug_lines:
        _draw_text(image, line, (x + 10, ty), size=14)
        ty += 18
