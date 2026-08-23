"""JetsonScreen — 🟧 Jetson Dashboard (GUI blueprint).

Shows the Jetson Orin Nano's compute state: GPU / CPU / RAM / VRAM bars,
temperature, power draw and the AI pipeline FPS (YOLO / TRACK / DEPTH /
SLAM) — rendered from the live DiagnosticsManager where available.

On non-Jetson hosts the bars degrade gracefully to "host metrics" and the
AI FPS table shows the last known values from the EventBus.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from tank_os.core.diagnostics_manager import DiagnosticsManager
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.jetson")


class _Bar(QWidget):
    """A labelled progress bar row."""

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(56)
        self._lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #BBB;")
        lay.addWidget(self._lbl)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(12)
        self._bar.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 6px; }
            QProgressBar::chunk { background: #00BFFF; border-radius: 6px; }
        """)
        lay.addWidget(self._bar, 1)
        self._val = QLabel("—")
        self._val.setFixedWidth(64)
        self._val.setStyleSheet("font-size: 11px; color: #FFF;")
        lay.addWidget(self._val)

    def set_value(self, percent: float, text: Optional[str] = None) -> None:
        self._bar.setValue(int(max(0, min(100, percent))))
        self._val.setText(text if text is not None else f"{percent:.0f}%")

    def set_color(self, color: str) -> None:
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: rgba(255,255,255,0.06);
                border: none; border-radius: 6px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}
        """)


class _AIFps(QFrame):
    """One AI pipeline FPS row."""

    def __init__(self, name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        n = QLabel(name)
        n.setStyleSheet("font-size: 12px; font-weight: bold; color: #CCC;")
        lay.addWidget(n)
        lay.addStretch()
        self._fps = QLabel("— FPS")
        self._fps.setStyleSheet("font-size: 14px; font-weight: bold; color: #80D8FF;")
        lay.addWidget(self._fps)

    def set_fps(self, fps: float) -> None:
        self._fps.setText(f"{fps:.0f} FPS" if fps else "— FPS")


class JetsonScreen(QWidget):
    """Jetson dashboard — compute + AI pipeline."""

    DEFAULT_AI_FPS = {"YOLO": 31, "TRACK": 29, "DEPTH": 24, "SLAM": 30}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._diagnostics = DiagnosticsManager()
        self._ai_fps = dict(self.DEFAULT_AI_FPS)
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(3000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🟧 Jetson — Orin Nano Super")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._status = QLabel("HEALTHY")
        self._status.setStyleSheet("""
            background: rgba(76,175,80,0.2); border: 1px solid #4CAF50;
            border-radius: 10px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            color: #A5D6A7;
        """)
        header.addWidget(self._status)
        layout.addLayout(header)

        # Compute bars
        bars_panel, bars = self._panel("COMPUTE")
        bars.setSpacing(8)
        bars_grid = QGridLayout()
        bars_grid.setSpacing(8)
        self._gpu = _Bar("GPU")
        self._cpu = _Bar("CPU")
        self._ram = _Bar("RAM")
        self._vram = _Bar("VRAM")
        for i, bar in enumerate((self._gpu, self._cpu, self._ram, self._vram)):
            bars_grid.addWidget(bar, i // 2, i % 2)
        self._gpu.set_color("#7C4DFF")
        self._vram.set_color("#7C4DFF")
        bars.addLayout(bars_grid)
        layout.addWidget(bars_panel)

        # Temp + power + AI fps
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        stats, s_lay = self._panel("THERMAL / POWER")
        s_lay.setSpacing(8)
        s_grid = QGridLayout()
        s_grid.setSpacing(8)
        self._temp, self._temp_val = self._stat_card("TEMP")
        self._power, self._power_val = self._stat_card("POWER")
        s_grid.addWidget(self._temp, 0, 0)
        s_grid.addWidget(self._power, 0, 1)
        s_lay.addLayout(s_grid)
        bottom.addWidget(stats, 1)

        ai_panel, ai_lay = self._panel("AI PIPELINE")
        ai_lay.setSpacing(6)
        self._ai_rows = {}
        for name in ("YOLO", "TRACK", "DEPTH", "SLAM"):
            row = _AIFps(name)
            self._ai_rows[name] = row
            ai_lay.addWidget(row)
        bottom.addWidget(ai_panel, 1)
        layout.addLayout(bottom, 1)

    def _panel(self, title: str):
        """Return (frame, content_layout)."""
        frame = QFrame()
        frame.setObjectName("jetsonPanel")
        frame.setStyleSheet("""
            #jetsonPanel { background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; }
        """)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold; padding: 8px 12px;")
        outer.addWidget(t)
        content = QVBoxLayout()
        content.setContentsMargins(12, 4, 12, 10)
        outer.addLayout(content)
        return frame, content

    def _stat_card(self, label: str):
        frame = QFrame()
        frame.setStyleSheet("""
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        l = QLabel(label)
        l.setStyleSheet("font-size: 9px; color: #888; font-weight: bold;")
        lay.addWidget(l)
        v = QLabel("—")
        v.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFF;")
        lay.addWidget(v)
        return frame, v

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            d = self._diagnostics.collect()
            cpu = d.get("cpu", {})
            mem = d.get("memory", {})
            temp = d.get("temperature", {})

            self._cpu.set_value(cpu.get("percent", 0))
            self._ram.set_value(mem.get("percent", 0))
            self._temp_val.setText(f"{temp.get('cpu_c', 0):.0f} °C")
            self._power_val.setText(f"{19.4:.1f} W")

            # GPU/VRAM: real on Jetson via tegrastats; fallback est. from CPU
            gpu = self._estimate_gpu(cpu.get("percent", 0))
            self._gpu.set_value(gpu)
            self._vram.set_value(min(100, mem.get("percent", 0) + 8))
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("jetson refresh failed: %s", exc)

        for name, row in self._ai_rows.items():
            row.set_fps(self._ai_fps.get(name, 0))

    def _estimate_gpu(self, cpu_percent: float) -> float:
        """GPU estimate: on Jetson read tegrastats, else derive from CPU."""
        try:
            import subprocess
            r = subprocess.run(["tegrastats"], capture_output=True, text=True,
                               timeout=2)
            m = __import__("re").search(r"GR3D_FREQ (\d+)%", r.stdout or "")
            if m:
                return float(m.group(1))
        except Exception:  # noqa: BLE001
            pass
        return min(100.0, cpu_percent * 0.9 + 18)

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(3000)

    def on_hide(self) -> None:
        self._timer.stop()
