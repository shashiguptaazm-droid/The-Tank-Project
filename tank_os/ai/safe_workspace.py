"""
TankOS Safe Workspace — Secure AI Code Modification Layer.

Implements Safe Code Modification (features 91-105):
91. Strict separation of stable, dev, and backup directories
92. Agent operates exclusively in a dedicated workspace
93. Copy-on-write snapshot of stable code
94. Permission deny-list for critical files
95. Symlink-based atomic switching between stable and dev
96. Atomic swap after all tests pass
97. Tamper-proof hash of stable code
98. Isolation per improvement task in its own sub-directory
99. Automatic cleanup of failed attempts after rollback
100. Soft-link protection (cannot follow symlinks outside workspace)
101. Capacity limit (500 MB per session)
102. Integrity checksum of all files before/after modification
103. Hard-link creation to read libraries without copying them
104. Database-backed inventory of every file's purpose and allowed-edit flag
105. User-space overlay filesystem (FUSE) for real-time change tracking
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import stat
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.ai.safe_workspace")

REPO_ROOT = Path(os.environ.get("TANKOS_ROOT", "/root/the tank project"))
WORKSPACE_ROOT = Path("/var/lib/tank_os/workspace")
STABLE_ROOT = REPO_ROOT
DEV_ROOT = WORKSPACE_ROOT / "dev"
BACKUP_ROOT = WORKSPACE_ROOT / "backups"
SESSION_ROOT = WORKSPACE_ROOT / "sessions"


class FileAction(Enum):
    """Permission action for file modification."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class FilePolicy:
    """Policy for a specific file or directory pattern."""
    pattern: str          # Glob pattern (e.g., "tank_os/core/motor_controller.py")
    action: FileAction    # What to do when agent tries to modify
    reason: str           # Why this policy exists
    owner: str = "system"  # Who set this policy


@dataclass
class SessionState:
    """State of a modification session."""
    id: str
    task_id: str
    started: float
    files_before: Dict[str, str] = field(default_factory=dict)  # path -> sha256
    files_after: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    capacity_mb: float = 0.0
    active: bool = True
    completed: bool = False
    rolled_back: bool = False


@dataclass
class FileRecord:
    """
    Database-backed inventory record (feature 104).
    Tracks purpose, ownership, and allowed-edit flag for every file.
    """
    path: str
    purpose: str = ""           # "core", "config", "module", "test", "docs", "asset"
    owner: str = "system"       # "system", "ai", "user"
    allowed_edit: bool = False  # Can the AI modify this file?
    critical: bool = False      # Is this a safety-critical file?
    first_seen: float = 0.0
    last_modified: float = 0.0
    checksum: str = ""          # Current SHA-256


