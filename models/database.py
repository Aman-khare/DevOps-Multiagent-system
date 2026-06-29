"""
Async SQLite database layer for incidents and audit logs.
Uses aiosqlite for non-blocking database operations.
"""

import json
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

import aiosqlite

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "devops_ai.db")


class Database:
    """Async SQLite database manager for incident storage and audit logging."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize the database connection and create tables."""
        db_parent = Path(self.db_path).expanduser().resolve().parent
        db_parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close the database connection."""
        if self.db:
            await self.db.close()
            self.db = None

    async def _create_tables(self):
        """Create all required tables if they don't exist."""
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                service TEXT NOT NULL DEFAULT 'unknown',
                container_id TEXT,
                host TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'detected',
                agent_trace TEXT DEFAULT '[]',
                root_cause TEXT,
                resolution TEXT,
                postmortem TEXT,
                commands_executed TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT,
                agent_name TEXT NOT NULL,
                command TEXT NOT NULL,
                output TEXT,
                status TEXT NOT NULL DEFAULT 'success',
                executed_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id)
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
            CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at);
            CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_logs(incident_id);
        """)
        await self.db.commit()

    async def create_incident(self, incident_data: dict) -> str:
        """Insert a new incident record. Returns the incident ID."""
        await self.db.execute(
            """INSERT INTO incidents
               (id, alert_type, severity, service, container_id, host, message,
                status, agent_trace, root_cause, resolution, postmortem,
                commands_executed, created_at, resolved_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident_data["id"],
                incident_data["alert_type"],
                incident_data.get("severity", "warning"),
                incident_data.get("service", "unknown"),
                incident_data.get("container_id"),
                incident_data.get("host"),
                incident_data["message"],
                incident_data.get("status", "detected"),
                json.dumps(incident_data.get("agent_trace", [])),
                incident_data.get("root_cause"),
                incident_data.get("resolution"),
                incident_data.get("postmortem"),
                json.dumps(incident_data.get("commands_executed", [])),
                incident_data.get("created_at", datetime.now(UTC).isoformat()),
                incident_data.get("resolved_at"),
                incident_data.get("updated_at", datetime.now(UTC).isoformat()),
            ),
        )
        await self.db.commit()
        return incident_data["id"]

    async def update_incident(self, incident_id: str, updates: dict):
        """Update specific fields on an incident record."""
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key in ("agent_trace", "commands_executed"):
                value = json.dumps(value) if isinstance(value, list) else value
            set_clauses.append(f"{key} = ?")
            values.append(value)

        set_clauses.append("updated_at = ?")
        values.append(datetime.now(UTC).isoformat())
        values.append(incident_id)

        query = f"UPDATE incidents SET {', '.join(set_clauses)} WHERE id = ?"
        await self.db.execute(query, values)
        await self.db.commit()

    async def get_incident(self, incident_id: str) -> Optional[dict]:
        """Fetch a single incident by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    async def list_incidents(self, limit: int = 50, status: Optional[str] = None) -> list[dict]:
        """List incidents, optionally filtered by status."""
        if status:
            cursor = await self.db.execute(
                "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def log_audit(
        self,
        incident_id: str,
        agent_name: str,
        command: str,
        output: str = "",
        status: str = "success",
    ):
        """Log a command execution to the audit trail."""
        await self.db.execute(
            """INSERT INTO audit_logs (incident_id, agent_name, command, output, status, executed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (incident_id, agent_name, command, output, status, datetime.now(UTC).isoformat()),
        )
        await self.db.commit()

    async def get_audit_logs(self, incident_id: str) -> list[dict]:
        """Get all audit log entries for an incident."""
        cursor = await self.db.execute(
            "SELECT * FROM audit_logs WHERE incident_id = ? ORDER BY executed_at ASC",
            (incident_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    def _row_to_dict(self, row) -> dict:
        """Convert a database row to a dictionary, parsing JSON fields."""
        d = dict(row)
        for json_field in ("agent_trace", "commands_executed"):
            if json_field in d and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    d[json_field] = []
        return d


# --- Singleton access ---
_db_instance: Optional[Database] = None


async def get_db() -> Database:
    """Get or create the database singleton."""
    global _db_instance
    db_path = os.getenv("DEVOPS_AI_DB_PATH", DB_PATH)
    if _db_instance is None or _db_instance.db_path != db_path or _db_instance.db is None:
        if _db_instance and _db_instance.db:
            await _db_instance.close()
        _db_instance = Database(db_path)
        await _db_instance.connect()
    return _db_instance


async def reset_db():
    """Close and clear the database singleton. Intended for tests and app shutdown."""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None