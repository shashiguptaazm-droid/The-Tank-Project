"""pytest suite for :mod:`tank_meta.code_indexer`."""
from __future__ import annotations

import os
import tempfile

from tank_meta.code_indexer import index_directory, index_file
from tank_meta.meta_store import MetaStore


SAMPLE_PY = '''
"""A fake motor driver used for tests."""

import time
import numpy as np
from typing import Optional

CONST = 42


def set_pwm(freq, duty):
    """Configure hardware PWM."""
    return (freq, duty)


class MotorDriver:
    """Wraps the BTS7960 H-bridge."""

    def __init__(self, pin_a=12, pin_b=13):
        self.pin_a = pin_a
        self.pin_b = pin_b

    def drive(self, speed):
        return speed * CONST


async def reset_can():
    return True
'''


def _bootstrap(tmpdir: str) -> str:
    pkg = os.path.join(tmpdir, "fake_pkg")
    os.makedirs(pkg)
    with open(os.path.join(pkg, "driver.py"), "w") as fh:
        fh.write(SAMPLE_PY)
    with open(os.path.join(pkg, "__init__.py"), "w") as fh:
        fh.write('"""Fake pkg."""\n')
    return pkg


def test_index_file_extracts_purpose_module_and_members(tmp_path):
    pkg = _bootstrap(str(tmp_path))
    py = os.path.join(pkg, "driver.py")
    row = index_file(py, str(tmp_path))
    assert row is not None
    assert row.language == "python"
    assert "fake motor driver" in row.purpose.lower()
    # row.module looks like "fake_pkg.driver" — endswith check on the dotted form.
    dotted_module = row.module.replace(os.sep, ".")
    assert dotted_module.endswith("driver")
    assert "set_pwm" in row.functions
    assert "reset_can" in row.functions            # async functions counted
    assert "MotorDriver" in row.classes
    # deps: time, numpy (top-level), typing (top-level)
    assert "time" in row.deps
    assert "numpy" in row.deps
    assert row.line_count > 5


def test_index_file_returns_none_on_syntax_error(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def this is not python ::: !!")
    row = index_file(str(bad), str(tmp_path))
    assert row is None


def test_index_directory_pushes_rows_into_meta_store(tmp_path):
    pkg = _bootstrap(str(tmp_path))
    with tempfile.TemporaryDirectory() as dbd:
        db = os.path.join(dbd, "meta.db")
        store = MetaStore(db)
        n = index_directory(str(tmp_path), store)
        assert n >= 2                      # driver.py + __init__.py
        hits = store.search_code("set_pwm pwm")
        assert hits, "search_code returned empty"
        top = hits[0]
        assert top.module.endswith("driver")
        store.close()


def test_index_directory_records_last_modified_mtime(tmp_path):
    pkg = _bootstrap(str(tmp_path))
    py = os.path.join(pkg, "driver.py")
    expected_mtime = os.path.getmtime(py)
    row = index_file(py, str(tmp_path))
    assert row is not None
    assert abs(row.last_modified - expected_mtime) < 0.01


def test_index_directory_uses_safe_module_name(tmp_path):
    pkg = _bootstrap(str(tmp_path))
    py = os.path.join(pkg, "__init__.py")
    row = index_file(py, str(tmp_path))
    assert row is not None
    # module should be "fake_pkg" not "fake_pkg/__init__"
    assert row.module == "fake_pkg"
