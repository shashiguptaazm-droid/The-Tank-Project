"""TankOS Window Manager — floating windows, dialogs, fullscreen, blur, gestures."""

from __future__ import annotations
import logging, threading, uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.window_manager")


class WindowState(Enum):
    NORMAL = auto()
    MINIMIZED = auto()
    MAXIMIZED = auto()
    FULLSCREEN = auto()


@dataclass
class Window:
    id: str = ""
    title: str = ""
    widget: Any = None  # Qt widget
    x: int = 0; y: int = 0; width: int = 400; height: int = 300
    state: WindowState = WindowState.NORMAL
    modal: bool = False
    resizable: bool = True
    closable: bool = True
    opacity: float = 1.0
    blur: bool = False
    z_index: int = 0


class WindowManager:
    _instance: Optional["WindowManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "WindowManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._windows: Dict[str, Window] = {}
                cls._instance._z_counter = 0
                cls._instance._bus = EventBus()
            return cls._instance

    def create_window(self, title: str, widget: Any = None,
                      width: int = 400, height: int = 300,
                      modal: bool = False, resizable: bool = True) -> Window:
        wid = f"win_{uuid.uuid4().hex[:8]}"
        win = Window(id=wid, title=title, widget=widget,
                     width=width, height=height, modal=modal, resizable=resizable,
                     z_index=self._z_counter)
        self._z_counter += 1
        self._windows[wid] = win
        self._bus.emit(Event("window_opened", {"id": wid, "title": title}))
        return win

    def close_window(self, win_id: str) -> bool:
        win = self._windows.pop(win_id, None)
        if win: self._bus.emit(Event("window_closed", {"id": win_id}))
        return win is not None

    def focus(self, win_id: str) -> None:
        win = self._windows.get(win_id)
        if win:
            self._z_counter += 1
            win.z_index = self._z_counter
            self._bus.emit(Event("window_focused", {"id": win_id}))

    def move_to(self, win_id: str, x: int, y: int) -> None:
        win = self._windows.get(win_id)
        if win: win.x, win.y = x, y

    def resize(self, win_id: str, w: int, h: int) -> None:
        win = self._windows.get(win_id)
        if win: win.width, win.height = w, h

    def set_state(self, win_id: str, state: WindowState) -> None:
        win = self._windows.get(win_id)
        if win: win.state = state

    def get(self, win_id: str) -> Optional[Window]:
        return self._windows.get(win_id)

    def all(self) -> List[Window]:
        return sorted(self._windows.values(), key=lambda w: w.z_index)

    def count(self) -> int:
        return len(self._windows)

    def close_all(self) -> None:
        for wid in list(self._windows.keys()):
            self.close_window(wid)
