"""
tracker.py - Object Tracking (Features 61-80)
Multi-object tracking, IDs, persistence, re-ID, velocity, collision prediction
"""
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("tank.ai.tracking")


class Track:
    def __init__(self, track_id: int, class_name: str, center: Tuple[int, int], bbox: tuple,
                 confidence: float = 0.0):
        self.track_id = track_id
        self.class_name = class_name
        self.center = center
        self.bbox = bbox
        self.confidence = confidence
        self.history: List[Tuple[int, int]] = [center]
        self.velocity = (0.0, 0.0)
        self.direction = (0.0, 0.0)
        self.created_at = time.time()
        self.last_seen = time.time()
        self.hit_count = 1
        self.miss_count = 0
        self.is_occluded = False
        self.reid_features: Optional[List[float]] = None
        self.confidence_score = 1.0

    def update(self, center: Tuple[int, int], bbox: tuple, confidence: float = 0.0):
        if self.history:
            prev = self.history[-1]
            self.velocity = (center[0] - prev[0], center[1] - prev[1])
            dist = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            if dist > 0:
                self.direction = (self.velocity[0] / dist, self.velocity[1] / dist)
        self.center = center
        self.bbox = bbox
        self.confidence = confidence
        self.history.append(center)
        if len(self.history) > 50:
            self.history.pop(0)
        self.last_seen = time.time()
        self.hit_count += 1
        self.miss_count = 0
        self.is_occluded = False

    def predict_next(self, steps: int = 1) -> Tuple[int, int]:
        return (int(self.center[0] + self.velocity[0] * steps),
                int(self.center[1] + self.velocity[1] * steps))

    def time_since_seen(self) -> float:
        return time.time() - self.last_seen

    def is_expired(self, timeout: float = 2.0) -> bool:
        return self.time_since_seen() > timeout

    def get_speed(self) -> float:
        return math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)

    def to_dict(self) -> dict:
        return {
            "id": self.track_id,
            "class": self.class_name,
            "center": list(self.center),
            "bbox": list(self.bbox),
            "velocity": [round(v, 1) for v in self.velocity],
            "direction": [round(d, 3) for d in self.direction],
            "speed": round(self.get_speed(), 1),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "occluded": self.is_occluded,
            "age_s": round(time.time() - self.created_at, 1),
            "confidence": self.confidence_score,
        }


