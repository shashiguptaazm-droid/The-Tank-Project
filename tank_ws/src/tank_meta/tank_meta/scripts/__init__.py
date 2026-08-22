"""tank_meta.scripts subpackage — importable versions of CLI scripts."""

import os as _os
import sys as _sys

# Ensure the ROS2 package root is on sys.path so tank_meta can be found
# from within this subpackage.
# Path: tank_meta/tank_meta/scripts/ → go up 3 levels to ROS2 package root
_scripts_dir = _os.path.dirname(_os.path.abspath(__file__))
_pkg_root = _os.path.abspath(_os.path.join(_scripts_dir, "..", "..", ".."))
if _pkg_root not in _sys.path:
    _sys.path.insert(0, _pkg_root)
