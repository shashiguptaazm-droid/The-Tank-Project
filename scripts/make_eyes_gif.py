#!/usr/bin/env python3
"""Generate an animated GIF of the tank's dual round-eye expressions.

Draws two 1.28" round LCDs (GC9A01, 240x240 each) side by side with the
expressions the eye firmware supports: happy, alert, blink, neutral, surprise.
Output: assets/gifs/eyes_expressions.gif
"""
import os
import sys
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QGuiApplication, QPainter, QColor, QBrush, QPen, QPixmap, QRadialGradient,
    QImage, QPainterPath, QFont,
)
from PySide6.QtCore import QTimer, QEventLoop

EYE_SIZE = 240          # 1.28" 240x240 per eye
MARGIN = 30             # gap between eyes / around the canvas
CANVAS_W = EYE_SIZE * 2 + MARGIN * 3
CANVAS_H = EYE_SIZE + MARGIN * 2 + 40  # +40 for the label bar

BG = QColor(10, 12, 20)          # TankOS dark background
SCREEN = QColor(14, 18, 30)      # LCD bezel
EYE_WHITE = QColor(230, 238, 255)
IRIS = QColor(64, 220, 255)      # cyan iris (TankOS accent)
PUPIL = QColor(8, 10, 18)
GLINT = QColor(255, 255, 255)
RING = QColor(30, 42, 70)


def draw_eye(painter, cx, cy, r, pupil_dx, pupil_dy, pupil_scale=1.0, lid=0.0):
    """Draw one eye. lid 0..1 (1 = fully closed). pupil_dx/dy -1..1 look dir."""
    # sclera
    painter.setBrush(QBrush(EYE_WHITE))
    painter.setPen(QPen(RING, 10))
    painter.drawEllipse(QPointF(cx, cy), r, r)
    # iris + pupil (offset by gaze direction)
    ir = r * 0.48
    ix = cx + pupil_dx * r * 0.18
    iy = cy + pupil_dy * r * 0.18
    grad = QRadialGradient(QPointF(ix - ir * 0.3, iy - ir * 0.3), ir * 1.4)
    grad.setColorAt(0.0, QColor(120, 235, 255))
    grad.setColorAt(0.7, IRIS)
    grad.setColorAt(1.0, QColor(30, 140, 190))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPointF(ix, iy), ir, ir)
    # pupil
    pr = ir * 0.45 * pupil_scale
    painter.setBrush(QBrush(PUPIL))
    painter.drawEllipse(QPointF(ix, iy), pr, pr)
    # glint
    painter.setBrush(QBrush(GLINT))
    painter.drawEllipse(QPointF(ix - ir * 0.35, iy - ir * 0.4), pr * 0.28, pr * 0.28)
    # eyelid (covers from top)
    if lid > 0:
        lid_h = r * 2.1 * lid
        painter.setBrush(QBrush(SCREEN))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(cx - r * 1.2, cy - r * 1.3, r * 2.4, lid_h))


def render_frame(expr, frame_idx, frames_per_expr=16, total_exprs=5):
    """Render one frame. expr: index 0..4."""
    img = QImage(CANVAS_W, CANVAS_H, QImage.Format_RGB32)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    names = ["HAPPY", "ALERT", "BLINK", "NEUTRAL", "SURPRISE"]
    t = frame_idx / frames_per_expr  # 0..1 progress within this expression

    # per-expression parameters
    lid = 0.0
    gaze = (0.0, 0.0)
    pupil = 1.0
    if expr == 0:      # HAPPY: eyes closed into arcs (happy lids) + slight up gaze
        lid = 0.55 + 0.25 * abs((frame_idx - frames_per_expr / 2) / (frames_per_expr / 2))
        gaze = (0.0, -0.4)
    elif expr == 1:    # ALERT: wide, gaze sweeps side to side
        gaze = (0.6 * __import__("math").sin(t * 6.28), 0.0)
        pupil = 0.85
    elif expr == 2:    # BLINK: lid sweeps 0 -> 1 -> 0
        lid = max(0.0, 1.0 - abs(t - 0.5) * 4.0) if t > 0.25 else 0.0
    elif expr == 3:    # NEUTRAL: calm, small pupil, slow gaze
        gaze = (0.25 * __import__("math").sin(t * 3.14), 0.15 * __import__("math").cos(t * 3.14))
    elif expr == 4:    # SURPRISE: big pupil, wide
        pupil = 1.25
        gaze = (0.0, 0.0)

    # label bar
    p.setPen(QPen(QColor(200, 210, 235)))
    font = QFont("DejaVu Sans", 15, QFont.Bold)
    p.setFont(font)
    label = names[expr]
    fm = p.fontMetrics()
    p.drawText(int((CANVAS_W - fm.horizontalAdvance(label)) / 2), CANVAS_H - 16, label)

    # bezel panels
    bz = EYE_SIZE + 40
    for ex in range(2):
        x = MARGIN + ex * (EYE_SIZE + MARGIN)
        p.setBrush(QBrush(SCREEN))
        p.setPen(QPen(QColor(40, 54, 86), 6))
        p.drawRoundedRect(QRectF(x, MARGIN, EYE_SIZE, EYE_SIZE), 28, 28)

    # eyes
    cx1 = MARGIN + EYE_SIZE / 2
    cx2 = MARGIN + EYE_SIZE + MARGIN + EYE_SIZE / 2
    cy = MARGIN + EYE_SIZE / 2
    draw_eye(p, cx1, cy, EYE_SIZE * 0.42, *gaze, pupil, lid)
    draw_eye(p, cx2, cy, EYE_SIZE * 0.42, *gaze, pupil, lid)

    p.end()
    return img


def main():
    os.makedirs("assets/gifs", exist_ok=True)
    app = QGuiApplication(sys.argv)

    frames = []
    exprs = [0, 0, 1, 2, 3, 4, 3]  # happy, happy, alert, blink, neutral, surprise, neutral
    for expr in exprs:
        for i in range(14):
            frames.append(render_frame(expr, i))

    # save each frame as png then assemble with ImageMagick (better GIF quality)
    os.makedirs("/tmp/eye_frames", exist_ok=True)
    for i, f in enumerate(frames):
        f.save(f"/tmp/eye_frames/f{i:03d}.png")

    import subprocess
    subprocess.run([
        "convert", "-delay", "6", "-loop", "0",
        *[f"/tmp/eye_frames/f{i:03d}.png" for i in range(len(frames))],
        "assets/gifs/eyes_expressions.gif",
    ], check=True)
    print("done -> assets/gifs/eyes_expressions.gif")


if __name__ == "__main__":
    main()
