"""Pytest bootstrap — make ``import tank_speech`` work without colcon."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
