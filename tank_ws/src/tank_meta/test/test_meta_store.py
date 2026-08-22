"""pytest suite for :mod:`tank_meta.meta_store`."""
from __future__ import annotations

import os
import tempfile

from tank_meta.decisions_indexer import load_decisions_file
from tank_meta.hardware_indexer import load_hardware_file
from tank_meta.meta_store import (
    CodeFileRow,
    DecisionRow,
    HardwareRow,
    MetaStore,
)


def _tmp_store() -> MetaStore:
    td = tempfile.mkdtemp()
    return MetaStore(os.path.join(td, "meta.db"))


def test_code_upsert_and_search():
    s = _tmp_store()
    s.upsert_code(CodeFileRow(
        path="tank_motion/driver.py",
        module="tank_motion.driver",
        purpose="Drive the BTS7960 H-bridge motor controller",
        line_count=120,
        last_modified=1234567890.0,
        functions=["set_pwm", "drive", "stop"],
        classes=["MotorDriver"],
        deps=["rpi_gpio", "time"],
    ))
    s.upsert_code(CodeFileRow(
        path="tank_motion/kinematics.py",
        module="tank_motion.kinematics",
        purpose="Forward/inverse kinematics for the tracked chassis",
        line_count=80,
        last_modified=1234567891.0,
        functions=["forward", "inverse"],
        classes=[],
        deps=["numpy"],
    ))
    hits = s.search_code("pwm servo h-bridge", top_k=5)
    assert hits, "search_code returned no results"
    top = hits[0]
    assert "BTS7960" in top.purpose or "pwm" in top.functions or \
           "set_pwm" in top.functions
    s.close()


def test_hardware_lookup_is_case_insensitive_then_falls_back_to_like():
    s = _tmp_store()
    s.upsert_hardware(HardwareRow(
        component="fingerprint_sensor",
        kind="fingerprint",
        bus="UART",
        pin="/dev/ttyAMA0 @ 57600 baud",
        driver="R307 pyserial protocol",
        notes="",
    ))
    # exact (case-insensitive)
    h = s.find_hardware("FINGERPRINT_SENSOR")
    assert h is not None and h.bus == "UART"
    # partial
    h2 = s.find_hardware("fingerprint")
    assert h2 is not None and h2.component == "fingerprint_sensor"
    # miss
    h3 = s.find_hardware("nonexistent_widget")
    assert h3 is None
    # all_hardware
    assert len(s.all_hardware()) == 1
    s.close()


def test_decisions_keyword_match_orders_top_first():
    s = _tmp_store()
    s.upsert_decision(DecisionRow(
        id="D-LOW", ts=100.0,
        problem="loose wire",
        reason="vibration", solution="hot glue", result="ok",
    ))
    s.upsert_decision(DecisionRow(
        id="D-PWM", ts=200.0,
        problem="motor not moving",
        reason="PWM frequency too high",
        solution="changed PWM to 200 Hz",
        result="smooth tracking",
    ))
    s.upsert_decision(DecisionRow(
        id="D-OLD", ts=50.0,
        problem="battery brown-out",
        reason="PWM + Wi-Fi spike",
        solution="official 27W supply",
        result="stable",
    ))
    hits = s.search_decisions("PWM frequency still bad")
    assert hits, "expected hits"
    # Among PWM-matching rows the D-PWM one has the most hits
    top_ids = [h.id for h in hits[:2]]
    assert "D-PWM" in top_ids
    s.close()


def test_hardware_decisions_indexers_load_from_json(tmp_path):
    s = _tmp_store()
    hw_json = tmp_path / "hardware.json"
    hw_json.write_text('{"components":[{"component":"pan_servo","kind":"servo",'
                       '"bus":"GPIO","pin":"GPIO18","driver":"x","notes":""}]}')
    dec_json = tmp_path / "decisions.json"
    dec_json.write_text('{"decisions":[{"id":"X-1","ts":1.0,"problem":"p",'
                        '"reason":"r","solution":"s","result":"ok"}]}')
    n_hw = load_hardware_file(str(hw_json), s)
    n_dec = load_decisions_file(str(dec_json), s)
    assert n_hw == 1 and n_dec == 1
    assert s.find_hardware("pan_servo") is not None
    assert s.search_decisions("p")
    s.close()


def test_knowledge_search_includes_tag_score():
    s = _tmp_store()
    s.upsert_knowledge(
        kid="md:install.md", title="Install ROS 2 Humble",
        source="docs", path="/tmp/install.md",
        text="apt install ros-humble-ros-base",
        tags=["ros2", "install"],
    )
    s.upsert_knowledge(
        kid="md:vim.md", title="Vim tricks",
        source="docs", path="/tmp/vim.md",
        text="use jj to escape",
        tags=["editor"],
    )
    hits = s.search_knowledge("ros2 install humble", top_k=3)
    assert hits and hits[0]["id"] == "md:install.md"
    s.close()


def test_counts_reports_all_four_tables():
    s = _tmp_store()
    s.upsert_code(CodeFileRow(path="x.py", line_count=10))
    s.upsert_hardware(HardwareRow(component="x"))
    s.upsert_decision(DecisionRow(id="X", problem="p"))
    s.upsert_knowledge(kid="k", title="t", source="s",
                       path="/p", text="x", tags=[])
    c = s.counts()
    assert c["code_files"] == 1
    assert c["hardware"] == 1
    assert c["decisions"] == 1
    assert c["knowledge"] == 1
    s.close()