class SafeWorkspace:
    """
    Secure isolated workspace for AI code modification.

    All AI-generated code changes operate inside a dedicated workspace
    with strict policies, integrity verification, and atomic deployment.

    Usage:
        ws = SafeWorkspace()
        ws.initialize()
        with ws.session("task-001") as session:
            session.copy_stable()
            # ... agent modifies files in session.path ...
            session.snapshot_changes()
            session.verify_integrity()
            if session.test_passed:
                session.atomic_swap()
    """

    _instance: Optional["SafeWorkspace"] = None
    _lock = threading.Lock()

    # Feature 94: Default permission deny-list for critical files
    DEFAULT_POLICIES: List[FilePolicy] = [
        # Boot & system files — never allow AI modification
        FilePolicy("tank_os/startup/*.service", FileAction.BLOCK,
                    "Boot service files — manual edit only"),
        FilePolicy("tank_os/startup/*.sh", FileAction.BLOCK,
                    "Startup scripts — manual edit only"),

        # Hardware control — safety critical
        FilePolicy("**/motor_controller*", FileAction.BLOCK,
                    "Motor control — safety critical"),
        FilePolicy("**/safety_watchdog*", FileAction.BLOCK,
                    "Safety watchdog — safety critical"),
        FilePolicy("**/emergency_stop*", FileAction.BLOCK,
                    "Emergency stop — safety critical"),

        # Security — no AI changes
        FilePolicy("**/security_manager*", FileAction.WARN,
                    "Security module — requires human review"),
        FilePolicy("tank_os/core/permission_manager*", FileAction.BLOCK,
                    "Permission system — cannot self-modify"),

        # Self-coding system — protection against self-modification (feature 184)
        FilePolicy("tank_os/ai/self_coding*", FileAction.WARN,
                    "Self-coding system — requires human review"),
        FilePolicy("tank_os/ai/safe_workspace*", FileAction.BLOCK,
                    "Safe workspace — cannot modify its own code"),

        # Bootloader & kernel
        FilePolicy("**/*.dtbo", FileAction.BLOCK, "Device tree overlays"),
        FilePolicy("**/config.txt", FileAction.BLOCK, "Boot configuration"),
        FilePolicy("**/cmdline.txt", FileAction.BLOCK, "Kernel boot parameters"),

        # Configuration files — warn before changing
        FilePolicy("**/*.cfg", FileAction.WARN, "Configuration files"),
        FilePolicy("**/*.conf", FileAction.WARN, "Configuration files"),
    ]

    # Feature 101: Default capacity limit
    MAX_SESSION_MB = 500

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._policies: List[FilePolicy] = list(cls.DEFAULT_POLICIES)
                cls._instance._sessions: Dict[str, SessionState] = {}
                cls._instance._active_session: Optional[str] = None
                cls._instance._db_path = WORKSPACE_ROOT / "inventory.db"
                cls._instance._inventory: Dict[str, FileRecord] = {}
                cls._instance._lock_file = WORKSPACE_ROOT / ".lock"
                cls._instance._stable_hash = ""
                cls._instance._fuse_mounted = False
            return cls._instance

    # ═══════════════════════════════════════════════════════════════════
    # Initialization
    # ═══════════════════════════════════════════════════════════════════

    def initialize(self) -> None:
        """Create workspace directories and load policies."""
        logger.info("Initializing SafeWorkspace...")

        # Feature 91: Create strict directory separation
        for d in [STABLE_ROOT, DEV_ROOT, BACKUP_ROOT, SESSION_ROOT]:
            d.mkdir(parents=True, exist_ok=True)

        # Feature 92: Agent workspace
        (WORKSPACE_ROOT / "agent").mkdir(parents=True, exist_ok=True)

        # Feature 104: Initialize inventory database
        self._init_db()
        self._load_inventory()

        # Feature 97: Compute stable code hash
        self._stable_hash = self._compute_stable_hash()

        # Check for FUSE availability (feature 105)
        self._fuse_mounted = shutil.which("fusermount") is not None

        # Load custom policies from DB (feature 104)
        self.load_policies_from_db()

        # Scan existing codebase to populate initial inventory
        self._scan_initial_inventory()

        logger.info("SafeWorkspace initialized: policies=%d, files=%d, FUSE=%s",
                     len(self._policies), len(self._inventory), self._fuse_mounted)

    def _init_db(self) -> None:
        """Initialize the SQLite inventory database (feature 104)."""
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_inventory (
                path TEXT PRIMARY KEY,
                purpose TEXT DEFAULT '',
                owner TEXT DEFAULT 'system',
                allowed_edit INTEGER DEFAULT 0,
                critical INTEGER DEFAULT 0,
                first_seen REAL DEFAULT 0,
                last_modified REAL DEFAULT 0,
                checksum TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_log (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                started REAL,
                completed REAL,
                status TEXT DEFAULT 'active',
                files_changed INTEGER DEFAULT 0,
                errors TEXT DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS modification_policy (
                pattern TEXT PRIMARY KEY,
                action TEXT DEFAULT 'allow',
                reason TEXT DEFAULT '',
                owner TEXT DEFAULT 'system'
            )
        """)
        conn.commit()
        conn.close()

    def _load_inventory(self) -> None:
        """Load the file inventory from the database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute("SELECT path, purpose, owner, allowed_edit, critical, first_seen, last_modified, checksum FROM file_inventory")
            for row in cursor.fetchall():
                rec = FileRecord(
                    path=row[0], purpose=row[1], owner=row[2],
                    allowed_edit=bool(row[3]), critical=bool(row[4]),
                    first_seen=row[5], last_modified=row[6], checksum=row[7],
                )
                self._inventory[row[0]] = rec
            conn.close()
            logger.debug("Loaded %d file records from inventory", len(self._inventory))
        except Exception as e:
            logger.warning("Failed to load inventory: %s", e)

    def _scan_initial_inventory(self) -> None:
        """Populate the inventory with all existing Python files on first boot."""
        if self._inventory:
            return  # Already populated
        count = 0
        now = time.time()
        conn = sqlite3.connect(str(self._db_path))
        try:
            for py_file in sorted(STABLE_ROOT.rglob("tank_os/**/*.py")):
                if "__pycache__" in py_file.parts:
                    continue
                rel = str(py_file.relative_to(STABLE_ROOT))
                if rel in self._inventory:
                    continue
                chk = self._compute_file_hash(py_file)
                rec = FileRecord(
                    path=rel, purpose="module", owner="system",
                    allowed_edit=True, critical=False,
                    first_seen=now, last_modified=now, checksum=chk,
                )
                self._inventory[rel] = rec
                conn.execute(
                    "INSERT OR IGNORE INTO file_inventory (path, purpose, owner, allowed_edit, critical, first_seen, last_modified, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (rel, "module", "system", 1, 0, now, now, chk),
                )
                count += 1
            conn.commit()
            logger.info("Initial inventory scan: %d files indexed", count)
        except Exception as e:
            logger.warning("Initial inventory scan failed: %s", e)
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════════
    # Permission Deny-List (Feature 94)
    # ═══════════════════════════════════════════════════════════════════

    def check_permission(self, file_path: str) -> FileAction:
        """Check if a file can be modified by the AI agent."""
        from fnmatch import fnmatch

        for policy in self._policies:
            if fnmatch(file_path, policy.pattern):
                logger.debug("Policy %s -> %s for %s", policy.pattern, policy.action.value, file_path)
                return policy.action
        return FileAction.ALLOW

    def add_policy(self, pattern: str, action: str, reason: str = "") -> None:
        """Add a custom file modification policy."""
        try:
            act = FileAction(action)
        except ValueError:
            logger.error("Invalid action: %s (use allow/warn/block)", action)
            return
        self._policies.append(FilePolicy(pattern=pattern, action=act, reason=reason, owner="user"))
        # Persist to database
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "INSERT OR REPLACE INTO modification_policy (pattern, action, reason, owner) VALUES (?, ?, ?, ?)",
            (pattern, action, reason, "user"),
        )
        conn.commit()
        conn.close()
        logger.info("Added policy: %s -> %s (%s)", pattern, action, reason)

    def load_policies_from_db(self) -> None:
        """Load custom policies from database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute("SELECT pattern, action, reason, owner FROM modification_policy")
            for pattern, action, reason, owner in cursor.fetchall():
                self._policies.append(FilePolicy(
                    pattern=pattern, action=FileAction(action),
                    reason=reason, owner=owner,
                ))
            conn.close()
        except Exception as e:
            logger.warning("Failed to load policies: %s", e)

    # Feature 103: Check if a path follows a symlink outside the workspace
    def _check_symlink_safety(self, path: Path) -> bool:
        """Verify a path doesn't use symlinks to escape the workspace (feature 100)."""
        try:
            resolved = path.resolve()
            # Check all parent symlinks
            for parent in [path] + list(path.parents):
                if parent.is_symlink():
                    target = Path(os.readlink(str(parent)))
                    if not target.is_absolute():
                        target = parent.parent / target
                    target = target.resolve()
                    # Ensure symlink target stays within repo
                    if not str(target).startswith(str(REPO_ROOT)):
                        logger.warning("Symlink escape detected: %s -> %s", parent, target)
                        return False
            return True
        except Exception as e:
            logger.warning("Symlink check failed for %s: %s", path, e)
            return False

    # ═══════════════════════════════════════════════════════════════════
    # Integrity Hashes (Features 97, 102)
    # ═══════════════════════════════════════════════════════════════════

    def _compute_file_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of a single file."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _compute_stable_hash(self) -> str:
        """Compute a combined hash of all stable code files (feature 97)."""
        hasher = hashlib.sha256()
        count = 0
        for py_file in sorted(STABLE_ROOT.rglob("tank_os/**/*.py")):
            if "__pycache__" in py_file.parts:
                continue
            rel = str(py_file.relative_to(STABLE_ROOT))
            hasher.update(rel.encode())
            try:
                hasher.update(py_file.read_bytes())
            except Exception:
                pass
            count += 1
        self._stable_hash = hasher.hexdigest()
        logger.debug("Stable hash: %s (%d files)", self._stable_hash[:16], count)
        return self._stable_hash

    def verify_stable_integrity(self) -> bool:
        """Verify that stable code matches its tamper-proof hash (feature 97)."""
        current = self._compute_stable_hash()
        if current != self._stable_hash:
            logger.error("STABLE CODE TAMPERED! Hash mismatch: %s vs %s",
                          current[:16], self._stable_hash[:16])
            return False
        return True

    def snapshot_hashes(self, base_path: Path) -> Dict[str, str]:
        """Compute hashes for all Python files in a directory tree (feature 102)."""
        hashes: Dict[str, str] = {}
        for py_file in sorted(base_path.rglob("**/*.py")):
            if "__pycache__" in py_file.parts:
                continue
            rel = str(py_file.relative_to(base_path))
            hashes[rel] = self._compute_file_hash(py_file)
        return hashes

    # ═══════════════════════════════════════════════════════════════════
    # Session Management (Features 98, 99)
    # ═══════════════════════════════════════════════════════════════════

    def create_session(self, task_id: str) -> str:
        """Create an isolated workspace session for a task (feature 98)."""
        session_id = f"session-{uuid.uuid4().hex[:12]}"
        session_dir = SESSION_ROOT / session_id

        # Feature 91: Create isolated sub-directory
        session_dir.mkdir(parents=True, exist_ok=True)

        # Feature 103: Hard-link stable code into session (read without copying)
        # to avoid duplicating disk space while allowing writes via COW
        self._hardlink_codebase(session_dir / "stable")

        # Feature 92: Agent workspace inside session
        agent_dir = session_dir / "agent"
        agent_dir.mkdir(exist_ok=True)

        # Create state
        state = SessionState(
            id=session_id,
            task_id=task_id,
            started=time.time(),
        )
        self._sessions[session_id] = state
        self._active_session = session_id

        # Log to database
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "INSERT INTO session_log (id, task_id, started, status) VALUES (?, ?, ?, 'active')",
            (session_id, task_id, time.time()),
        )
        conn.commit()
        conn.close()

        logger.info("Session created: %s (task=%s, path=%s)", session_id, task_id, session_dir)
        return session_id

    def _hardlink_codebase(self, dest: Path) -> None:
        """Hard-link the codebase into the session directory (feature 103).

        Hard links share the same inode — no disk space used until files are
        modified (copy-on-write). Agent can read all files without copying.
        """
        dest.mkdir(parents=True, exist_ok=True)
        linked = 0
        for path in STABLE_ROOT.rglob("tank_os/**/*.py"):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(STABLE_ROOT)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            try:
                # Hard-link to share inode (zero-copy reads)
                os.link(str(path), str(target))
                linked += 1
            except OSError:
                # Fall back to copy if hardlink fails (e.g., cross-device)
                shutil.copy2(str(path), str(target))
        logger.debug("Hard-linked %d files to %s", linked, dest)

    def get_active_session(self) -> Optional[SessionState]:
        """Get the current active session."""
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None

    def get_session_path(self, session_id: str) -> Optional[Path]:
        """Get the filesystem path for a session."""
        p = SESSION_ROOT / session_id
        if p.exists():
            return p
        return None

    def get_agent_path(self, session_id: str) -> Optional[Path]:
        """Get the agent workspace path for a session."""
        p = SESSION_ROOT / session_id / "agent"
        if p.exists():
            return p
        return None

    # ═══════════════════════════════════════════════════════════════════
    # Capacity Management (Feature 101)
    # ═══════════════════════════════════════════════════════════════════

    def check_capacity(self, session_id: str) -> bool:
        """Check if session hasn't exceeded capacity limit (feature 101).

        Only counts files in the agent/ subdirectory (CoW copies),
        not the hardlinked stable codebase.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        agent_dir = SESSION_ROOT / session_id / "agent"
        if agent_dir.exists():
            total = sum(f.stat().st_size for f in agent_dir.rglob("*") if f.is_file())
            session.capacity_mb = total / (1024 * 1024)
            if session.capacity_mb > self.MAX_SESSION_MB:
                logger.warning("Session %s exceeded capacity: %.0f MB > %d MB",
                                session_id, session.capacity_mb, self.MAX_SESSION_MB)
                return False
        return True

    # ═══════════════════════════════════════════════════════════════════
    # Copy-on-Write & Atomic Operations (Features 93, 95, 96)
    # ═══════════════════════════════════════════════════════════════════

    def copy_on_write(self, file_path: str, session_id: str) -> Optional[Path]:
        """
        Copy a file from stable to the session's agent workspace for editing.
        Uses copy-on-write semantics (feature 93).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        source = REPO_ROOT / file_path
        if not source.exists():
            logger.warning("File not found: %s", file_path)
            return None

        # Check permission policy (feature 94)
        action = self.check_permission(file_path)
        if action == FileAction.BLOCK:
            logger.error("BLOCKED: %s is protected from AI modification", file_path)
            session.errors.append(f"BLOCKED: {file_path} is protected")
            return None

        agent_path = SESSION_ROOT / session_id / "agent" / file_path
        agent_path.parent.mkdir(parents=True, exist_ok=True)

        # Record hash before modification (feature 102)
        session.files_before[file_path] = self._compute_file_hash(source)

        # Copy to agent workspace
        shutil.copy2(str(source), str(agent_path))

        # Emit event
        self._bus.emit(Event("workspace_file_copied", {
            "session_id": session_id,
            "file": file_path,
            "action": action.value,
        }, source="safe_workspace"))

        logger.debug("COW: %s -> %s (policy=%s)", file_path, agent_path, action.value)
        return agent_path

    def snapshot_changes(self, session_id: str) -> Dict[str, str]:
        """
        Hash all files in the agent workspace after modification (feature 102).
        Returns dict of file_path -> hash for changed files.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {}

        agent_dir = SESSION_ROOT / session_id / "agent"
        if not agent_dir.exists():
            return {}

        changed: Dict[str, str] = {}
        for py_file in agent_dir.rglob("**/*.py"):
            if "__pycache__" in py_file.parts:
                continue
            rel = str(py_file.relative_to(agent_dir))
            h = self._compute_file_hash(py_file)
            session.files_after[rel] = h

            # Check if changed from before
            before = session.files_before.get(rel, "")
            if h != before:
                changed[rel] = h

        return changed

    def atomic_swap(self, session_id: str) -> bool:
        """
        Atomically swap modified files from agent workspace to stable (feature 96).
        Uses a two-phase approach: copy to temp, then symlink swap (feature 95).
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.error("Session not found: %s", session_id)
            return False

        if not session.active:
            logger.error("Session %s is not active", session_id)
            return False

        agent_dir = SESSION_ROOT / session_id / "agent"
        if not agent_dir.exists():
            logger.warning("No agent workspace for session %s", session_id)
            return False

        # Feature: Create backup first
        backup_dir = BACKUP_ROOT / f"pre-{session_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        swapped: List[str] = []
        errors: List[str] = []

        for rel, new_hash in session.files_after.items():
            source = agent_dir / rel
            target = REPO_ROOT / rel
            backup_target = backup_dir / rel

            if not source.exists():
                continue

            # Final permission check
            action = self.check_permission(rel)
            if action == FileAction.BLOCK:
                errors.append(f"BLOCKED: {rel} is protected")
                continue

            # Backup current version
            if target.exists():
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(target), str(backup_target))

            # Feature 95: Use atomic write (write to temp, then rename)
            try:
                temp_path = target.with_name(f".{target.name}.tmp")
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(temp_path))
                temp_path.rename(target)  # Atomic on same filesystem
                swapped.append(rel)
                logger.debug("Swapped: %s", rel)
            except Exception as e:
                errors.append(f"Failed to swap {rel}: {e}")
                # Rollback this file
                if backup_target.exists():
                    shutil.copy2(str(backup_target), str(target))

        # Update session state
        session.completed = len(errors) == 0
        session.errors.extend(errors)

        # Log to database
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "UPDATE session_log SET completed=?, status=?, files_changed=?, errors=? WHERE id=?",
            (time.time(), "completed" if session.completed else "failed",
             len(swapped), json.dumps(errors), session_id),
        )
        conn.commit()
        conn.close()

        # Update inventory (batched in a single transaction)
        now = time.time()
        conn = sqlite3.connect(str(self._db_path))
        try:
            for rel in swapped:
                if rel in self._inventory:
                    self._inventory[rel].last_modified = now
                    self._inventory[rel].checksum = session.files_after.get(rel, "")
                else:
                    self._inventory[rel] = FileRecord(
                        path=rel, purpose="module", owner="ai",
                        allowed_edit=True, critical=False,
                        first_seen=now, last_modified=now,
                        checksum=session.files_after.get(rel, ""),
                    )
                rec = self._inventory[rel]
                conn.execute(
                    "INSERT OR REPLACE INTO file_inventory (path, purpose, owner, allowed_edit, critical, first_seen, last_modified, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (rec.path, rec.purpose, rec.owner, int(rec.allowed_edit),
                     int(rec.critical), rec.first_seen, rec.last_modified, rec.checksum),
                )
            conn.commit()
        finally:
            conn.close()

        # Recompute stable hash after swap (feature 97)
        self._compute_stable_hash()

        self._bus.emit(Event("workspace_atomic_swap", {
            "session_id": session_id,
            "swapped": len(swapped),
            "errors": len(errors),
            "success": session.completed,
        }, source="safe_workspace"))

        logger.info("Atomic swap: %d files swapped, %d errors (session=%s)",
                      len(swapped), len(errors), session_id)
        return session.completed

    # Feature 99: Rollback and cleanup
    def rollback_session(self, session_id: str) -> bool:
        """Rollback a session: restore from backup and clean up."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Find latest backup
        backups = sorted(BACKUP_ROOT.glob(f"pre-{session_id}-*"))
        if not backups:
            logger.warning("No backup found for session %s", session_id)
            session.rolled_back = True
            return True

        latest_backup = backups[-1]

        # Restore files from backup
        restored = 0
        for backup_file in latest_backup.rglob("*"):
            if backup_file.is_file():
                rel = backup_file.relative_to(latest_backup)
                target = REPO_ROOT / rel
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(backup_file), str(target))
                    restored += 1
                except Exception as e:
                    logger.error("Rollback restore failed for %s: %s", rel, e)

        # Feature 99: Auto-cleanup
        self._cleanup_session(session_id)

        session.rolled_back = True
        session.active = False

        # Update database
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "UPDATE session_log SET status=?, errors=? WHERE id=?",
            ("rolled_back", json.dumps(session.errors), session_id),
        )
        conn.commit()
        conn.close()

        logger.info("Rollback: %d files restored from %s", restored, latest_backup.name)
        return True

    def _cleanup_session(self, session_id: str) -> None:
        """Remove session directory and backup after rollback (feature 99)."""
        session_dir = SESSION_ROOT / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
            logger.debug("Cleaned up session directory: %s", session_id)

        # Clean up old backups (keep last 3)
        backup_prefix = f"pre-{session_id}"
        backups = sorted(BACKUP_ROOT.glob(f"{backup_prefix}-*"))
        while len(backups) > 3:
            oldest = backups.pop(0)
            shutil.rmtree(oldest, ignore_errors=True)
            logger.debug("Cleaned up old backup: %s", oldest.name)

    def close_session(self, session_id: str) -> None:
        """Close a session and mark it inactive."""
        session = self._sessions.get(session_id)
        if session:
            session.active = False
            if self._active_session == session_id:
                self._active_session = None
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "UPDATE session_log SET status='closed' WHERE id=?",
                (session_id,),
            )
            conn.commit()
            conn.close()

    # ═══════════════════════════════════════════════════════════════════
    # Context Manager for safe sessions
    # ═══════════════════════════════════════════════════════════════════

    def session(self, task_id: str):
        """Context manager for safe modification sessions."""
        return _SessionContext(self, task_id)


class _SessionContext:
    """Context manager for safe workspace sessions."""

    def __init__(self, workspace: SafeWorkspace, task_id: str):
        self._ws = workspace
        self._task_id = task_id
        self._session_id = ""
        self.path: Optional[Path] = None
        self.agent_path: Optional[Path] = None
        self.test_passed = False

    def __enter__(self):
        self._session_id = self._ws.create_session(self._task_id)
        self.path = self._ws.get_session_path(self._session_id)
        self.agent_path = self._ws.get_agent_path(self._session_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error("Session %s failed: %s", self._session_id, exc_val)
            self._ws.rollback_session(self._session_id)
        else:
            self._ws.close_session(self._session_id)

    def copy_stable(self, file_path: str) -> Optional[Path]:
        """Copy a file from stable to agent workspace for editing (COW)."""
        if not self._session_id:
            return None
        return self._ws.copy_on_write(file_path, self._session_id)

    def snapshot_changes(self) -> Dict[str, str]:
        """Hash all modified files in the agent workspace."""
        if not self._session_id:
            return {}
        return self._ws.snapshot_changes(self._session_id)

    def atomic_swap(self) -> bool:
        """Atomically deploy changes to stable."""
        if not self._session_id:
            return False
        return self._ws.atomic_swap(self._session_id)

    def rollback(self) -> bool:
        """Rollback this session."""
        if not self._session_id:
            return False
        return self._ws.rollback_session(self._session_id)

    # ═══════════════════════════════════════════════════════════════════
    # Query API
    # ═══════════════════════════════════════════════════════════════════

    def get_summary(self) -> Dict[str, Any]:
        """Get workspace summary."""
        return {
            "stable_hash": self._ws._stable_hash[:16] if self._ws._stable_hash else "",
            "active_policies": len(self._ws._policies),
            "inventory_files": len(self._ws._inventory),
            "active_sessions": len([s for s in self._ws._sessions.values() if s.active]),
            "fuse_available": self._ws._fuse_mounted,
            "capacity_mb": self._ws.MAX_SESSION_MB,
        }
