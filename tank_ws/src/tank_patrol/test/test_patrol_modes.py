"""pytest for the pure-Python ``tank_patrol.patrol_modes`` and ``surveillance`` modules.

No ROS dependency. Covers WaypointPatrol progression + RandomWalk bounds
+ load_waypoints_json happy & failure paths + classify + severity
rule matrix.
"""
from __future__ import annotations

import pytest


def _wp():
    from tank_patrol.patrol_modes import (
        Pose2D, WaypointPatrol, RandomWalkPatrol, load_waypoints_json,
    )
    return Pose2D, WaypointPatrol, RandomWalkPatrol, load_waypoints_json


def test_waypoint_patrol_visits_each_in_order():
    Pose2D, WaypointPatrol, _, _ = _wp()
    wp = [Pose2D(0, 0), Pose2D(1, 0), Pose2D(1, 1)]
    patrol = WaypointPatrol(wp, loop=True)
    g = patrol.reset(Pose2D.origin())
    assert g.target == wp[0]
    g = patrol.next_goal(wp[0])
    assert g.target == wp[1]
    g = patrol.next_goal(wp[1])
    assert g.target == wp[2]
    g = patrol.next_goal(wp[2])
    # After the third wp, looping wraps — back to wp[0]
    assert g.target == wp[0]
    assert not patrol.done()


def test_waypoint_patrol_done_when_no_loop():
    Pose2D, WaypointPatrol, _, _ = _wp()
    wp = [Pose2D(0, 0), Pose2D(2, 0)]
    patrol = WaypointPatrol(wp, loop=False)
    patrol.reset(Pose2D.origin())   # wp[0]
    patrol.next_goal(wp[0])         # wp[1]
    nxt = patrol.next_goal(wp[1])   # exhausted -> None
    assert nxt is None
    assert patrol.done()


def test_random_walk_bounds_and_min_leg():
    Pose2D, _, RandomWalkPatrol, _ = _wp()
    bounds = (-3.0, -3.0, 3.0, 3.0)
    patrol = RandomWalkPatrol(bounds=bounds,
                              min_leg=1.0, max_leg=3.0,
                              seed=123)
    cur = Pose2D(0, 0)
    for _ in range(40):
        goal = patrol.next_goal(cur)
        x, y = goal.target.x, goal.target.y
        assert -3.0 <= x <= 3.0
        assert -3.0 <= y <= 3.0
        cur = goal.target


def test_random_walk_seeded_is_deterministic():
    Pose2D, _, RandomWalkPatrol, _ = _wp()
    a = RandomWalkPatrol(bounds=(-5, -5, 5, 5), seed=7)
    b = RandomWalkPatrol(bounds=(-5, -5, 5, 5), seed=7)
    cur = Pose2D(0, 0)
    for _ in range(20):
        ga = a.next_goal(cur)
        gb = b.next_goal(cur)
        assert ga.target.x == pytest.approx(gb.target.x)
        assert ga.target.y == pytest.approx(gb.target.y)
        cur = ga.target


def test_load_waypoints_json(tmp_path):
    _, _, _, load_waypoints_json = _wp()
    p = tmp_path / "wp.json"
    p.write_text("""[
        {"name":"north","x":1.0,"y":2.0,"yaw":1.57},
        {"name":"south","x":-1.0,"y":-2.0}
    ]""")
    wp = load_waypoints_json(str(p))
    assert len(wp) == 2
    assert wp[0].yaw == 1.57
    assert wp[1].yaw == 0.0     # default


def test_load_waypoints_json_missing_x_y(tmp_path):
    _, _, _, load_waypoints_json = _wp()
    p = tmp_path / "bad.json"
    p.write_text('[{"name":"oops"}]')
    with pytest.raises(ValueError):
        load_waypoints_json(str(p))


def test_load_waypoints_json_empty(tmp_path):
    _, _, _, load_waypoints_json = _wp()
    p = tmp_path / "empty.json"
    p.write_text('[]')
    with pytest.raises(ValueError):
        load_waypoints_json(str(p))


def test_classify_labels_and_threshold():
    from tank_patrol.surveillance import (
        MotionObservation, classify,
    )
    def obs(label, conf=0.9, area=0.05):
        return MotionObservation(
            ts=1.0, source="t", bbox=(0.1, 0.1, 0.1 + area, 0.1 + area),
            confidence=conf, label=label,
        )
    # Person with solid area & conf → person
    assert classify(obs("person", conf=0.9, area=0.05)) == "person"
    # Cat with thin area (encoded as 0.05²=2.5e-3) and conf above
    # ANIMAL_MIN_CONF → animal.
    assert classify(obs("cat", conf=0.9, area=0.05)) == "animal"
    # CAR also classified.
    assert classify(obs("car", conf=0.9, area=0.05)) == "vehicle"
    # 'noise' label → noise.
    assert classify(obs("noise")) == "noise"
    # Tiny box + very low conf + generic label → noise
    assert classify(obs("motion", conf=0.2, area=0.0001)) == "noise"
    # Unknown / alien → unknown
    assert classify(obs("alien", conf=0.9, area=0.05)) == "unknown"


def test_severity_paused_person_is_critical():
    from tank_patrol.surveillance import (
        AlertSeverity, MotionObservation, severity,
    )
    obs = MotionObservation(
        ts=1.0, source="t", bbox=(0.1, 0.1, 0.3, 0.3),
        confidence=0.8, label="person",
    )
    assert severity(obs, patrol_phase="paused",
                    distance_from_active_edge_m=2.0) == AlertSeverity.CRITICAL


def test_severity_patrolling_person_distance_threshold():
    from tank_patrol.surveillance import (
        AlertSeverity, MotionObservation, severity, ON_PATH_M,
    )
    obs = MotionObservation(
        ts=1.0, source="t", bbox=(0.1, 0.1, 0.3, 0.3),
        confidence=0.8, label="person",
    )
    # Off the path → WARNING.
    assert severity(obs, patrol_phase="patrolling",
                    distance_from_active_edge_m=10.0) == AlertSeverity.WARNING
    # Infinity sentinel (no edge data yet) → WARNING.
    assert severity(obs, patrol_phase="patrolling",
                    distance_from_active_edge_m=float('inf')) == AlertSeverity.WARNING
    # Within ON_PATH_M (3.0) → INFO, not warning.
    assert severity(obs, patrol_phase="patrolling",
                    distance_from_active_edge_m=ON_PATH_M - 0.5) == AlertSeverity.INFO


def test_severity_noise_is_info_even_when_paused():
    from tank_patrol.surveillance import (
        AlertSeverity, MotionObservation, severity,
    )
    obs = MotionObservation(
        ts=1.0, source="t", bbox=(0.1, 0.1, 0.2, 0.2),
        confidence=0.5, label="noise",
    )
    assert severity(obs, patrol_phase="paused",
                    distance_from_active_edge_m=2.0) == AlertSeverity.INFO
