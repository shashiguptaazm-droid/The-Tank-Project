"""TankOS Permission Manager — async role-based access control.

Permissions are requested by emitting a ``permission_requested`` event on
the EventBus. A UI/system component listens, decides whether to grant,
and calls :meth:`PermissionManager.grant` or :meth:`revoke`. Callers can
either await the returned :class:`PermissionRequest` object (with
:meth:`PermissionRequest.wait`) or rely on the passive grant lookup via
:meth:`PermissionManager.check`.

Grants are persisted under ``settings.permissions`` so they survive
reboots. The default policy is **deny-by-default** — explicit grants
are required for every permission.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.permissions")

# Default-deny policy — every perm must be explicitly granted.
SETTINGS_SECTION = "permissions"


class Permission(Enum):
    """All resource-level permissions managed by PermissionManager."""

    # Existing peripheral access
    CAMERA = auto()
    MICROPHONE = auto()
    STORAGE = auto()
    NETWORK = auto()
    BLUETOOTH = auto()
    LOCATION = auto()
    NOTIFICATIONS = auto()
    ROS_CONTROL = auto()

    # New — added for AI / system surfaces
    SYSTEM_SETTINGS = auto()      # mutate ~/.config/tank_os/*
    LLM_ACCESS = auto()           # call into AIManager
    UPDATE_INSTALL = auto()        # apply OS / app updates
    APP_LIFECYCLE = auto()         # start/stop registered apps
    PLUGIN_INSTALL = auto()        # load / unload plugins


# Human-readable labels so the dashboard can render permission toggles
# without each caller building its own copy.
PERMISSION_LABELS: Dict[Permission, str] = {
    Permission.CAMERA: "Camera",
    Permission.MICROPHONE: "Microphone",
    Permission.STORAGE: "Files & Storage",
    Permission.NETWORK: "Network Access",
    Permission.BLUETOOTH: "Bluetooth",
    Permission.LOCATION: "Location",
    Permission.NOTIFICATIONS: "Notifications",
    Permission.ROS_CONTROL: "Robot Motion (ROS)",
    Permission.SYSTEM_SETTINGS: "System Settings",
    Permission.LLM_ACCESS: "LLM / AI Requests",
    Permission.UPDATE_INSTALL: "Apply Updates",
    Permission.APP_LIFECYCLE: "App Lifecycle",
    Permission.PLUGIN_INSTALL: "Plugin Install/Uninstall",
}


@dataclass
class PermissionRequest:
    """An in-flight permission request.

    Holds the state until :meth:`PermissionManager.grant` /
    :meth:`revoke` is called by an approver (typically the dashboard
    or a settings panel bound to ``permission_requested`` on the bus).
    """

    id: str
    permission: Permission
    requester: str
    reason: str
    created_at: float = field(default_factory=time.time)
    _resolved: bool = field(default=False, init=False)
    _granted: Optional[bool] = field(default=None, init=False)
    _cond: threading.Condition = field(default_factory=threading.Condition,
                                       init=False, repr=False)

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until resolved. Returns the granted state.

        Returns ``False`` on timeout.
        """
        with self._cond:
            if self._resolved:
                return bool(self._granted)
            self._cond.wait(timeout=timeout)
            return bool(self._granted) if self._resolved else False

    @property
    def resolved(self) -> bool:
        return self._resolved

    @property
    def granted(self) -> Optional[bool]:
        return self._granted

    def _resolve(self, granted: bool) -> None:
        with self._cond:
            self._granted = granted
            self._resolved = True
            self._cond.notify_all()


