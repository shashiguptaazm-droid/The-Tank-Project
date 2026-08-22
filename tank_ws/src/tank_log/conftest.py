"""pytest conftest — ensures tests can import tank_log by package name."""
import os
import sys

_PKG_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_SRC = _PKG_PARENT
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
