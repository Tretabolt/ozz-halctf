"""
Ozz — Memory Module
SQLite-based working memory for the agent.
"""

import json
import sqlite3
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ozz.memory")

DB_PATH = "/tmp/ozz_memory.db"


class Memory:
    """SQLite-based agent memory."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                tool TEXT,
                command TEXT,
                output TEXT,
                success BOOLEAN,
                target TEXT,
                phase TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                category TEXT,
                key TEXT,
                value TEXT,
                target TEXT,
                canonical_hash TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                flag TEXT,
                source TEXT,
                target TEXT,
                submitted BOOLEAN DEFAULT FALSE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                username TEXT,
                password TEXT,
                hash_value TEXT,
                service TEXT,
                target TEXT,
                source TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS run_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                run_id TEXT,
                metrics_json TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS strategy_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                target TEXT,
                service TEXT,
                vulnerability TEXT,
                action TEXT,
                reference TEXT,
                confidence REAL,
                outcome TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Memory initialized at {self.db_path}")

    def store(self, observation):
        """Store an observation."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO observations (timestamp, tool, command, output, success) VALUES (?, ?, ?, ?, ?)",
            (observation.timestamp, observation.tool, observation.command,
             observation.output, observation.success)
        )
        conn.commit()
        conn.close()

    def store_finding(self, category: str, key: str, value: str, target: str = ""):
        """Store a structured finding with canonical SHA-256 hash (tau(t))."""
        import hashlib
        canonical_str = f"{target}:{category}:{key}:{value}".lower()
        canonical_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO findings (timestamp, category, key, value, target, canonical_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), category, key, value, target, canonical_hash)
        )
        conn.commit()
        conn.close()

    def store_flag(self, flag: str, source: str = "", target: str = ""):
        """Store a found flag."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO flags (timestamp, flag, source, target) VALUES (?, ?, ?, ?)",
            (time.time(), flag, source, target)
        )
        conn.commit()
        conn.close()
        logger.info(f"🚩 Flag stored: {flag}")

    def store_credential(self, username: str, password: str = "", hash_value: str = "",
                        service: str = "", target: str = "", source: str = ""):
        """Store discovered credentials."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO credentials (timestamp, username, password, hash_value, service, target, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), username, password, hash_value, service, target, source)
        )
        conn.commit()
        conn.close()

    def get_findings(self, target: str = "", category: str = "") -> list[dict]:
        """Retrieve findings."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        query = "SELECT category, key, value, target FROM findings WHERE 1=1"
        params = []
        if target:
            query += " AND target = ?"
            params.append(target)
        if category:
            query += " AND category = ?"
            params.append(category)

        c.execute(query, params)
        results = [{"category": r[0], "key": r[1], "value": r[2], "target": r[3]} for r in c.fetchall()]
        conn.close()
        return results

    def get_flags(self) -> list[dict]:
        """Retrieve all flags."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT flag, source, target, submitted FROM flags")
        results = [{"flag": r[0], "source": r[1], "target": r[2], "submitted": r[3]} for r in c.fetchall()]
        conn.close()
        return results

    def store_run_metrics(self, metrics: dict, run_id: str = ""):
        """Persist a summarized snapshot of agent execution metrics."""
        payload = dict(metrics)
        payload.setdefault("run_id", run_id or f"run-{int(time.time())}")
        payload.setdefault("timestamp", time.time())

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO run_metrics (timestamp, run_id, metrics_json) VALUES (?, ?, ?)",
            (payload["timestamp"], payload["run_id"], json.dumps(payload))
        )
        conn.commit()
        conn.close()

    def get_run_metrics(self, run_id: str = "") -> dict:
        """Retrieve the latest run metrics, or a specific run if provided."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if run_id:
            c.execute("SELECT run_id, metrics_json FROM run_metrics WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,))
        else:
            c.execute("SELECT run_id, metrics_json FROM run_metrics ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if not row:
            return {}
        return {"run_id": row[0], **json.loads(row[1])}

    def get_run_metrics_history(self) -> list[dict]:
        """Retrieve all persisted run metrics in chronological order."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT run_id, metrics_json FROM run_metrics ORDER BY id ASC")
        rows = c.fetchall()
        conn.close()
        return [{"run_id": run_id, **json.loads(metrics_json)} for run_id, metrics_json in rows]

    def store_strategy_evidence(self, target: str, service: str, vulnerability: str, action: str,
                                reference: str = "", confidence: float = 0.0,
                                outcome: str = "unknown"):
        """Persist a strategy recommendation tied to service/vulnerability context."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO strategy_evidence (timestamp, target, service, vulnerability, action, reference, confidence, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), target, service, vulnerability, action, reference, confidence, outcome)
        )
        conn.commit()
        conn.close()

    def get_strategy_evidence(self, target: str = "") -> list[dict]:
        """Retrieve strategy evidence entries, optionally filtered by target."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        query = "SELECT target, service, vulnerability, action, reference, confidence, outcome FROM strategy_evidence WHERE 1=1"
        params = []
        if target:
            query += " AND target = ?"
            params.append(target)
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [{
            "target": row[0],
            "service": row[1],
            "vulnerability": row[2],
            "action": row[3],
            "reference": row[4],
            "confidence": row[5],
            "outcome": row[6],
        } for row in rows]

    def get_credentials(self, target: str = "") -> list[dict]:
        """Retrieve credentials."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        query = "SELECT username, password, hash_value, service, target FROM credentials WHERE 1=1"
        params = []
        if target:
            query += " AND target = ?"
            params.append(target)

        c.execute(query, params)
        results = [{"username": r[0], "password": r[1], "hash": r[2], "service": r[3], "target": r[4]}
                   for r in c.fetchall()]
        conn.close()
        return results

    def get_recent_observations(self, limit: int = 10) -> list[dict]:
        """Get recent observations."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT tool, command, output, success, timestamp FROM observations ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        results = [{"tool": r[0], "command": r[1], "output": r[2], "success": r[3], "timestamp": r[4]}
                   for r in c.fetchall()]
        conn.close()
        return results

    def get_stats(self) -> dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        stats = {}
        for table in ["observations", "findings", "flags", "credentials", "run_metrics"]:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = c.fetchone()[0]

        conn.close()
        return stats
