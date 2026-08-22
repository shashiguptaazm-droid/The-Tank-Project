"""pytest conftest — ensures the tank_patrol package is importable."""
import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
