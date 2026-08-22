"""Orchestrator factory — picks the matching orchestrator for a mode name.

Modes
-----
- ``"rotation"`` (default) — :class:`RotationOrchestrator`
- ``"ensemble"`` — :class:`EnsembleOrchestrator`
- ``"refinement"`` — :class:`RefinementOrchestrator`
- ``"auto_train"`` — :class:`AutoTrainOrchestrator`

Mode strings are case-insensitive. Unknown modes fall back to
:class:`RotationOrchestrator` (and log a warning).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Type

from .orchestrators.base import BaseOrchestrator
from .orchestrators.rotation import RotationOrchestrator

# Optional orchestrators — present if the corresponding modules shipped,
# absent (and the mode falls back to rotation) if not yet implemented.
# These are re-exported from ``tank_assistant.evolution`` so callers
# get one consistent namespace regardless of which subset shipped.
try:
    from .orchestrators.ensemble import EnsembleOrchestrator
    ENSEMBLE_OK = True
except ImportError:                                          # pragma: no cover
    EnsembleOrchestrator = None                              # type: ignore[assignment]
    ENSEMBLE_OK = False
try:
    from .orchestrators.refinement import RefinementOrchestrator
    REFINEMENT_OK = True
except ImportError:                                          # pragma: no cover
    RefinementOrchestrator = None                            # type: ignore[assignment]
    REFINEMENT_OK = False
try:
    from .orchestrators.auto_train import AutoTrainOrchestrator
    AUTO_TRAIN_OK = True
except ImportError:                                          # pragma: no cover
    AutoTrainOrchestrator = None                             # type: ignore[assignment]
    AUTO_TRAIN_OK = False


_LOG = logging.getLogger("tank_assistant.evolution.factory")


# String identifiers — exported for ROS parameter parsing.
class OrchestratorMode:
    ROTATION = "rotation"
    ENSEMBLE = "ensemble"
    REFINEMENT = "refinement"
    AUTO_TRAIN = "auto_train"


_REGISTRY: Dict[str, Type[BaseOrchestrator]] = {
    OrchestratorMode.ROTATION: RotationOrchestrator,
}
if ENSEMBLE_OK:
    _REGISTRY[OrchestratorMode.ENSEMBLE] = EnsembleOrchestrator
if REFINEMENT_OK:
    _REGISTRY[OrchestratorMode.REFINEMENT] = RefinementOrchestrator
if AUTO_TRAIN_OK:
    _REGISTRY[OrchestratorMode.AUTO_TRAIN] = AutoTrainOrchestrator


__all__ = [
    "build_orchestrator", "OrchestratorMode",
    "EnsembleOrchestrator", "RefinementOrchestrator", "AutoTrainOrchestrator",
    "ENSEMBLE_OK", "REFINEMENT_OK", "AUTO_TRAIN_OK",
]


def build_orchestrator(mode: Optional[str] = None, *,
                       providers: Optional[list] = None,
                       **kwargs: Any) -> BaseOrchestrator:
    """Build an orchestrator for the given mode.

    Parameters
    ----------
    mode
        One of :class:`OrchestratorMode`'s values. ``None`` reads the
        ``TANK_EVOLUTION_MODE`` env var, defaulting to ``"rotation"``.
    providers
        Optional pre-built provider instances (skips registry lookup).
        When ``None`` (the typical case), the orchestrator discovers
        providers from the registry + key availability.
    kwargs
        Forwarded to the orchestrator constructor.

    Returns
    -------
    BaseOrchestrator
        A concrete orchestrator subclass instance.
    """
    resolved = (mode or os.environ.get(
        "TANK_EVOLUTION_MODE", OrchestratorMode.ROTATION)).lower()
    cls = _REGISTRY.get(resolved)
    if cls is None:
        _LOG.warning(
            "unknown orchestrator mode %r; falling back to rotation",
            resolved)
        cls = RotationOrchestrator
    return cls(providers=providers, **kwargs)


# Default singleton — for use by external_llm_client.py without arg passing.
_default: Optional[BaseOrchestrator] = None


def get_default_orchestrator(**kwargs: Any) -> BaseOrchestrator:
    """Lazy-initialized singleton for the default orchestrator."""
    global _default
    if _default is None:
        _default = build_orchestrator(**kwargs)
    return _default


def reset_default_orchestrator() -> None:
    """Drop the cached singleton (used after config changes)."""
    global _default
    _default = None
