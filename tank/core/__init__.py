"""Tank — Core package: config, events, state machine, decision engine, hardware."""
from .config import TankConfig, get_config
from .event_bus import EventBus, EventType, Event, get_event_bus
from .state_machine import State, StateMachine
from .decision_engine import DecisionEngine, AIResult, Decision, ActionType
from .hardware_registry import (
    Component, BodySection, ComponentStatus, REGISTRY,
    get_all_components, get_components_by_section, get_component_count
)
