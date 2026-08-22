"""Tank — Full Pipeline Integration Test.

Tests the complete cycle: SENSE → PERCEIVE → FUSE → AI → DECIDE → ACT → VERIFY
with all sensors, ESP32 swarm, storage, and safety systems.
"""
from __future__ import annotations

import sys
import os
import time
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestEventBus(unittest.TestCase):
    def test_publish_subscribe(self):
        from tank.core.event_bus import EventBus, EventType
        bus = EventBus()
        received = []
        bus.subscribe(EventType.PERSON_DETECTED, lambda e: received.append(e))
        bus.emit(EventType.PERSON_DETECTED, source="test", confidence=0.95)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].confidence, 0.95)

    def test_history(self):
        from tank.core.event_bus import EventBus, EventType
        bus = EventBus()
        for i in range(5):
            bus.emit(EventType.CAMERA_FRAME, source=f"cam_{i}")
        history = bus.history(limit=3)
        self.assertEqual(len(history), 3)


class TestStateMachine(unittest.TestCase):
    def test_valid_transitions(self):
        from tank.core.state_machine import StateMachine, State
        sm = StateMachine()
        self.assertTrue(sm.transition(State.OBSERVING, reason="start"))
        self.assertEqual(sm.state, State.OBSERVING)
        self.assertTrue(sm.transition(State.DETECTING, reason="person"))
        self.assertEqual(sm.state, State.DETECTING)

    def test_invalid_transition(self):
        from tank.core.state_machine import StateMachine, State
        sm = StateMachine()
        # IDLE → ACTING is not valid
        result = sm.transition(State.ACTING, reason="bad")
        self.assertFalse(result)
        self.assertEqual(sm.state, State.IDLE)

    def test_emergency_force(self):
        from tank.core.state_machine import StateMachine, State
        sm = StateMachine()
        sm.transition(State.OBSERVING)
        sm.transition(State.DETECTING)
        sm.force(State.SAFE_STOP, reason="estop")
        self.assertEqual(sm.state, State.SAFE_STOP)


class TestDecisionEngine(unittest.TestCase):
    def test_person_tracking(self):
        from tank.core.state_machine import StateMachine, State
        from tank.core.decision_engine import DecisionEngine, AIResult, ActionType
        sm = StateMachine()
        sm.transition(State.OBSERVING)
        sm.transition(State.DETECTING)
        de = DecisionEngine(sm)
        ai = AIResult(object_name="person", confidence=0.95, distance_m=2.1,
                      situation="person_detected", recommended_action="track")
        decision = de.process(ai)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, ActionType.TRACK)

    def test_unknown_close_rejects(self):
        from tank.core.state_machine import StateMachine, State
        from tank.core.decision_engine import DecisionEngine, AIResult, ActionType
        sm = StateMachine()
        sm.transition(State.OBSERVING)
        de = DecisionEngine(sm)
        ai = AIResult(object_name="unknown", confidence=0.5, distance_m=0.2,
                      situation="unknown_close", recommended_action="approach")
        decision = de.process(ai)
        # Should fail safety check → SAFE_STOP
        self.assertEqual(sm.state, State.SAFE_STOP)


class TestSensorFusion(unittest.TestCase):
    def test_camera_only(self):
        from tank.perception.sensor_fusion import SensorFusion
        fusion = SensorFusion()
        fusion.update_camera([{"object": "person", "confidence": 0.9, "distance_m": 3.0}])
        entities = fusion.fuse()
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].entity_type, "person")
        self.assertEqual(len(entities[0].sources), 1)

    def test_multi_sensor_fusion(self):
        from tank.perception.sensor_fusion import SensorFusion
        fusion = SensorFusion()
        fusion.update_camera([{"object": "person", "confidence": 0.85, "distance_m": 3.0}])
        fusion.update_lidar(2.8)
        fusion.update_thermal(True, 0.9)
        entities = fusion.fuse()
        self.assertEqual(len(entities), 1)
        self.assertIn("camera", entities[0].sources)
        self.assertIn("lidar", entities[0].sources)
        self.assertIn("thermal", entities[0].sources)
        self.assertGreater(entities[0].confidence, 0.85)


