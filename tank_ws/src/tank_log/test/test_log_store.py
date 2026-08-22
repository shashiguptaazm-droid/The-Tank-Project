"""pytest for :mod:`tank_log.log_store` and :mod:`tank_log.learner`."""
from __future__ import annotations

import json
import os
import tempfile
import time

import pytest


def _tmp_store():
    td = tempfile.mkdtemp()
    return (td, os.path.join(td, "log.db"))


def test_log_store_append_and_recent():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    s.append(ts=time.time(), topic="/wake_detected",
             msgtype="std_msgs/Bool", source="wake_node", payload="true")
    s.append(ts=time.time() + 1.0, topic="/intent_text",
             msgtype="std_msgs/String", source="stt_node", payload='hi')
    assert s.count() == 2
    rows = s.recent(limit=5)
    # newest first
    assert rows[0].topic == "/intent_text"
    assert rows[1].topic == "/wake_detected"
    s.close()


def test_log_store_by_topic_and_by_source():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    for i in range(5):
        s.append(time.time() + i, "/cmd_vel", "geometry_msgs/Twist",
                 "teleop_node", f"twist {i}")
    for i in range(3):
        s.append(time.time() + 100 + i, "/cmd_vel", "geometry_msgs/Twist",
                 "auto_node",    f"twist auto {i}")
    topic = s.by_topic("/cmd_vel")
    assert len(topic) == 8
    src = s.by_source("auto_node")
    assert len(src) == 3 and all(r.source == "auto_node" for r in src)
    s.close()


def test_log_store_idempotent_on_primary_key_collision():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    ts = time.time()
    s.append(ts, "/wake_detected", "std_msgs/Bool", "wake_node", "true")
    s.append(ts, "/wake_detected", "std_msgs/Bool", "wake_node", "false")
    rows = s.by_topic("/wake_detected")
    # (ts, topic, source) is the PK — second insert replaces the first.
    assert len(rows) == 1
    assert rows[0].payload == "false"
    s.close()


def test_log_store_compact_age():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    old = time.time() - 100 * 86400.0
    s.append(old + 1, "/cmd_vel", "x", "y", "1")
    s.append(old + 2, "/cmd_vel", "x", "y", "2")
    s.append(time.time(), "/cmd_vel", "x", "y", "fresh")
    before = s.count()
    removed = s.compact_age(max_age_days=30.0)
    after = s.count()
    assert before == 3
    assert removed == 2
    assert after == 1
    s.close()


def test_log_store_summary_record_and_recent():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    s.record_summary(time.time(), 60.0, "/cmd_vel", 42, None,
                     {"/cmd_vel": 42, "/intent_text": 7})
    s.record_summary(time.time() + 1.0, 60.0, "/estop", 1,
                     "estop_stuck", {"/estop": 1})
    rows = s.recent_summaries(limit=5)
    assert len(rows) == 2
    assert rows[0]["top_topic"] == "/estop"
    assert rows[1]["top_topic"] == "/cmd_vel"
    s.close()


def test_learner_detects_wake_no_intent_and_estop_stuck():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    from tank_log.learner import Learner
    s = LogStore(db)
    # wake event with no follow-up intent
    s.append(time.time() - 1.0, "/wake_detected",
             "std_msgs/Bool", "wake_node", "true")
    summary = Learner(store=s).tick()
    assert summary["anomaly"] == "wake_no_intent"

    # estop stuck for >= 30s
    s2_path = os.path.join(td, "log2.db")
    s2 = LogStore(s2_path)
    s2.append(time.time() - 60.0, "/estop", "std_msgs/Bool", "ui", "true")
    s2.append(time.time() - 30.0, "/estop", "std_msgs/Bool", "ui", "true")
    s2.append(time.time(),        "/estop", "std_msgs/Bool", "ui", "true")
    summary = Learner(store=s2).tick()
    assert summary["anomaly"] == "estop_stuck"

    # dock charging but health not ok
    s3_path = os.path.join(td, "log3.db")
    s3 = LogStore(s3_path)
    s3.append(time.time() - 1.0, "/dock/charge_cmd", "std_msgs/Bool",
              "dock_node", "true")
    s3.append(time.time() - 0.5, "/health/ok", "std_msgs/Bool",
              "health_node", "false")
    summary = Learner(store=s3).tick()
    assert summary["anomaly"] == "dock_charging_but_health_not_ok"
    s.close(); s2.close(); s3.close()


def test_log_store_payloaddict_helper():
    td, db = _tmp_store()
    from tank_log.log_store import LogStore
    s = LogStore(db)
    s.append_payload_dict(time.time(), "/cmd_vel", "geometry_msgs/Twist",
                          "teleop", {"linear_x": 0.4, "angular_z": 0.1})
    rows = s.by_topic("/cmd_vel")
    assert len(rows) == 1
    blob = json.loads(rows[0].payload)
    assert blob["linear_x"] == 0.4
    s.close()
