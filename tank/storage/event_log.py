"""Tank — SQLite Event & Telemetry Storage.

Every important event is logged with timestamp, type, source, data.
Queryable for analysis, debugging, and competition demos.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank.storage")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "tank_events.db"


class EventStorage:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None

    def connect(self) -> bool:
        try:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._create_tables()
            logger.info(f"Storage connected: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Storage connect failed: {e}")
            return False

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 0.0,
                data TEXT,
                system_state TEXT
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                unit TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                confidence REAL DEFAULT 0.0,
                source TEXT,
                params TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_telemetry_metric ON telemetry(metric);
        """)

    def log_event(self, event_type: str, source: str, confidence: float = 0.0,
                  data: Dict = None, system_state: str = "") -> None:
        if not self._conn:
            return
        self._conn.execute(
            "INSERT INTO events (timestamp, event_type, source, confidence, data, system_state) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), event_type, source, confidence, json.dumps(data or {}), system_state)
        )
        self._conn.commit()

    def log_telemetry(self, metric: str, value: float, unit: str = "", data: Dict = None) -> None:
        if not self._conn:
            return
        self._conn.execute(
            "INSERT INTO telemetry (timestamp, metric, value, unit, data) VALUES (?, ?, ?, ?, ?)",
            (time.time(), metric, value, unit, json.dumps(data or {}))
        )
        self._conn.commit()

    def log_decision(self, action: str, reason: str, confidence: float, source: str, params: Dict = None) -> None:
        if not self._conn:
            return
        self._conn.execute(
            "INSERT INTO decisions (timestamp, action, reason, confidence, source, params) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), action, reason, confidence, source, json.dumps(params or {}))
        )
        self._conn.commit()

    def query_events(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        if not self._conn:
            return []
        if event_type:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"id": r[0], "timestamp": r[1], "event_type": r[2], "source": r[3],
                 "confidence": r[4], "data": json.loads(r[5] or "{}"), "system_state": r[6]} for r in rows]

    def query_telemetry(self, metric: str = None, limit: int = 100) -> List[Dict]:
        if not self._conn:
            return []
        if metric:
            rows = self._conn.execute(
                "SELECT * FROM telemetry WHERE metric = ? ORDER BY timestamp DESC LIMIT ?",
                (metric, limit)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "timestamp": r[1], "metric": r[2], "value": r[3],
                 "unit": r[4], "data": json.loads(r[5] or "{}")} for r in rows]

    def stats(self) -> Dict[str, Any]:
        if not self._conn:
            return {"connected": False}
        event_count = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        telemetry_count = self._conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
        decision_count = self._conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        return {
            "connected": True,
            "events": event_count,
            "telemetry": telemetry_count,
            "decisions": decision_count,
            "db_path": str(self.db_path),
        }

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
