"""Load ``content/hardware.json`` rows into :class:`MetaStore`."""
from __future__ import annotations

import json
import os
from typing import List

from .meta_store import HardwareRow, MetaStore


def load_hardware_file(path: str, store: MetaStore) -> int:
    """Read a hardware.json file and push every component to ``store``.

    Returns the number of components added. Missing file yields 0.
    """
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    components = data.get("components") or []
    n = 0
    for c in components:
        store.upsert_hardware(HardwareRow(
            component=str(c.get("component", "")),
            kind=str(c.get("kind", "")),
            bus=str(c.get("bus", "")),
            pin=str(c.get("pin", "")),
            driver=str(c.get("driver", "")),
            notes=str(c.get("notes", "")),
        ))
        n += 1
    return n


def list_components(path: str) -> List[str]:
    """Read-only convenience for the CLI tab-completion."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [str(c.get("component", "")) for c in (data.get("components") or [])]