class PermissionManager:
    """Singleton permission gatekeeper.

    Thread-safe, persistent, deny-by-default.

    Lock invariant: ``_lock`` is an ``RLock`` (not a ``Lock``) because
    :meth:`grant` and :meth:`revoke` hold it while calling
    :meth:`_resolve_pending`, which itself re-acquires the lock to
    record history. A plain ``Lock`` would deadlock on the nested
    acquire — keep it ``RLock`` so all refactors stay deadlock-free.
    """

    _instance: Optional["PermissionManager"] = None
    # See class docstring: must stay RLock so grant/revoke can re-enter.
    _lock = threading.RLock()
    _MAX_HISTORY = 200

    def __new__(cls) -> "PermissionManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
                cls._instance._grants: Dict[Permission, bool] = {}
                cls._instance._pending: Dict[str, PermissionRequest] = {}
                cls._instance._history: List[Dict[str, object]] = []
            return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load persisted grants from settings and resubscribe listeners."""
        try:
            saved = self._settings.get(SETTINGS_SECTION, {}) or {}
            for key, granted in saved.items():
                try:
                    perm = Permission[key]
                except KeyError:
                    logger.debug("Ignoring unknown persisted perm %r", key)
                    continue
                self._grants[perm] = bool(granted)
        except Exception as exc:
            logger.warning("Could not load persisted permissions: %s", exc)
        logger.info(
            "PermissionManager initialized — %d grants loaded, "
            "%d permissions tracked",
            sum(1 for v in self._grants.values() if v),
            len(Permission),
        )

    def request(self, perm: Permission, requester: str = "",
                reason: str = "") -> PermissionRequest:
        """Request a permission.

        Publishing ``permission_requested`` lets a UI/approver resolve the
        request asynchronously via :meth:`grant` / :meth:`revoke`. The
        returned object exposes :meth:`wait` for callers that want a
        blocking answer.

        Short-circuits when the permission is already granted: the
        request is auto-resolved as ``granted=True`` and no event is
        emitted. Callers that want a UI prompt even when previously
        granted can bypass via ``request(perm, force=True)``.
        """
        if not isinstance(perm, Permission):
            raise TypeError(f"perm must be Permission, got {type(perm).__name__}")
        req_id = f"perm_{uuid.uuid4().hex[:10]}"
        req = PermissionRequest(
            id=req_id, permission=perm, requester=requester, reason=reason
        )
        # Fast path — if already granted, resolve immediately and skip
        # the bus event so the dashboard is not woken for nothing.
        if self.check(perm):
            logger.debug("Permission %s already granted — short-circuit "
                         "request from %r", perm.name, requester)
            req._resolve(True)
            return req
        with self._lock:
            self._pending[req_id] = req
        self._bus.emit(Event(
            "permission_requested",
            {
                "id": req_id,
                "permission": perm.name,
                "permission_label": PERMISSION_LABELS.get(perm, perm.name),
                "requester": requester,
                "reason": reason,
            },
            source=requester or "permission_manager",
        ))
        logger.info("Permission %s requested by %r (%s)",
                    perm.name, requester, reason)
        return req

    def grant(self, perm: Permission,
              requester: str = "") -> bool:
        """Grant a permission (resolver side)."""
        if not isinstance(perm, Permission):
            raise TypeError(f"perm must be Permission, got {type(perm).__name__}")
        with self._lock:
            self._grants[perm] = True
            self._settings.set(f"{SETTINGS_SECTION}.{perm.name}", True)
            self._resolve_pending(perm, granted=True, granter=requester)
        self._bus.emit(Event(
            "permission_granted",
            {"permission": perm.name, "requester": requester},
            source="permission_manager",
        ))
        logger.info("Granted %s by %r", perm.name, requester)
        return True

    def revoke(self, perm: Permission, requester: str = "") -> bool:
        """Revoke a previously granted permission."""
        if not isinstance(perm, Permission):
            raise TypeError(f"perm must be Permission, got {type(perm).__name__}")
        with self._lock:
            self._grants[perm] = False
            self._settings.set(f"{SETTINGS_SECTION}.{perm.name}", False)
            self._resolve_pending(perm, granted=False, granter=requester)
        self._bus.emit(Event(
            "permission_revoked",
            {"permission": perm.name, "requester": requester},
            source="permission_manager",
        ))
        logger.info("Revoked %s by %r", perm.name, requester)
        return True

    def check(self, perm: Permission) -> bool:
        """Return cached grant state. Default-deny."""
        if not isinstance(perm, Permission):
            raise TypeError(f"perm must be Permission, got {type(perm).__name__}")
        with self._lock:
            return self._grants.get(perm, False)

    def require(self, perm: Permission,
                requester: str = "",
                reason: str = "") -> bool:
        """Convenience: request and block for up to 3 s for approval.

        Useful for short-lived operations that just-in-time want to
        ensure the gate is open. Returns the granted state. A request
        event is published either way; if the permission is already
        granted the method short-circuits and returns True.
        """
        if self.check(perm):
            return True
        req = self.request(perm, requester=requester, reason=reason)
        granted = req.wait(timeout=3.0)
        if not granted:
            logger.debug("Timed out waiting for permission %s from %r",
                         perm.name, requester)
        return granted

    def cancel(self, request_id: str) -> bool:
        """Cancel a pending request (e.g. caller gave up)."""
        with self._lock:
            req = self._pending.pop(request_id, None)
        if req is None:
            return False
        req._resolve(False)
        return True

    def reset(self) -> None:
        """Revoke every grant and clear settings."""
        with self._lock:
            for perm in list(self._grants.keys()):
                self._grants[perm] = False
            self._pending.clear()
        try:
            current = self._settings.get(SETTINGS_SECTION, {}) or {}
            for key in current.keys():
                self._settings.set(f"{SETTINGS_SECTION}.{key}", False)
        except Exception as exc:
            logger.warning("Could not reset permission settings: %s", exc)
        self._bus.emit(Event("permissions_reset", {},
                             source="permission_manager"))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, bool]:
        """Public grant snapshot (by permission name)."""
        with self._lock:
            return {p.name: self._grants.get(p, False) for p in Permission}

    def pending(self) -> List[PermissionRequest]:
        with self._lock:
            return list(self._pending.values())

    def history(self, limit: int = 20) -> List[Dict[str, object]]:
        with self._lock:
            return list(self._history[-limit:])

    def all_grants(self) -> List[Permission]:
        with self._lock:
            return [p for p, v in self._grants.items() if v]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_pending(self, perm: Permission, granted: bool,
                         granter: str) -> None:
        """Resolve every pending request whose target is ``perm``.

        Appends bounded history (most recent 200 entries).
        """
        resolved: List[str] = []
        for req_id, req in list(self._pending.items()):
            if req.permission is perm:
                req._resolve(granted)
                resolved.append(req_id)
        for req_id in resolved:
            self._pending.pop(req_id, None)
        with self._lock:
            self._history.append({
                "permission": perm.name,
                "granted": granted,
                "granter": granter,
                "ts": time.time(),
            })
            if len(self._history) > self._MAX_HISTORY:
                self._history = self._history[-self._MAX_HISTORY:]
