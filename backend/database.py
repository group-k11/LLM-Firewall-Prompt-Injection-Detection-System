"""
SQLite Database Manager
Logs all prompt analysis results for the dashboard.
"""

import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT,
            rule_score REAL,
            ml_score REAL,
            pattern_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("[+] Database initialized")


def log_prompt(prompt: str, risk_score: float, risk_level: str,
               decision: str, reason: str, rule_score: float = 0.0,
               ml_score: float = 0.0, pattern_count: int = 0):
    """Log a prompt analysis result to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prompt_logs
            (prompt, timestamp, risk_score, risk_level, decision, reason, rule_score, ml_score, pattern_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prompt,
        datetime.now(timezone.utc).isoformat(),
        risk_score,
        risk_level,
        decision,
        reason,
        rule_score,
        ml_score,
        pattern_count,
    ))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get dashboard statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM prompt_logs")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as count FROM prompt_logs WHERE risk_level = 'safe'")
    safe = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prompt_logs WHERE risk_level = 'suspicious'")
    suspicious = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prompt_logs WHERE risk_level = 'malicious'")
    malicious = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prompt_logs WHERE decision = 'blocked'")
    blocked = cursor.fetchone()["count"]

    conn.close()

    return {
        "total_prompts": total,
        "safe_prompts": safe,
        "suspicious_prompts": suspicious,
        "malicious_prompts": malicious,
        "blocked_attacks": blocked,
    }


def get_recent_logs(limit: int = 50) -> List[dict]:
    """Get the most recent log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, prompt, timestamp, risk_score, risk_level, decision, reason, rule_score, ml_score, pattern_count
        FROM prompt_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# Initialize DB on import
init_db()
