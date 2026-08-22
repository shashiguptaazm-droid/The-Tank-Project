"""tank_offload.scripts \u2014 CLI-first entry points.

Per STATUS.md \u00a79 design rule 8, every module ships a ``scripts/``
wrapper. This sub-package hosts:

* ``run_offload``     \u2014 the uvicorn launcher the systemd unit invokes.
* ``tank_offload_cli`` \u2014 a ``tank-offload`` CLI tool that hits the
  HTTP API (when reachable) or falls back to direct policy walks
  (dry-run mode) so the user can introspect the system offline.
"""
