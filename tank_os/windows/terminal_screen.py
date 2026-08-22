"""TerminalScreen — PySide6 ``QWidget`` for the AI-powered terminal.

Layout::

    ┌──────────────────────────────────────────────┐
    │  🤖 AI Terminal             ● idle  [esc]    │
    ├──────────────────────────────────────────────┤
    │                                              │
    │  <QPlainTextEdit — read-only output>         │
    │  (monospace, monitor-green, on dark bg)      │
    │                                              │
    ├──────────────────────────────────────────────┤
    │  > QLineEdit input                           │
    │  [Confirm] [Cancel] hidden until needed      │
    └──────────────────────────────────────────────┘

Design choices worth knowing:

* Output is delivered by :class:`_PtyOutputReader` on a background
  :class:`QThread`. Two inner threads drain stdout and stderr
  respectively, and emit a Qt :class:`Signal` per line. This means a
  long-running command with megabytes of output never blocks the GUI
  thread.
* ``Ctrl+C`` sends a SIGINT to the running process via ``os.killpg``
  on the child's process group; it does NOT close the screen. ``Esc``
  navigates back to Home.
* ``start_new_session=True`` replaces the older ``preexec_fn``
  pattern, which is documented as unsafe under multi-threaded parents
  (Qt's main loop is one such parent).
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus
from tank_os.shell.terminal.engine import TerminalEngine

logger = logging.getLogger("tank_os.windows.terminal")


# ───────────────────────────────────────────────────────────────────────────
# Worker thread — drain stdout + stderr without blocking the Qt main loop.
# ───────────────────────────────────────────────────────────────────────────

class _PtyOutputReader(QThread):
    """Background thread that reads subprocess pipes into Qt signals.

    A separate inner thread drains stderr so a chatty child can't
    block writing to stderr while we're draining stdout (which would
    deadlock the child). Each emitted line carries an optional
    ``color`` (empty string = use the default in the screen panel).
    """

    appended = Signal(str, str)        # text, color ("" = default)
    closed = Signal(int)               # exit code

    def __init__(self, proc: subprocess.Popen,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._proc = proc

    def run(self) -> None:                                       # noqa: D401
        def _drain(stream, color: str) -> None:
            try:
                for line in iter(stream.readline, ""):
                    if line:
                        self.appended.emit(line, color)
            except (OSError, ValueError) as exc:
                # Tell the operator if a pipe read failed instead of
                # letting stderr silently truncate.
                self.appended.emit(
                    f"[read error: {exc}]\n", "#FF5252",
                )
        t_out = threading.Thread(
            target=_drain, args=(self._proc.stdout, ""),
            name="tank-os-terminal-stdout", daemon=True,
        )
        t_err = threading.Thread(
            target=_drain, args=(self._proc.stderr, "#FF5252"),
            name="tank-os-terminal-stderr", daemon=True,
        )
        t_out.start()
        t_err.start()
        # Block here only until both drainers finish.
        t_out.join()
        t_err.join()
        rc = self._proc.wait()
        self.closed.emit(rc)


# ───────────────────────────────────────────────────────────────────────────
# The screen widget itself
# ───────────────────────────────────────────────────────────────────────────

class TerminalScreen(QWidget):
    """Full-screen AI terminal widget."""

    request_navigate_home = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._engine = TerminalEngine()
        self._proc: Optional[subprocess.Popen] = None
        self._reader: Optional[_PtyOutputReader] = None
        self._pending_command: str = ""
        self._build_ui()
        self._bus.on("terminal_blocked_by_safety", self._on_blocked)
        self._bus.on("terminal_confirmation_requested", self._on_confirmation)
        self._greet()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header ------------------------------------------------
        header = QFrame()
        header.setFixedHeight(44)
        header.setStyleSheet("background: rgba(0,0,0,0.30); color: #FFFFFF;")
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 6, 12, 6)

        title = QLabel("🤖 AI Terminal")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        h.addWidget(title)

        self._status = QLabel("● idle")
        self._status.setStyleSheet("color: #00E676; font-size: 11px;")
        h.addStretch()
        h.addWidget(self._status)

        self._esc_btn = QPushButton("⟵ Home")
        self._esc_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid "
            "rgba(255,255,255,0.15); border-radius: 6px; padding: 4px "
            "10px; color: #DDD; } QPushButton:hover { background: "
            "rgba(0,191,255,0.15); }"
        )
        self._esc_btn.clicked.connect(self.request_navigate_home.emit)
        h.addWidget(self._esc_btn)
        layout.addWidget(header)

        # --- Output ------------------------------------------------
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Monospace", 10))
        self._output.setStyleSheet(
            "QPlainTextEdit { background: #0D0D1A; color: #00E676;"
            " border: none; padding: 8px; }"
        )
        self._output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._output, 1)

        # --- Confirmation strip ------------------------------------
        self._confirm_strip = QFrame()
        self._confirm_strip.setVisible(False)
        self._confirm_strip.setStyleSheet(
            "background: rgba(255,165,0,0.10); border-top: 1px solid "
            "rgba(255,165,0,0.40); padding: 6px;"
        )
        cs = QHBoxLayout(self._confirm_strip)
        cs.setContentsMargins(12, 4, 12, 4)
        self._confirm_label = QLabel("")
        self._confirm_label.setStyleSheet("color: #FFA500; font-size: 11px;")
        cs.addWidget(self._confirm_label, 1)

        self._confirm_btn = QPushButton("Confirm [y]")
        self._confirm_btn.setStyleSheet(
            "QPushButton { background: #00E676; color: #0D0D1A; "
            "border: none; padding: 4px 12px; border-radius: 6px; "
            "font-weight: bold; } QPushButton:hover { background: #00C060; }"
        )
        self._confirm_btn.clicked.connect(self._on_confirm_yes)
        cs.addWidget(self._confirm_btn)

        self._cancel_btn = QPushButton("Cancel [N]")
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.20); color: #DDD; "
            "padding: 4px 12px; border-radius: 6px; } "
            "QPushButton:hover { background: rgba(255,82,82,0.18); }"
        )
        self._cancel_btn.clicked.connect(self._on_confirm_no)
        cs.addWidget(self._cancel_btn)
        layout.addWidget(self._confirm_strip)

        # --- Input -------------------------------------------------
        input_frame = QFrame()
        input_frame.setFixedHeight(40)
        input_frame.setStyleSheet("background: rgba(0,0,0,0.35);")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(12, 4, 12, 4)

        prompt = QLabel("❯")
        prompt.setStyleSheet("color: #00BFFF; font-size: 14px;")
        il.addWidget(prompt)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            "Type a shell command (!ls -la) or describe what you want…"
        )
        self._input.setStyleSheet(
            "QLineEdit { background: transparent; border: none; "
            "color: #FFFFFF; font-size: 12px; padding: 4px; }"
        )
        self._input.returnPressed.connect(self._on_submit)
        il.addWidget(self._input, 1)
        layout.addWidget(input_frame)

    # ------------------------------------------------------------------
    # Greeter + utility
    # ------------------------------------------------------------------
    def _greet(self) -> None:
        self._append(
            "🤖 \033[38;5;81mTankOS AI Terminal\033[0m\n"
            "  !<cmd>      run shell directly\n"
            "  <sentence>  describe a goal — AI translates\n"
            "  Ctrl+C      interrupt the running command\n"
            "  Esc         go back to Home\n"
        )

    def _append(self, text: str, *, color: Optional[str] = None) -> None:
        if color:
            text = f'<span style="color: {color};">{text}</span>'
        self._output.append(text.rstrip("\n"))
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._output.setTextCursor(cursor)

    def _set_status(self, text: str, color: str = "#00E676") -> None:
        self._status.setText(f"● {text}")
        self._status.setStyleSheet(f"color: {color}; font-size: 11px;")

    # ------------------------------------------------------------------
    # Submit + execute
    # ------------------------------------------------------------------
    def _on_submit(self) -> None:
        line = self._input.text().strip()
        if not line:
            return
        self._input.clear()
        self._append(f"❯ {line}", color="#00BFFF")
        result = self._engine.interpret(line)
        if not result.command and result.error:
            self._append(f"(error) {result.error}", color="#FF5252")
            return
        if result.error:
            self._append(result.error, color="#FF5252")
            return
        if result.pending_confirmation:
            self._pending_command = result.command
            self._confirm_label.setText(
                f"This command is "
                f"{result.safety_class.name.lower()} — confirm before "
                f"running:\n   {result.command}"
            )
            self._confirm_strip.setVisible(True)
            return
        self._run_command(result.command)

    def _run_command(self, command: str) -> None:
        self._set_status("running", "#FFA500")
        self._append(f"→ {command}", color="#AAAAAA")
        # start_new_session=True is the documented safe replacement for
        # preexec_fn=os.setsid in multi-threaded programs (Qt is one).
        self._proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(os.name == "posix"),
        )
        self._reader = _PtyOutputReader(self._proc, parent=self)
        self._reader.appended.connect(self._on_proc_chunk)
        self._reader.closed.connect(self._finish_proc)
        self._reader.start()

    def _on_proc_chunk(self, text: str, color: str) -> None:
        self._append(text, color=color or None)

    def _finish_proc(self, rc: int) -> None:
        self._proc = None
        self._reader = None
        self._append(f"(exit {rc})", color="#00E676" if rc == 0 else "#FF5252")
        self._set_status("idle", "#00E676")
        self._bus.emit(Event(
            "terminal_command_finished",
            {"command": self._pending_command or "",
             "exit_code": rc},
            source="terminal_screen",
        ))

    # ------------------------------------------------------------------
    # Confirm buttons
    # ------------------------------------------------------------------
    def _on_confirm_yes(self) -> None:
        cmd_text = self._pending_command
        self._pending_command = ""
        self._confirm_strip.setVisible(False)
        if cmd_text:
            self._run_command(cmd_text)

    def _on_confirm_no(self) -> None:
        self._pending_command = ""
        self._confirm_strip.setVisible(False)
        self._append("(cancelled by operator)", color="#FFA500")
        self._set_status("idle", "#00E676")

    def _on_blocked(self, event: Event) -> None:
        cmd = event.data.get("command", "")
        if cmd:
            self._append(f"⛔ blocked: {cmd}", color="#FF5252")

    def _on_confirmation(self, _event: Event) -> None:
        # Strip visibility is controlled by _on_submit when a pending
        # command is detected; this handler exists for symmetry so
        # subscribers can see the event without side-effects.
        pass

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:           # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.request_navigate_home.emit()
            return
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            if self._proc is not None:
                try:
                    if os.name == "posix":
                        os.killpg(self._proc.pid, signal.SIGINT)
                    else:
                        self._proc.send_signal(signal.SIGINT)
                    self._append("[Ctrl+C] SIGINT sent", color="#FFA500")
                except Exception as exc:                         # noqa: BLE001
                    self._append(f"[Ctrl+C] failed: {exc}",
                                  color="#FF5252")
            return
        super().keyPressEvent(event)
