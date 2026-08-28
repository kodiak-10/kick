import cv2

PRIMARY = (0x91, 0x3D, 0x0B)  # BGR for #0B3D91
WARNING = (0x00, 0x8C, 0xFF)  # BGR for #FF8C00


def draw_summary_card(image, rect, motion_issue, severity, exercise_text, alpha=0.6):
    x, y, w, h = rect
    overlay = image.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)
    cv2.rectangle(image, (x, y), (x + w, y + h), PRIMARY, 2)

    font = cv2.FONT_HERSHEY_SIMPLEX
    # OpenCV putText doesn't render CJK reliably; use English labels to avoid '?'.
    cv2.putText(image, f"Finding: {motion_issue}", (x + 12, y + 32), font, 0.8, (255, 255, 255), 2)

    # severity bar
    bar_x, bar_y, bar_w, bar_h = x + 12, y + 50, w - 24, 14
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), 1)
    fill = int(bar_w * max(0.0, min(1.0, severity)))
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), WARNING, -1)
    cv2.putText(image, f"Severity: {severity:.2f}", (x + 12, y + 80), font, 0.6, (220, 220, 220), 1)

    cv2.putText(image, f"Suggested: {exercise_text}", (x + 12, y + 110), font, 0.6, (220, 220, 220), 1)