class TestSafety(unittest.TestCase):
    def test_watchdog_timeout(self):
        from tank.core.state_machine import StateMachine, State
        from tank.control.safety import SafetyController
        sm = StateMachine()
        safety = SafetyController(sm, timeout=0.1)
        safety.feed_watchdog()
        time.sleep(0.15)
        result = safety.check()
        self.assertFalse(result)
        self.assertEqual(sm.state, State.SAFE_STOP)

    def test_emergency_stop(self):
        from tank.core.state_machine import StateMachine, State
        from tank.control.safety import SafetyController
        sm = StateMachine()
        sm.transition(State.OBSERVING)
        safety = SafetyController(sm)
        safety.emergency_stop()
        self.assertEqual(sm.state, State.SAFE_STOP)
        self.assertTrue(safety._emergency)


class TestStorage(unittest.TestCase):
    def test_log_and_query(self):
        from tank.storage.event_log import EventStorage
        import tempfile
        db = tempfile.mktemp(suffix=".db")
        storage = EventStorage(db_path=__import__("pathlib").Path(db))
        storage.connect()
        storage.log_event("TEST_EVENT", "test_source", 0.95, {"key": "val"})
        events = storage.query_events("TEST_EVENT")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["confidence"], 0.95)
        storage.disconnect()

    def test_telemetry(self):
        from tank.storage.event_log import EventStorage
        import tempfile
        db = tempfile.mktemp(suffix=".db")
        storage = EventStorage(db_path=__import__("pathlib").Path(db))
        storage.connect()
        storage.log_telemetry("cpu_percent", 45.2, "%")
        storage.log_telemetry("ram_mb", 1024, "MB")
        stats = storage.stats()
        self.assertEqual(stats["telemetry"], 2)
        storage.disconnect()


class TestESP32Swarm(unittest.TestCase):
    def test_swarm_connect(self):
        from tank.networking.esp32.swarm import create_default_swarm
        swarm = create_default_swarm()
        results = swarm.connect_all()
        self.assertTrue(len(results) == 5)
        health = swarm.health()
        self.assertEqual(health["total_nodes"], 5)

    def test_swarm_broadcast(self):
        from tank.networking.esp32.swarm import create_default_swarm
        swarm = create_default_swarm()
        swarm.connect_all()
        responses = swarm.broadcast("ping")
        self.assertTrue(len(responses) == 5)


class TestHardwareRegistry(unittest.TestCase):
    def test_component_count(self):
        from tank.core.hardware_registry import get_component_count
        count = get_component_count()
        self.assertGreater(count, 40)

    def test_sections(self):
        from tank.core.hardware_registry import get_components_by_section, BodySection
        head = get_components_by_section(BodySection.HEAD)
        self.assertGreater(len(head), 5)


class TestDashboard(unittest.TestCase):
    def test_render(self):
        from tank.ui.dashboard import render_dashboard
        status = {"state": "OBSERVING", "cycle": 1, "sensors": [], "fusion": {},
                  "ai_latency": 0.05, "safety": {"emergency": False}}
        output = render_dashboard(status)
        self.assertIn("TANK", output)
        self.assertIn("OBSERVING", output)


class TestFullPipeline(unittest.TestCase):
    def test_sense_perceive_fuse_decide_act_verify(self):
        """The most important test: full pipeline cycle."""
        from tank.main import TankSystem
        from tank.core.config import get_config

        config = get_config()
        tank = TankSystem(config, simulation=True)

        # Add mock sensors
        from tank.simulation.mock_sensors import create_mock_sensors
        for s in create_mock_sensors():
            tank.add_sensor(s)

        tank.start()

        # Run 10 cycles
        for i in range(10):
            result = tank.tick()
            self.assertIn("cycle", result)
            self.assertIn("state", result)

        tank.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
