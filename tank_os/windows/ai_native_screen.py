"""AINativeScreen — 🧠 TankOS Native AI (100-AI plan).

Capability-based AI as an OS subsystem: applications ask "give me object
detection", TankOS decides model / device / precision / fallback.

Shows: capability map, model registry with health + fallback, inference
scheduler load, the capability-run API in action, and the AI Executive
(NL command → intent → subtasks → verify → recover).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.ai.native_core import TankAIService

logger = logging.getLogger("tank_os.windows.ainative")


class AINativeScreen(QWidget):
    """Native AI — capability-based, model-agnostic."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ai = TankAIService()
        self._seed_world()
        self._build_ui()
        self._demo()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2500)

    def _seed_world(self) -> None:
        w = self._ai.world
        if not w._objects:
            w.observe("chair", "north-doorway", 0.9)
            w.observe("bottle", "room-a", 0.86)
            w.observe("person", "corridor-b", 0.94)
            w.observe("charging-station", "dock", 0.97)
            w.set_location_confidence("north corridor", 0.96)
            w.set_location_confidence("room a", 0.88)
            w.set_location_confidence("behind obstacle", 0.41)
            w.set_location_confidence("stair area", 0.22)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🧠 TankOS Native AI — capability-based")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._health_badge = QLabel("")
        self._health_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._health_badge)
        layout.addLayout(header)

        # Capability map
        cap_label = QLabel("CAPABILITY MAP — apps ask for capabilities, TankOS picks model/device/precision")
        cap_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(cap_label)
        self._caps = QLabel("")
        self._caps.setWordWrap(True)
        self._caps.setStyleSheet("""
            background: rgba(255,255,255,0.03); border-radius: 10px;
            padding: 8px 12px; font-size: 10px; color: #CCC; font-family: Monospace;
        """)
        layout.addWidget(self._caps)

        body = QHBoxLayout()
        body.setSpacing(10)

        # Model registry
        models = QFrame()
        models.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        m_lay = QVBoxLayout(models)
        m_lay.setContentsMargins(12, 10, 12, 10)
        m_t = QLabel("MODEL REGISTRY — HEALTH + FALLBACK")
        m_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        m_lay.addWidget(m_t)
        self._models = QLabel("")
        self._models.setWordWrap(True)
        self._models.setStyleSheet("font-size: 10px; color: #CCC;"
                                   " background: transparent;")
        m_lay.addWidget(self._models)
        self._load = QProgressBar()
        self._load.setRange(0, 100)
        self._load.setTextVisible(True)
        self._load.setFixedHeight(14)
        self._load.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 7px; text-align: center;
                font-size: 9px; font-weight: bold; color: #FFF; }
            QProgressBar::chunk { background: #7C4DFF; border-radius: 7px; }
        """)
        m_lay.addWidget(self._load)
        body.addWidget(models, 1)

        # Capability run + executive
        right = QVBoxLayout()
        right.setSpacing(10)
        run = QFrame()
        run.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        r_lay = QVBoxLayout(run)
        r_lay.setContentsMargins(12, 10, 12, 10)
        r_t = QLabel("⚡ CAPABILITY API — 'give me object detection'")
        r_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        r_lay.addWidget(r_t)
        self._run = QLabel("")
        self._run.setWordWrap(True)
        self._run.setStyleSheet("font-size: 10px; color: #CCC;"
                                " font-family: Monospace; background: transparent;")
        r_lay.addWidget(self._run)
        btn = QPushButton("🔄 RUN CAPABILITY")
        btn.setStyleSheet("""
            QPushButton { background: rgba(124,77,255,0.18);
                border: 1px solid rgba(124,77,255,0.45); border-radius: 8px;
                padding: 7px 12px; color: #C9A8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(124,77,255,0.3); }
        """)
        btn.clicked.connect(self._demo)
        r_lay.addWidget(btn)
        right.addWidget(run)

        exec_f = QFrame()
        exec_f.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        e_lay = QVBoxLayout(exec_f)
        e_lay.setContentsMargins(12, 10, 12, 10)
        e_t = QLabel("🤖 AI EXECUTIVE — 'Inspect the entire room'")
        e_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        e_lay.addWidget(e_t)
        self._exec = QLabel("")
        self._exec.setWordWrap(True)
        self._exec.setStyleSheet("font-size: 10px; color: #CCC;"
                                 " font-family: Monospace; background: transparent;")
        e_lay.addWidget(self._exec)
        right.addWidget(exec_f)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        # World intelligence
        world = QFrame()
        world.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        w_lay = QVBoxLayout(world)
        w_lay.setContentsMargins(12, 10, 12, 10)
        w_t = QLabel("🧠 WORLD INTELLIGENCE — semantic world model + memory")
        w_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        w_lay.addWidget(w_t)
        self._world = QLabel("")
        self._world.setWordWrap(True)
        self._world.setStyleSheet("font-size: 10px; color: #CCC;"
                                  " background: transparent;")
        w_lay.addWidget(self._world)
        layout.addWidget(world)

    # ------------------------------------------------------------- demo
    def _demo(self) -> None:
        res = self._ai.run_capability("object_detection")
        self._run.setText(
            f"$ tank.ai.run('object_detection')\n"
            f"device={res.get('device')} · model={res.get('model')} · "
            f"precision={res.get('precision')} · fps={res.get('fps')}\n"
            + "\n".join(f"  {d['label']:<10} {d['confidence']:.0%}"
                        for d in res.get("detections", [])[:4]))

    def refresh(self) -> None:
        ai = self._ai
        health = ai.registry.health_report()
        self._health_badge.setText(
            f"MODELS {health['healthy']}/{health['total']} HEALTHY")

        # Capability map
        caps = ai.capabilities()
        lines = ["PERCEPTION: " + ", ".join(caps["perception"]),
                 "WORLD: " + ", ".join(caps["world"]),
                 "NAV: " + ", ".join(caps["navigation"]),
                 "LANGUAGE: " + ", ".join(caps["language"])]
        self._caps.setText("\n".join(lines))

        # Models
        m_lines = []
        for m in ai.registry.list():
            mark = "✓" if m.healthy else "✗"
            fallback = f" → {m.fallback_to}" if m.fallback_to else ""
            m_lines.append(
                f"{mark} {m.name:<14} [{m.task:<22}] {m.device:<6} "
                f"{m.precision:<5} {m.fps:.0f}fps {m.accuracy:.0%}{fallback}")
        self._models.setText("\n".join(m_lines))
        load = ai.scheduler.load()
        self._load.setValue(int(load["jetson"]))
        self._load.setFormat(f"JETSON INFERENCE LOAD: {load['jetson']:.0f}%")

        # Executive (re-run periodically for a live feel)
        if int(time.time()) % 6 == 0 and not ai.executive.goals():
            pass
        goal = ai.executive.goals()
        if not goal:
            result = ai.executive.run("Inspect the entire room")
            steps = "\n".join(f"  {'✓' if t['status'] == 'done' else '·'} "
                              f"{t['description']}" for t in result["steps"])
            self._exec.setText(
                f"INTENT: {result['intent']} · {result['summary']}\n{steps}")
        else:
            result = {"intent": goal[-1]["intent"]}
            tasks = ai.executive.tasks()[-goal[-1]["tasks"]:]
            steps = "\n".join(f"  {'✓' if t.status == 'done' else '·'} "
                              f"{t.description}" for t in tasks)
            self._exec.setText(f"INTENT: {result['intent']}\n{steps}")

        # World
        w = ai.world
        q = w.query("What objects are near the north doorway?", near="north-doorway")
        self._world.setText(
            f"$ tank.ai.world.query('What objects are near the north doorway?')\n"
            f"→ {q['objects']} (count {q['count']})\n"
            f"object memory: {w.summary()['objects']} · locations: "
            f"{w.summary()['locations']} · unknown areas: "
            f"{', '.join(w.unknown_areas()) or 'none'}")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2500)

    def on_hide(self) -> None:
        self._timer.stop()
