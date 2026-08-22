"""Pytest bootstrap — make `from tank_motion... import ...` work without colcon.

Pytest's rootdir detection puts this file's directory on sys.path, which is
``tank_ws/src/tank_motion/``. From there the inner ``tank_motion/`` Python
package resolves correctly.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