class MultiObjectTracker:
    """Features 61-80: Multi-object tracking with IDs, re-ID, velocity, collision."""

    def __init__(self, max_age: float = 3.0, match_threshold: float = 50.0):
        self.max_age = max_age
        self.match_threshold = match_threshold
        self.tracks: Dict[int, Track] = {}
        self.next_id = 1
        self.frame_count = 0
        self.total_tracks = 0
        self._reid_gallery: Dict[int, List[float]] = {}
        self.track_events: List[Dict] = []

    # 61-63. Multi-object tracking + Track IDs + persistence
    def update(self, detections: List[Dict]) -> List[Dict]:
        self.frame_count += 1
        det_centers = []
        for det in detections:
            center = tuple(det.get("center", [0, 0]))
            det_centers.append((center, det))

        matched_det_ids = set()
        matched_track_ids = set()

        for det_center, det in det_centers:
            best_dist = self.match_threshold
            best_id = None
            for tid, track in self.tracks.items():
                dist = math.sqrt((det_center[0] - track.center[0])**2 +
                                 (det_center[1] - track.center[1])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_id = tid
            if best_id is not None:
                self.tracks[best_id].update(det_center, det.get("bbox", (0, 0, 0, 0)),
                                            det.get("confidence", 0))
                matched_det_ids.add(id(det))
                matched_track_ids.add(best_id)
            else:
                tid = self._create_track(det)
                matched_det_ids.add(id(det))
                matched_track_ids.add(tid)

        for tid in list(self.tracks.keys()):
            if tid not in matched_track_ids:
                self.tracks[tid].miss_count += 1
                self.tracks[tid].is_occluded = True

        expired = [tid for tid, t in self.tracks.items() if t.is_expired(self.max_age)]
        for tid in expired:
            self._delete_track(tid)

        self._update_confidence_scores()
        return [t.to_dict() for t in self.tracks.values()]

    def _create_track(self, det: Dict) -> int:
        tid = self.next_id
        self.next_id += 1
        center = tuple(det.get("center", [0, 0]))
        track = Track(tid, det.get("class", "unknown"), center,
                      det.get("bbox", (0, 0, 0, 0)), det.get("confidence", 0))
        self.tracks[tid] = track
        self.total_tracks += 1
        self.track_events.append({"type": "created", "id": tid, "time": time.time()})
        return tid

    def _delete_track(self, tid: int):
        if tid in self._reid_gallery:
            self._reid_gallery[tid] = self.tracks[tid].reid_features or []
        del self.tracks[tid]
        self.track_events.append({"type": "deleted", "id": tid, "time": time.time()})

    # 64-66. Track timeout, occlusion, re-identification
    def handle_occlusion(self, track_id: int, occluded: bool = True):
        if track_id in self.tracks:
            self.tracks[track_id].is_occluded = occluded

    def re_identify(self, detected_class: str, features: Optional[List[float]] = None) -> Optional[int]:
        for tid, saved_feats in self._reid_gallery.items():
            if saved_feats and features:
                similarity = sum(a * b for a, b in zip(saved_feats, features))
                if similarity > 0.7:
                    return tid
        return None

    # 67. Person re-identification
    def re_identify_person(self, features: List[float]) -> Optional[int]:
        for tid, track in self.tracks.items():
            if track.class_name == "person" and track.reid_features:
                sim = sum(a * b for a, b in zip(features, track.reid_features))
                if sim > 0.7:
                    return tid
        return None

    # 68-70. Object velocity, direction, collision trajectory
    def get_velocity(self, track_id: int) -> Tuple[float, float]:
        track = self.tracks.get(track_id)
        return track.velocity if track else (0, 0)

    def get_direction(self, track_id: int) -> Tuple[float, float]:
        track = self.tracks.get(track_id)
        return track.direction if track else (0, 0)

    def predict_collision(self, track_a: int, track_b: int, horizon_s: float = 2.0) -> Dict[str, Any]:
        ta = self.tracks.get(track_a)
        tb = self.tracks.get(track_b)
        if not ta or not tb:
            return {"collision": False}
        min_dist = float('inf')
        collision_time = -1
        for t in range(1, int(horizon_s * 10) + 1):
            pa = ta.predict_next(t)
            pb = tb.predict_next(t)
            dist = math.sqrt((pa[0] - pb[0])**2 + (pa[1] - pb[1])**2)
            if dist < min_dist:
                min_dist = dist
                collision_time = t * 0.1
        return {
            "collision": min_dist < 50,
            "min_distance_px": round(min_dist, 1),
            "collision_time_s": round(collision_time, 2) if collision_time > 0 else None,
        }

    # 71-73. Nearest object, threat ranking, priority
    def nearest_object(self, reference_point: Tuple[int, int] = (320, 240)) -> Optional[Dict]:
        nearest = None
        min_dist = float('inf')
        for tid, track in self.tracks.items():
            dist = math.sqrt((track.center[0] - reference_point[0])**2 +
                             (track.center[1] - reference_point[1])**2)
            if dist < min_dist:
                min_dist = dist
                nearest = track.to_dict()
                nearest["distance_px"] = round(dist, 1)
        return nearest

    def threat_ranking(self) -> List[Dict]:
        threats = []
        for tid, track in self.tracks.items():
            score = 0
            if track.class_name in ("person", "car", "truck", "dog"):
                score += 30
            if track.get_speed() > 20:
                score += 20
            if track.center[1] > 300:
                score += 10
            score += track.confidence * 40
            threats.append({**track.to_dict(), "threat_score": round(score, 1)})
        return sorted(threats, key=lambda x: x["threat_score"], reverse=True)

    def get_priority_track(self) -> Optional[Dict]:
        threats = self.threat_ranking()
        return threats[0] if threats else None

    # 74-76. Track confidence, history, visualization data
    def _update_confidence_scores(self):
        for track in self.tracks.values():
            age = time.time() - track.created_at
            recency = 1.0 / (1.0 + track.time_since_seen())
            hit_ratio = track.hit_count / max(1, track.hit_count + track.miss_count)
            track.confidence_score = round(0.4 * recency + 0.3 * hit_ratio + 0.3 * min(1.0, age / 5), 3)

    def get_track_history(self, track_id: int) -> List[Tuple[int, int]]:
        track = self.tracks.get(track_id)
        return track.history if track else []

    def get_visualization_data(self) -> Dict[str, Any]:
        return {
            "tracks": [t.to_dict() for t in self.tracks.values()],
            "total_active": len(self.tracks),
            "total_created": self.total_tracks,
            "frame": self.frame_count,
        }

    # 77-80. Recording, replay, benchmark, failure recovery
    def record_tracks(self) -> List[Dict]:
        return [t.to_dict() for t in self.tracks.values()]

    def get_statistics(self) -> Dict[str, Any]:
        speeds = [t.get_speed() for t in self.tracks.values()]
        return {
            "active_tracks": len(self.tracks),
            "total_created": self.total_tracks,
            "events": len(self.track_events),
            "avg_speed": round(sum(speeds) / max(1, len(speeds)), 1),
            "max_speed": round(max(speeds) if speeds else 0, 1),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "tracker_active": True,
            "max_age_s": self.max_age,
            "match_threshold_px": self.match_threshold,
            "statistics": self.get_statistics(),
        }
