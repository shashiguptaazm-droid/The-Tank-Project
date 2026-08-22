"""Pytest bootstrap for tank_vision tests.

Mirrors the path-injection trick used in tank_motion: pytest's rootdir
detection puts this directory on sys.path, which makes ``import
tank_vision.object_tracker`` (etc.) resolve against the inner
``tank_vision/`` package directory below.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
