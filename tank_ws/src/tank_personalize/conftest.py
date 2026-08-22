import os
import sys

# Make `tank_personalize` importable when pytest is invoked from within
# this package directory (mirrors the convention used by other tank_ws
# packages — see `tank_task/conftest.py`).
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
