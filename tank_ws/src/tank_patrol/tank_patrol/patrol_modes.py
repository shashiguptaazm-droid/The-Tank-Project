"""Pure-Python patrol modes for :mod:`tank_patrol`.

Two modes ship today — :class:`WaypointPatrol` and :class:`RandomWalkPatrol`.
Perimeter sweep + expanding spiral were dropped per Thinker's verdict —
they need a global occupancy grid to avoid scraping walls, and we don't
have Nav2 wired yet (Phase 7.5 follow-up).

Goal design
-----------
Each mode emits a :class:`MovementGoal` — a target ``Pose2D`` plus a
suggested linear speed. The downstream controller (in ROS land,
``patrol_node``) decides how to actually get there. By keeping the goal
emission pure-Python we can unit-test the modes without ROS or a robot.

RandomWalk uses a seeded RNG so bench tests are deterministic. Set
``seed=None`` at construction time to get true randomness in production.
"""
from __future__ import annotations

import json
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ----------------------------- geometry ----------------------------------
@dataclass
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0          # radians

    @classmethod
    def origin(cls) -> "Pose2D":
        return cls(0.0, 0.0, 0.0)

    def distance_to(self, other: "Pose2D") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class MovementGoal:
    target: Pose2D
    speed: float = 0.4         # m/s
    tolerance: float = 0.3      # accept as reached within this radius (m)
    label: str = ""            # human-readable waypoint name


# ----------------------------- base --------------------------------------
class PatrolMode(ABC):
    """All patrol modes know how to (re)start and emit the next goal."""

    name: str = "abstract"

    @abstractmethod
    def reset(self, start: Pose2D) -> MovementGoal: ...

    @abstractmethod
    def next_goal(self, current: Pose2D) -> Optional[MovementGoal]: ...

    @abstractmethod
    def done(self) -> bool: ...


# --------------------------- waypoint patrol ----------------------------
class WaypointPatrol(PatrolMode):
    """Visits a list of ``Pose2D`` in order. Loops by default.

    Internal index semantics: ``_idx`` points to the **next** waypoint to
    return. reset() sets ``_idx = -1`` so the first :meth:`next_goal` call
    increments to 0 and yields ``waypoints[0]``.
    """

    name = "waypoint"

    def __init__(self, waypoints: List[Pose2D], loop: bool = True) -> None:
        if not waypoints:
            raise ValueError("WaypointPatrol requires >= 1 waypoint")
        self._waypoints = list(waypoints)
        self._loop = bool(loop)
        self._idx = -1
        self._completed = False

    def reset(self, start: Pose2D) -> MovementGoal:
        self._idx = -1
        self._completed = False
        return self.next_goal(start)

    def next_goal(self, current: Pose2D) -> Optional[MovementGoal]:     # noqa: ARG002
        if self._completed:
            return None
        self._idx += 1
        if self._idx >= len(self._waypoints):
            if self._loop:
                self._idx = 0
            else:
                self._completed = True
                return None
        wp = self._waypoints[self._idx]
        return MovementGoal(target=wp, label=f"wp[{self._idx}/{len(self._waypoints)-1}]")

    def done(self) -> bool:
        return self._completed


# --------------------------- random walk patrol -------------------------
class RandomWalkPatrol(PatrolMode):
    """Random waypoint sampled inside a rectangular ``bounds``.

    ``bounds`` = ``(xmin, ymin, xmax, ymax)``. Each call to :meth:`next_goal`
    returns a fresh random target inside that rectangle. The mode never
    reports done — caller is responsible for the run-duration budget.

    The constructor takes a ``seed`` so pytest runs are deterministic.
    Set ``seed=None`` for entropy.

    Sampling rule
    -------------
    The :meth:`_sample_new_target` helper retries up to 64 times to land a
    point whose distance from the current pose is in
    ``[min_leg, max_leg]``. If that fails (very small bounds), it falls
    back to ANY random point inside bounds — sub-optimal but the robot
    can still move, and we'd rather nudge out of a degenerate state than
    freeze.
    """

    name = "random"

    def __init__(self,
                 bounds: Tuple[float, float, float, float],
                 min_leg: float = 1.0,
                 max_leg: float = 3.0,
                 speed: float = 0.4,
                 seed: Optional[int] = 42) -> None:
        if len(bounds) != 4:
            raise ValueError(f"bounds must be (xmin,ymin,xmax,ymax); got {bounds!r}")
        xmin, ymin, xmax, ymax = bounds
        if xmin >= xmax or ymin >= ymax:
            raise ValueError(f"invalid bounds {bounds!r}")
        self._bounds = tuple(float(v) for v in bounds)
        if min_leg <= 0 or max_leg < min_leg:
            raise ValueError(f"invalid legs min={min_leg} max={max_leg}")
        self._min_leg = float(min_leg)
        self._max_leg = float(max_leg)
        self._speed = float(speed)
        self._rng = random.Random(seed)
        self._prev: Pose2D = Pose2D.origin()

    def reset(self, start: Pose2D) -> MovementGoal:
        target = self._sample_new_target(start)
        self._prev = start
        return MovementGoal(target=target, speed=self._speed, label="rw[seed]")

    def next_goal(self, current: Pose2D) -> MovementGoal:
        target = self._sample_new_target(current)
        self._prev = current
        return MovementGoal(target=target, speed=self._speed, label="rw")

    def done(self) -> bool:
        return False

    def _sample_new_target(self, current: Pose2D) -> Pose2D:
        """Sample a target. Retry until leg length is in the configured
        band; on retry exhaustion, fall back to a uniform random point."""
        xmin, ymin, xmax, ymax = self._bounds
        for _ in range(64):                         # bounded retries
            tx = self._rng.uniform(xmin, xmax)
            ty = self._rng.uniform(ymin, ymax)
            cand = Pose2D(tx, ty, 0.0)
            leg = current.distance_to(cand)
            if self._min_leg <= leg <= self._max_leg:
                return cand
        # Fallback: take any random point. Documented inline; intentional.
        return Pose2D(self._rng.uniform(xmin, xmax),
                      self._rng.uniform(ymin, ymax), 0.0)


# ----------------------------- helpers ----------------------------------
def load_waypoints_json(path: str) -> List[Pose2D]:
    """Read JSON of the form::

        [
          {"name": "perimeter_north", "x": 1.0, "y": 2.0, "yaw": 1.57},
          ...
        ]

    Missing ``yaw`` defaults to 0.0. Missing ``name`` is OK (only :class:`WaypointPatrol` uses it as a label").
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise ValueError(f"{path}: top-level must be a list, got {type(raw).__name__}")
    out: List[Pose2D] = []
    for w in raw:
        if not isinstance(w, dict):
            raise ValueError(f"{path}: every entry must be an object, got {w!r}")
        if "x" not in w or "y" not in w:
            raise ValueError(f"{path}: entry missing x/y: {w!r}")
        out.append(Pose2D(
            x=float(w["x"]),
            y=float(w["y"]),
            yaw=float(w.get("yaw", 0.0)),
        ))
    if not out:
        raise ValueError(f"{path}: no waypoints")
    return out
