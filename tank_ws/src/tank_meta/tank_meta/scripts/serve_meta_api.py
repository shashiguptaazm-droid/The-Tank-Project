#!/usr/bin/env python3
"""Thin re-export of serve_meta_api from within the tank_meta Python package.

Lives at tank_meta/tank_meta/scripts/ so ``import tank_meta.scripts.serve_meta_api``
works for programmatic callers (tests, TankOS).  Loads the canonical source from
the outer scripts/ directory and exec's it into *this* module's namespace so that
test patching of ``_DB_PATH`` and ``_STORE`` takes effect on the live module globals.
"""

import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))

# Path to outer scripts: tank_meta/tank_meta/scripts → tank_meta/scripts
_OUTER_SCRIPTS = _os.path.abspath(_os.path.join(_HERE, "..", "..", "scripts"))

# The package __init__ already inserted the ROS2 package root onto sys.path,
# so tank_meta.meta_store is importable.  Load the outer module wholesale.
_SOURCE = _os.path.join(_OUTER_SCRIPTS, "serve_meta_api.py")
with open(_SOURCE) as _fh:
    _code = compile(_fh.read(), _SOURCE, "exec")
    exec(_code, globals())
