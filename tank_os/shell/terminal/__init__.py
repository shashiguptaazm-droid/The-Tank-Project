"""TankOS AI Terminal — headless engine + PySide6 screen.

The terminal is split into layers:

* :mod:`engine` — parse + execute + capture output via an injectable
  Executor.
* :mod:`ai_router` — natural-language to shell command mapping and
  ``explain-error`` recovery via :class:`AIManager`.
* :mod:`safety` — pure-functional command classifier (SAFE/READ/
  MUTATING/DANGEROUS/BLOCKED).
* :mod:`history` — bounded in-memory command log with lexical recall.
* :mod:`cli` — REPL front-end usable from the dev-sandbox simulation
  loop (no Qt required).
* The PySide6 screen lives at :mod:`tank_os.windows.terminal_screen`
  and wires the engine into a Qt UI.
"""
