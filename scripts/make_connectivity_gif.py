#!/usr/bin/env python3
"""Generate an animated GIF showing the tank network failover hierarchy:
WiFi (primary) -> 4G LTE (EG800AK) -> Hotspot -> Tailscale mesh (fallback).
Output: assets/gifs/network_failover.gif
"""
import math
import os
import subprocess
import sys
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QPainter,
                           QPen, QBrush)

W, H = 760, 520
BG = QColor(10, 12, 20)
CARD = QColor(21, 29, 56)
ACCENT = QColor(52, 211, 153)   # green = active
WARN = QColor(251, 191, 36)     # amber = fallback
PINK = QColor(244, 114, 182)    # tailscale
GRAY = QColor(107, 115, 154)    # idle

STEPS = [
    ("WiFi", "AirFiber-X9nxU1", ACCENT, "primary link · 192.168.31.x"),
    ("4G LTE", "EG800AK-CN", WARN, "cellular backup · registered 64%"),
    ("Hotspot", "tank-network", WARN, "phone hotspot failover"),
    ("Tailscale", "mesh 100.x", PINK, "boot-enabled fallback"),
]

WAVE = "#22d3ee"  # cyan accents


def draw_frame(step_idx, t):
    """t: 0..1 progress through this step's pulse."""
    img = QImage(W, H, QImage.Format_RGB32)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    # title
    p.setPen(QPen(QColor(238, 242, 255)))
    f = QFont("DejaVu Sans", 17, QFont.Bold)
    p.setFont(f)
    p.drawText(QRectF(0, 18, W, 30), Qt.AlignHCenter, "TANK NETWORK — FAILOVER HIERARCHY")

    # tank icon (top center)
    tx, ty = W / 2, 110
    p.setBrush(QBrush(QColor(30, 41, 68)))
    p.setPen(QPen(QColor(WAVE), 3))
    p.drawRoundedRect(QRectF(tx - 46, ty - 26, 92, 52), 10, 10)
    # eyes on tank
    for ex in (-20, 20):
        p.setBrush(QBrush(QColor(230, 238, 255)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(tx + ex, ty - 2), 12, 12)
        p.setBrush(QBrush(QColor(20, 30, 60)))
        p.drawEllipse(QPointF(tx + ex, ty - 2), 5, 5)
    p.setPen(QPen(QColor(238, 242, 255), 2))
    p.drawArc(QRectF(tx - 30, ty + 6, 60, 18), 0, 180 * 16)
    # wheels
    p.setBrush(QBrush(QColor(20, 30, 60)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(tx - 34, ty + 26), 9, 9)
    p.drawEllipse(QPointF(tx + 34, ty + 26), 9, 9)

    # step cards
    y0 = 190
    card_h = 62
    for i, (name, detail, color, note) in enumerate(STEPS):
        y = y0 + i * (card_h + 12)
        active = (i == step_idx)
        if active:
            p.setPen(QPen(color, 3))
            p.setBrush(QBrush(CARD.lighter(120)))
        else:
            p.setPen(QPen(GRAY, 1))
            p.setBrush(QBrush(CARD))
        p.drawRoundedRect(QRectF(90, y, 580, card_h), 10, 10)

        # status dot with pulse
        cx, cy = 130, y + card_h / 2
        if active:
            r = 9 + 7 * math.sin(t * math.pi)  # pulse
            glow = QColor(color)
            glow.setAlpha(60)
            p.setBrush(QBrush(glow))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(cx, cy), 8, 8)
        else:
            p.setBrush(QBrush(GRAY))
            p.drawEllipse(QPointF(cx, cy), 6, 6)

        # step number
        p.setPen(QPen(QColor(139, 147, 181)))
        f2 = QFont("DejaVu Sans", 11)
        p.setFont(f2)
        p.drawText(QRectF(150, y + 8, 30, 20), Qt.AlignLeft, f"{i+1}.")

        # name
        p.setPen(QPen(color if active else QColor(203, 213, 240)))
        f3 = QFont("DejaVu Sans", 14, QFont.Bold)
        p.setFont(f3)
        p.drawText(QRectF(180, y + 6, 240, 24), Qt.AlignLeft, name)

        # detail
        p.setPen(QPen(QColor(139, 147, 181)))
        p.setFont(f2)
        p.drawText(QRectF(180, y + 32, 280, 20), Qt.AlignLeft, detail)

        # note / status
        if active:
            p.setPen(QPen(color))
            p.drawText(QRectF(430, y + 18, 220, 24), Qt.AlignRight | Qt.AlignVCenter, "● ACTIVE")

    # footer
    p.setPen(QPen(QColor(107, 115, 154)))
    f4 = QFont("DejaVu Sans", 10)
    p.setFont(f4)
    p.drawText(QRectF(0, H - 30, W, 20), Qt.AlignHCenter,
               "Auto-failover: WiFi down → 4G LTE → Hotspot → Tailscale mesh (all boot-enabled)")

    p.end()
    return img


def main():
    os.makedirs("assets/gifs", exist_ok=True)
    app = QGuiApplication(sys.argv)
    os.makedirs("/tmp/net_frames", exist_ok=True)
    frames = []
    for step in range(4):
        for i in range(16):
            frames.append(draw_frame(step, i / 16))
    for i, f in enumerate(frames):
        f.save(f"/tmp/net_frames/n{i:03d}.png")
    subprocess.run([
        "convert", "-delay", "7", "-loop", "0",
        *[f"/tmp/net_frames/n{i:03d}.png" for i in range(len(frames))],
        "assets/gifs/network_failover.gif",
    ], check=True)
    print("done -> assets/gifs/network_failover.gif")


if __name__ == "__main__":
    main()
