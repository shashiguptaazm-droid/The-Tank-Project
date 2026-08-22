"""
TankOS Animation Engine — 60 FPS transitions, physics, spring, particles, boot animation.

Provides tweening, spring physics, particle systems, and transition
helpers that all GUI components can use.  Works both with and without
PySide6 (falls back to simple time-based interpolation).
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class Easing(Enum):
    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto()
    EASE_IN_OUT = auto()
    SPRING = auto()
    BOUNCE = auto()
    ELASTIC = auto()


@dataclass
class Animation:
    """A single tweened animation."""
    target_id: str
    property_name: str
    start_value: float
    end_value: float
    duration_ms: int = 300
    easing: Easing = Easing.EASE_OUT
    delay_ms: int = 0
    loop: bool = False
    yoyo: bool = False
    on_complete: Optional[Callable] = None
    id: str = ""
    _start_time: float = 0.0
    _progress: float = 0.0
    _running: bool = False


@dataclass
class Particle:
    """A single particle for the particle system."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 1.0
    max_life: float = 1.0
    size: float = 4.0
    color: str = "#FFFFFF"
    alpha: float = 1.0


class AnimationEngine:
    """Singleton animation engine providing tweening, spring physics,
    particle systems, and callback-based animation updates."""

    _instance: Optional["AnimationEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AnimationEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._animations: Dict[str, Animation] = {}
                cls._instance._particles: List[Particle] = []
                cls._instance._running = False
                cls._instance._thread: Optional[threading.Thread] = None
                cls._instance._callbacks: Dict[str, Callable] = {}
                cls._instance._lock = threading.Lock()
            return cls._instance

    def start(self, fps: int = 60) -> None:
        """Start the animation update loop in a background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(fps,),
            daemon=True, name="tank_os_anim"
        )
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def _loop(self, fps: int) -> None:
        """Main animation loop. Updates all active animations."""
        period = 1.0 / fps
        while True:
            with self._lock:
                if not self._running:
                    break
            self._tick(period)
            time.sleep(period)

    def _tick(self, dt: float) -> None:
        """Update all animations and particles."""
        now = time.time()
        with self._lock:
            # Update animations
            completed: List[str] = []
            for anim_id, anim in list(self._animations.items()):
                if not anim._running:
                    continue
                elapsed = (now - anim._start_time) * 1000
                if elapsed < anim.delay_ms:
                    continue
                elapsed_after_delay = elapsed - anim.delay_ms
                duration = max(1, anim.duration_ms)
                anim._progress = min(1.0, elapsed_after_delay / duration)
                value = self._interpolate(
                    anim.start_value, anim.end_value,
                    anim._progress, anim.easing
                )
                if anim.property_name:
                    cb = self._callbacks.get(anim.target_id)
                    if cb:
                        try:
                            cb(anim.property_name, value)
                        except Exception:
                            pass
                if anim._progress >= 1.0:
                    if anim.loop:
                        anim._start_time = now
                        anim._progress = 0.0
                    elif anim.yoyo:
                        anim.start_value, anim.end_value = anim.end_value, anim.start_value
                        anim._start_time = now
                        anim._progress = 0.0
                    else:
                        completed.append(anim_id)
                        if anim.on_complete:
                            try:
                                anim.on_complete()
                            except Exception:
                                pass

            for anim_id in completed:
                self._animations.pop(anim_id, None)

            # Update particles
            alive: List[Particle] = []
            for p in self._particles:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.life -= dt
                p.alpha = max(0.0, p.life / p.max_life)
                if p.life > 0:
                    alive.append(p)
            self._particles = alive

    def animate(self, anim: Animation) -> str:
        """Register and start an animation. Returns the animation ID."""
        anim._start_time = time.time()
        anim._running = True
        if not anim.id:
            anim.id = f"anim_{int(time.time() * 1000)}_{hash(anim)}"
        with self._lock:
            self._animations[anim.id] = anim
        return anim.id

    def register_callback(self, target_id: str,
                          callback: Callable[[str, float], None]) -> None:
        """Register a callback that receives updates during animation."""
        with self._lock:
            self._callbacks[target_id] = callback

    def stop_animation(self, anim_id: str) -> bool:
        with self._lock:
            anim = self._animations.pop(anim_id, None)
            return anim is not None

    # ------------------------------------------------------------------
    # Easing math
    # ------------------------------------------------------------------

    @staticmethod
    def _interpolate(start: float, end: float, t: float,
                     easing: Easing) -> float:
        """Interpolate between start and end using the given easing."""
        if easing == Easing.LINEAR:
            return start + (end - start) * t
        elif easing == Easing.EASE_IN:
            return start + (end - start) * (t * t)
        elif easing == Easing.EASE_OUT:
            return start + (end - start) * (t * (2 - t))
        elif easing == Easing.EASE_IN_OUT:
            if t < 0.5:
                return start + (end - start) * (2 * t * t)
            return start + (end - start) * (-1 + (4 - 2 * t) * t)
        elif easing == Easing.SPRING:
            return start + (end - start) * (
                math.exp(-5 * t) * math.cos(10 * t) + 1 - math.exp(-5)
            )
        elif easing == Easing.BOUNCE:
            if t < 1 / 2.75:
                return start + (end - start) * (7.5625 * t * t)
            elif t < 2 / 2.75:
                t -= 1.5 / 2.75
                return start + (end - start) * (7.5625 * t * t + 0.75)
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                return start + (end - start) * (7.5625 * t * t + 0.9375)
            t -= 2.625 / 2.75
            return start + (end - start) * (7.5625 * t * t + 0.984375)
        elif easing == Easing.ELASTIC:
            if t == 0 or t == 1:
                return start + (end - start) * t
            return start + (end - start) * (
                -math.pow(2, 10 * (t - 1)) * math.sin((t - 1.1) * 5 * math.pi)
            )
        return start + (end - start) * t

    # ------------------------------------------------------------------
    # Convenience animators
    # ------------------------------------------------------------------

    def fade_in(self, target_id: str, duration_ms: int = 300,
                on_complete: Optional[Callable] = None) -> str:
        return self.animate(Animation(
            target_id=target_id, property_name="opacity",
            start_value=0.0, end_value=1.0,
            duration_ms=duration_ms, easing=Easing.EASE_OUT,
            on_complete=on_complete,
        ))

    def fade_out(self, target_id: str, duration_ms: int = 300,
                 on_complete: Optional[Callable] = None) -> str:
        return self.animate(Animation(
            target_id=target_id, property_name="opacity",
            start_value=1.0, end_value=0.0,
            duration_ms=duration_ms, easing=Easing.EASE_IN,
            on_complete=on_complete,
        ))

    def slide_in(self, target_id: str, from_x: float = 100,
                 duration_ms: int = 300,
                 on_complete: Optional[Callable] = None) -> str:
        return self.animate(Animation(
            target_id=target_id, property_name="x",
            start_value=from_x, end_value=0.0,
            duration_ms=duration_ms, easing=Easing.EASE_OUT,
            on_complete=on_complete,
        ))

    def spring_to(self, target_id: str, property_name: str,
                  end_value: float, duration_ms: int = 500) -> str:
        return self.animate(Animation(
            target_id=target_id, property_name=property_name,
            start_value=0.0, end_value=end_value,
            duration_ms=duration_ms, easing=Easing.SPRING,
        ))

    # ------------------------------------------------------------------
    # Particle system
    # ------------------------------------------------------------------

    def burst(self, x: float, y: float, count: int = 20,
              color: str = "#00BFFF", speed: float = 100) -> None:
        """Create a burst of particles at (x, y)."""
        particles = []
        for _ in range(count):
            angle = math.radians(360.0 * _ / count + (hash(str(_)) % 30))
            v = speed * (0.5 + hash(str(_)) % 50 / 100.0)
            particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * v,
                vy=math.sin(angle) * v,
                life=0.5 + (hash(str(_)) % 10) / 10.0,
                max_life=1.0,
                size=2 + (hash(str(_)) % 4),
                color=color,
            ))
        with self._lock:
            self._particles.extend(particles)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._animations)

    @property
    def particle_count(self) -> int:
        with self._lock:
            return len(self._particles)
