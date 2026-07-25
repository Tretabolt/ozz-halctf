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
                target TEXT
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
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                domain TEXT,
                target TEXT,
                winner_name TEXT,
                debate_summary TEXT,
                rounds INTEGER,
                history_json TEXT
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
        """Store a structured finding."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO findings (timestamp, category, key, value, target) VALUES (?, ?, ?, ?, ?)",
            (time.time(), category, key, value, target)
        )
        conn.commit()
        conn.close()

    def store_flag(self, flag: str, source: str = "", target: str = ""):
        """Store a found flag with idempotency check (does not duplicate identical flags)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id FROM flags WHERE flag = ?", (flag,))
        if c.fetchone() is not None:
            conn.close()
            return  # Idempotent skip
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

    def store_tournament_result(self, domain: str, target: str, result):
        """Store a tournament result from TacticalHypothesisEngine."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO tournaments (timestamp, domain, target, winner_name, debate_summary, rounds, history_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                domain,
                target,
                getattr(result.winner, "name", str(result.winner)),
                result.debate_summary,
                result.rounds_executed,
                json.dumps(result.history),
            )
        )
        conn.commit()
        conn.close()

    def get_tournament_history(self, domain: str = "", limit: int = 10) -> list[dict]:
        """Retrieve tournament history."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        query = "SELECT domain, target, winner_name, debate_summary, rounds, timestamp FROM tournaments WHERE 1=1"
        params = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        c.execute(query, params)
        results = [
            {
                "domain": r[0],
                "target": r[1],
                "winner_name": r[2],
                "debate_summary": r[3],
                "rounds": r[4],
                "timestamp": r[5],
            }
            for r in c.fetchall()
        ]
        conn.close()
        return results

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
        for table in ["observations", "findings", "flags", "credentials", "tournaments"]:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = c.fetchone()[0]

        conn.close()
        return stats
