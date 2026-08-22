"""Tank — Main Entry Point.

SENSE → PERCEIVE → FUSE → UNDERSTAND → DECIDE → ACT → VERIFY → LEARN/LOG

Usage:
    python3 -m tank.main                    # simulation mode
    python3 -m tank.main --demo             # deterministic demo
    python3 -m tank.main --real             # real hardware
    python3 -m tank.main --dashboard        # with web dashboard
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from typing import Dict, List

from .core import (
    TankConfig, get_config,
    EventBus, EventType, get_event_bus,
    State, StateMachine,
    AIResult, Decision, DecisionEngine, ActionType,
)
from .perception.sensor import SensorInterface, SensorReading
from .perception.sensor_fusion import SensorFusion
from .ai.engine import AIEngine
from .ai.vps_client import VPSClient
from .control.safety import SafetyController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("tank.main")


class TankSystem:
    """The complete Tank robot system — SENSE→PERCEIVE→FUSE→DECIDE→ACT→VERIFY."""

    def __init__(self, config: TankConfig, simulation: bool = True) -> None:
        self.config = config
        self.simulation = simulation
        self.bus: EventBus = get_event_bus()
        self.sm: StateMachine = StateMachine(on_transition=self._on_state_change)
        self.fusion: SensorFusion = SensorFusion()
        self.safety: SafetyController = SafetyController(self.sm, timeout=config.control.safety_timeout)

        # AI
        vps = None
        if config.vps.api_key:
            vps = VPSClient(config.vps.url, config.vps.api_key, config.vps.timeout, config.vps.retries)
        self.ai: AIEngine = AIEngine(vps_client=vps, local_model=config.ai.model)

        # Decision
        self.decision_engine: DecisionEngine = DecisionEngine(self.sm)

        # Sensors
        self.sensors: List[SensorInterface] = []
        self._running = False
        self._cycle_count = 0
        self._actions_log: List[Dict] = []

    def add_sensor(self, sensor: SensorInterface) -> None:
        self.sensors.append(sensor)

    def start(self) -> None:
        logger.info("Tank starting...")
        self._running = True
        self.sm.transition(State.IDLE, reason="system_start")
        self.bus.emit(EventType.SYSTEM_STARTUP, source="tank_main",
                      data={"simulation": self.simulation})

        # Connect sensors
        for s in self.sensors:
            ok = s.connect()
            if ok:
                self.bus.emit(EventType.SENSOR_CONNECTED, source=s.name)
            else:
                self.bus.emit(EventType.SENSOR_DISCONNECTED, source=s.name)
                self.safety.sensor_failure(s.name)

        self.sm.transition(State.OBSERVING, reason="sensors_connected")
        logger.info(f"Tank running ({len(self.sensors)} sensors connected, sim={self.simulation})")

    def tick(self) -> Dict:
        """One full SENSE→PERCEIVE→FUSE→DECIDE→ACT cycle. Returns status dict."""
        self._cycle_count += 1
        status = {"cycle": self._cycle_count, "state": self.sm.state.value}

        # SAFETY CHECK
        if not self.safety.check():
            status["safety"] = "BLOCKED"
            return status
        self.safety.feed_watchdog()

        # 1. SENSE — read all sensors
        readings: List[SensorReading] = []
        for sensor in self.sensors:
            r = sensor.read()
            if r:
                readings.append(r)
        status["readings"] = len(readings)

        # 2. PERCEIVE — extract detections from readings
        camera_dets = []
        lidar_dist = None
        thermal_human = False
        for r in readings:
            if r.sensor_type.value == "CAMERA":
                camera_dets = r.data.get("detections", [])
                self.bus.emit(EventType.CAMERA_FRAME, source=r.sensor_type.value, data=r.data)
            elif r.sensor_type.value == "LIDAR":
                lidar_dist = r.data.get("distance_m")
                self.bus.emit(EventType.LIDAR_SCAN, source=r.sensor_type.value, data=r.data)
            elif r.sensor_type.value == "THERMAL":
                thermal_human = r.data.get("human_detected", False)
                if thermal_human:
                    self.bus.emit(EventType.THERMAL_EVENT, source=r.sensor_type.value, data=r.data)
            elif r.sensor_type.value == "IMU":
                self.bus.emit(EventType.IMU_UPDATE, source=r.sensor_type.value, data=r.data)

        # 3. FUSE — combine sensor data
        self.fusion.update_camera(camera_dets)
        self.fusion.update_lidar(lidar_dist)
        self.fusion.update_thermal(thermal_human)
        entities = self.fusion.fuse()
        status["entities"] = len(entities)

        # 4. UNDERSTAND — AI analysis
        ai_result = AIResult()
        if entities:
            top = entities[0]
            ai_result = AIResult(
                object_name=top.entity_type,
                confidence=top.confidence,
                distance_m=top.distance_m,
                situation=f"{top.entity_type}_detected",
                recommended_action="track" if top.entity_type == "person" else "idle",
            )
            self.bus.emit(EventType.AI_RESPONSE_RECEIVED, source="fusion", confidence=top.confidence,
                          data={"entity": top.entity_type, "distance": top.distance_m})

        # 5. DECIDE — through decision engine (never AI→action directly)
        self.sm.transition(State.ANALYZING, reason="ai_analysis")
        decision = self.decision_engine.process(ai_result)
        status["decision"] = decision.action.value if decision else "none"

        # 6. ACT
        if decision and decision.action not in (ActionType.IDLE, ActionType.SAFE_STOP):
            self.sm.transition(State.ACTING, reason=decision.action.value)
            self.safety.on_action_start()
            # Simulate action (in real hardware, this would send motor commands)
            action_result = self._execute_action(decision)
            self.safety.on_action_complete()
            status["action_result"] = action_result
            self._actions_log.append({
                "cycle": self._cycle_count,
                "action": decision.action.value,
                "result": action_result,
                "time": time.time(),
            })

            # 7. VERIFY
            self.sm.transition(State.VERIFYING, reason="action_complete")
            verified = self._verify_action(decision, action_result)
            status["verified"] = verified

        # 8. LEARN/LOG — return to observing
        self.sm.transition(State.OBSERVING, reason="cycle_complete")
        return status

    def _execute_action(self, decision: Decision) -> str:
        """Execute action. Simulation returns 'simulated_success'."""
        if self.simulation:
            return "simulated_success"
        # Real hardware would send motor commands via serial to Arduino
        logger.info(f"Executing: {decision.action.value} — {decision.reason}")
        return "success"

    def _verify_action(self, decision: Decision, result: str) -> bool:
        return result in ("success", "simulated_success")

    def _on_state_change(self, old: State, new: State, reason: str) -> None:
        self.bus.emit(EventType.STATE_CHANGED, source="state_machine",
                      data={"from": old.value, "to": new.value, "reason": reason})

    def stop(self) -> None:
        logger.info("Tank stopping...")
        self._running = False
        self.bus.emit(EventType.SYSTEM_SHUTDOWN, source="tank_main")
        for s in self.sensors:
            s.disconnect()

    def status(self) -> Dict:
        return {
            "state": self.sm.state.value,
            "cycle": self._cycle_count,
            "sensors": [s.health_check() for s in self.sensors],
            "safety": self.safety.health(),
            "ai_latency": round(self.ai.avg_latency, 3),
            "fusion": self.fusion.get_status(),
            "running": self._running,
        }


def main():
    parser = argparse.ArgumentParser(description="Tank — Physical AI Robot Platform")
    parser.add_argument("--demo", action="store_true", help="Run deterministic demo")
    parser.add_argument("--real", action="store_true", help="Use real hardware")
    parser.add_argument("--dashboard", action="store_true", help="Enable web dashboard")
    parser.add_argument("--cycles", type=int, default=20, help="Number of cycles (demo)")
    args = parser.parse_args()

    config = get_config()
    simulation = not args.real

    # Build system
    tank = TankSystem(config, simulation=simulation)

    # Add sensors
    if simulation:
        from .simulation.mock_sensors import create_mock_sensors
        for s in create_mock_sensors():
            tank.add_sensor(s)
    # Real hardware sensors would be added here

    # Run
    tank.start()

    try:
        for i in range(args.cycles):
            result = tank.tick()
            state = result.get("state", "?")
            decision = result.get("decision", "?")
            entities = result.get("entities", 0)
            print(f"  [{i+1:3d}] state={state:<12} entities={entities} decision={decision}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        tank.stop()
        print("\n✅ Tank shutdown complete")


if __name__ == "__main__":
    main()
