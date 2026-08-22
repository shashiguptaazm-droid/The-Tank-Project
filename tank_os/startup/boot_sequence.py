"""TankOS Boot Sequence — orchestrates the 11-step startup process."""

from __future__ import annotations
import logging, time
from typing import Any, Callable, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.boot")

BootStep = Callable[[], bool]


class BootSequence:
    """Orchestrates the TankOS startup sequence step by step."""

    STEPS = [
        "init_logging",
        "load_config",
        "init_hardware",
        "start_ros",
        "verify_services",
        "init_plugins",
        "init_gui",
        "start_ai",
        "start_voice",
        "open_dashboard",
        "accept_input",
    ]

    def __init__(self) -> None:
        self.bus = EventBus()
        self._handlers: Dict[str, BootStep] = {}
        self._results: Dict[str, bool] = {}
        self._aborted = False

    def register(self, step: str, handler: BootStep) -> None:
        """Register a handler for a boot step."""
        self._handlers[step] = handler

    def run(self) -> bool:
        """Execute the boot sequence. Returns True if all steps succeeded."""
        logger.info("=== TankOS Boot Sequence Starting ===")
        self.bus.emit(Event("boot_started", {}, source="boot_sequence"))

        for step_name in self.STEPS:
            if self._aborted:
                logger.warning("Boot aborted at step: %s", step_name)
                self.bus.emit(Event("boot_aborted", {
                    "step": step_name,
                }, source="boot_sequence"))
                return False

            logger.info("Boot step [%s]...", step_name)
            self.bus.emit(Event("boot_step", {
                "step": step_name,
                "index": self.STEPS.index(step_name),
                "total": len(self.STEPS),
            }, source="boot_sequence"))

            handler = self._handlers.get(step_name)
            if handler is None:
                logger.warning("No handler for step %s, skipping", step_name)
                self._results[step_name] = True
                continue

            try:
                success = handler()
                self._results[step_name] = success
                if not success:
                    logger.error("Boot step FAILED: %s", step_name)
                    self.bus.emit(Event("boot_step_failed", {
                        "step": step_name,
                    }, source="boot_sequence"))
            except Exception as exc:
                logger.exception("Boot step %s crashed: %s", step_name, exc)
                self._results[step_name] = False
                self.bus.emit(Event("boot_step_crashed", {
                    "step": step_name,
                    "error": str(exc),
                }, source="boot_sequence"))

        all_ok = all(self._results.values())
        if all_ok:
            self.bus.emit(Event("boot_complete", {
                "steps": self._results,
                "failed": [s for s, ok in self._results.items() if not ok],
            }, source="boot_sequence"))
            logger.info("=== TankOS Boot Complete ===")
        else:
            self.bus.emit(Event("boot_complete_with_errors", {
                "steps": self._results,
                "failed": [s for s, ok in self._results.items() if not ok],
            }, source="boot_sequence"))
            logger.warning("=== TankOS Boot Complete (with %d errors) ===",
                           sum(1 for v in self._results.values() if not v))
        return all_ok

    def abort(self) -> None:
        self._aborted = True

    @property
    def results(self) -> Dict[str, bool]:
        return dict(self._results)
