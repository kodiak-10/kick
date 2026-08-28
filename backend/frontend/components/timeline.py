import cv2
import numpy as np

PRIMARY = (0x91, 0x3D, 0x0B)
WARNING = (0x00, 0x8C, 0xFF)


def draw_timeline(image, rect, severity_values):
    x, y, w, h = rect
    cv2.rectangle(image, (x, y), (x + w, y + h), (30, 30, 30), -1)
    cv2.rectangle(image, (x, y), (x + w, y + h), PRIMARY, 1)

    if not severity_values:
        return

    vals = np.array(severity_values, dtype=float)
    vals = np.clip(vals, 0.0, 1.0)
    n = len(vals)

    # heatmap strip
    for i in range(n):
        px = x + int(i * (w - 1) / max(1, n - 1))
        c = (int(50 + 205 * vals[i]), int(50 + 100 * vals[i]), int(50))
        cv2.line(image, (px, y), (px, y + h), c, 1)

    # severity line
    pts = []
    for i in range(n):
        px = x + int(i * (w - 1) / max(1, n - 1))
        py = y + h - 1 - int(vals[i] * (h - 2))
        pts.append((px, py))
    cv2.polylines(image, [np.array(pts, dtype=np.int32)], False, WARNING, 1, cv2.LINE_AA)
