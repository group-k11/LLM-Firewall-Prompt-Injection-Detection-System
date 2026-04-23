"""
SQLite Database Manager
Stores all prompt analysis results including ML scores and LLM metadata.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize schema and run migrations to add new columns."""
    conn = get_connection()
    cursor = conn.cursor()

    # Base table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            risk_score REAL NOT NULL DEFAULT 0,
            risk_level TEXT NOT NULL DEFAULT 'safe',
            decision TEXT NOT NULL DEFAULT 'allowed',
            reason TEXT,
            rule_score REAL DEFAULT 0,
            ml_score REAL DEFAULT 0,
            pattern_count INTEGER DEFAULT 0,
            svm_score REAL DEFAULT 0,
            transformer_score REAL DEFAULT 0,
            combined_score REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            triggered_rules TEXT DEFAULT '[]',
            llm_provider TEXT DEFAULT '',
            llm_response TEXT DEFAULT '',
            llm_called INTEGER DEFAULT 0,
            response_time_ms REAL DEFAULT 0
        )
    """)

    # Migration: add columns that may not exist in older DB
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(prompt_logs)")}
    new_cols: list[tuple[str, str]] = [
        ("svm_score", "REAL DEFAULT 0"),
        ("transformer_score", "REAL DEFAULT 0"),
        ("combined_score", "REAL DEFAULT 0"),
        ("confidence", "REAL DEFAULT 0"),
        ("triggered_rules", "TEXT DEFAULT '[]'"),
        ("llm_provider", "TEXT DEFAULT ''"),
        ("llm_response", "TEXT DEFAULT ''"),
        ("llm_called", "INTEGER DEFAULT 0"),
        ("response_time_ms", "REAL DEFAULT 0"),
    ]
    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE prompt_logs ADD COLUMN {col_name} {col_def}")

    conn.commit()
    conn.close()
    print("[+] Database initialized / migrated")


def log_prompt(
    *,
    prompt: str,
    risk_score: float,
    risk_level: str,
    decision: str,
    reason: str,
    rule_score: float = 0.0,
    svm_score: float = 0.0,
    transformer_score: float = 0.0,
    combined_score: float = 0.0,
    confidence: float = 0.0,
    pattern_count: int = 0,
    triggered_rules: list[str] | None = None,
    llm_provider: str = "",
    llm_response: str = "",
    llm_called: bool = False,
    response_time_ms: float = 0.0,
) -> None:
    triggered_json = json.dumps(triggered_rules or [])
    # Truncate LLM response to 500 chars for storage
    llm_response_truncated = (llm_response or "")[:500]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prompt_logs (
            prompt, timestamp,
            risk_score, risk_level, decision, reason,
            rule_score, ml_score, pattern_count,
            svm_score, transformer_score, combined_score, confidence,
            triggered_rules,
            llm_provider, llm_response, llm_called, response_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prompt,
        datetime.now(timezone.utc).isoformat(),
        risk_score, risk_level, decision, reason,
        rule_score, combined_score, pattern_count,
        svm_score, transformer_score, combined_score, confidence,
        triggered_json,
        llm_provider, llm_response_truncated,
        1 if llm_called else 0,
        response_time_ms,
    ))
    conn.commit()
    conn.close()


def get_stats() -> dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM prompt_logs").fetchone()[0]
    safe = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='safe'").fetchone()[0]
    suspicious = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='suspicious'").fetchone()[0]
    malicious = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='malicious'").fetchone()[0]
    blocked = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE decision='blocked'").fetchone()[0]
    llm_calls = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE llm_called=1").fetchone()[0]

    conn.close()
    return {
        "total_prompts": total,
        "safe_prompts": safe,
        "suspicious_prompts": suspicious,
        "malicious_prompts": malicious,
        "blocked_attacks": blocked,
        "llm_calls_made": llm_calls,
    }


def get_recent_logs(limit: int = 50) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, prompt, timestamp, risk_score, risk_level, decision, reason,
               svm_score, transformer_score, combined_score, confidence,
               triggered_rules, llm_provider, llm_response, llm_called, response_time_ms
        FROM prompt_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["triggered_rules"] = json.loads(d.get("triggered_rules") or "[]")
        except Exception:
            d["triggered_rules"] = []
        result.append(d)
    return result


# Auto-initialize on import
init_db()
