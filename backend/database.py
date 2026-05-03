"""
SQLite Database Manager — LLM Firewall v2.0

Schema:
  prompt_logs   — per-request telemetry
  sessions      — SQLite-backed session state (multi-worker safe)

Schema upgrades (prompt_logs):
  - session_id TEXT
  - normalized_prompt TEXT
  - attack_category TEXT
  - encoding_anomaly_score REAL
  - triggered_layers TEXT (JSON)
  - nested_score REAL

New query functions:
  - get_attack_trends()       — attack counts by category + time bucketed
  - get_session_logs()        — all logs for a session
  - upsert_session_state()    — persist session tracker state
  - load_session_state()      — reload session state on startup
  - cleanup_expired_sessions()— purge stale sessions
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Any

# Store the DB in a dedicated data/ subdirectory.
# This matches the Docker volume mount: backend_data:/app/backend/data
# so that only the database is persisted, not the source code.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "firewall.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize schema and run migrations to add v2.0 columns."""
    conn = get_connection()
    cursor = conn.cursor()

    # Base prompt_logs table (idempotent)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_logs (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt                TEXT NOT NULL,
            timestamp             TEXT NOT NULL,
            risk_score            REAL NOT NULL DEFAULT 0,
            risk_level            TEXT NOT NULL DEFAULT 'safe',
            decision              TEXT NOT NULL DEFAULT 'allowed',
            reason                TEXT,
            rule_score            REAL DEFAULT 0,
            ml_score              REAL DEFAULT 0,
            pattern_count         INTEGER DEFAULT 0,
            svm_score             REAL DEFAULT 0,
            transformer_score     REAL DEFAULT 0,
            combined_score        REAL DEFAULT 0,
            confidence            REAL DEFAULT 0,
            triggered_rules       TEXT DEFAULT '[]',
            llm_provider          TEXT DEFAULT '',
            llm_response          TEXT DEFAULT '',
            llm_called            INTEGER DEFAULT 0,
            response_time_ms      REAL DEFAULT 0,
            -- v2.0 columns --
            session_id            TEXT DEFAULT '',
            normalized_prompt     TEXT DEFAULT '',
            attack_category       TEXT DEFAULT 'none',
            encoding_anomaly_score REAL DEFAULT 0,
            triggered_layers      TEXT DEFAULT '[]',
            nested_score          REAL DEFAULT 0
        )
    """)

    # Migration: add v2.0 columns that may not exist in older DB
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(prompt_logs)")}
    new_cols: list[tuple[str, str]] = [
        # v1 columns (safe to re-run)
        ("svm_score",           "REAL DEFAULT 0"),
        ("transformer_score",   "REAL DEFAULT 0"),
        ("combined_score",      "REAL DEFAULT 0"),
        ("confidence",          "REAL DEFAULT 0"),
        ("triggered_rules",     "TEXT DEFAULT '[]'"),
        ("llm_provider",        "TEXT DEFAULT ''"),
        ("llm_response",        "TEXT DEFAULT ''"),
        ("llm_called",          "INTEGER DEFAULT 0"),
        ("response_time_ms",    "REAL DEFAULT 0"),
        # v2.0 columns
        ("session_id",              "TEXT DEFAULT ''"),
        ("normalized_prompt",       "TEXT DEFAULT ''"),
        ("attack_category",         "TEXT DEFAULT 'none'"),
        ("encoding_anomaly_score",  "REAL DEFAULT 0"),
        ("triggered_layers",        "TEXT DEFAULT '[]'"),
        ("nested_score",            "REAL DEFAULT 0"),
    ]
    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE prompt_logs ADD COLUMN {col_name} {col_def}")

    # Sessions table (SQLite-backed session tracker state)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id           TEXT PRIMARY KEY,
            created_at           REAL NOT NULL,
            last_seen            REAL NOT NULL,
            total_prompts        INTEGER DEFAULT 0,
            total_blocked        INTEGER DEFAULT 0,
            total_suspicious     INTEGER DEFAULT 0,
            cumulative_suspicion REAL DEFAULT 0,
            history_json         TEXT DEFAULT '[]'
        )
    """)

    # Index on session_id for fast session lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_id ON prompt_logs(session_id)
    """)
    # Index on timestamp for trend queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON prompt_logs(timestamp)
    """)

    conn.commit()
    conn.close()
    print("[+] Database initialized / migrated (v2.0)")


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

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
    # v2.0 fields
    session_id: str = "",
    normalized_prompt: str = "",
    attack_category: str = "none",
    encoding_anomaly_score: float = 0.0,
    triggered_layers: list[str] | None = None,
    nested_score: float = 0.0,
) -> None:
    triggered_json = json.dumps(triggered_rules or [])
    layers_json    = json.dumps(triggered_layers or [])
    llm_response_truncated = (llm_response or "")[:500]
    normalized_truncated   = (normalized_prompt or "")[:500]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prompt_logs (
            prompt, timestamp,
            risk_score, risk_level, decision, reason,
            rule_score, ml_score, pattern_count,
            svm_score, transformer_score, combined_score, confidence,
            triggered_rules,
            llm_provider, llm_response, llm_called, response_time_ms,
            session_id, normalized_prompt, attack_category,
            encoding_anomaly_score, triggered_layers, nested_score
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        prompt,
        datetime.now(timezone.utc).isoformat(),
        risk_score, risk_level, decision, reason,
        # BUG FIX: ml_score was incorrectly mapped to combined_score.
        # ml_score is now correctly set to svm_score (the primary ML signal)
        # while combined_score gets the actual hybrid combined score.
        rule_score, svm_score, pattern_count,
        svm_score, transformer_score, combined_score, confidence,
        triggered_json,
        llm_provider, llm_response_truncated,
        1 if llm_called else 0,
        response_time_ms,
        session_id, normalized_truncated, attack_category,
        encoding_anomaly_score, layers_json, nested_score,
    ))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Read — stats
# ---------------------------------------------------------------------------

def get_stats() -> dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    total       = cursor.execute("SELECT COUNT(*) FROM prompt_logs").fetchone()[0]
    safe        = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='safe'").fetchone()[0]
    suspicious  = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='suspicious'").fetchone()[0]
    malicious   = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE risk_level='malicious'").fetchone()[0]
    blocked     = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE decision='blocked'").fetchone()[0]
    llm_calls   = cursor.execute("SELECT COUNT(*) FROM prompt_logs WHERE llm_called=1").fetchone()[0]

    conn.close()
    return {
        "total_prompts":    total,
        "safe_prompts":     safe,
        "suspicious_prompts": suspicious,
        "malicious_prompts": malicious,
        "blocked_attacks":  blocked,
        "llm_calls_made":   llm_calls,
    }


# ---------------------------------------------------------------------------
# Read — recent logs
# ---------------------------------------------------------------------------

def get_recent_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, prompt, timestamp, risk_score, risk_level, decision, reason,
               svm_score, transformer_score, combined_score, confidence,
               triggered_rules, llm_provider, llm_response, llm_called,
               response_time_ms,
               session_id, attack_category, encoding_anomaly_score,
               triggered_layers, nested_score
        FROM prompt_logs
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        for json_col in ("triggered_rules", "triggered_layers"):
            try:
                d[json_col] = json.loads(d.get(json_col) or "[]")
            except Exception:
                d[json_col] = []
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Read — attack trends (v2.0)
# ---------------------------------------------------------------------------

def get_attack_trends(days: int = 7) -> dict[str, Any]:
    """
    Return attack category breakdown and daily threat counts.

    Returns:
        {
            "by_category": {"jailbreak": 5, "encoding_attack": 2, ...},
            "by_day": [{"date": "2025-04-20", "total": 10, "blocked": 3}, ...],
            "layer_hits": {"rule_engine": 15, "svm_classifier": 12, ...},
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Category breakdown (non-safe only)
    rows = cursor.execute("""
        SELECT attack_category, COUNT(*) as cnt
        FROM prompt_logs
        WHERE risk_level != 'safe'
          AND timestamp >= datetime('now', ? || ' days')
        GROUP BY attack_category
        ORDER BY cnt DESC
    """, (f"-{days}",)).fetchall()
    by_category = {r["attack_category"]: r["cnt"] for r in rows}

    # Daily totals + blocked counts
    daily_rows = cursor.execute("""
        SELECT
            substr(timestamp, 1, 10) as date,
            COUNT(*) as total,
            SUM(CASE WHEN decision='blocked' THEN 1 ELSE 0 END) as blocked,
            SUM(CASE WHEN risk_level='suspicious' THEN 1 ELSE 0 END) as suspicious,
            SUM(CASE WHEN risk_level='malicious' THEN 1 ELSE 0 END) as malicious
        FROM prompt_logs
        WHERE timestamp >= datetime('now', ? || ' days')
        GROUP BY date
        ORDER BY date ASC
    """, (f"-{days}",)).fetchall()
    by_day = [dict(r) for r in daily_rows]

    # Which detection layers are triggering most
    all_layers_rows = cursor.execute("""
        SELECT triggered_layers FROM prompt_logs
        WHERE risk_level != 'safe'
          AND timestamp >= datetime('now', ? || ' days')
    """, (f"-{days}",)).fetchall()

    layer_hits: dict[str, int] = {}
    for row in all_layers_rows:
        try:
            layers: list[str] = json.loads(row["triggered_layers"] or "[]")
            for layer in layers:
                layer_hits[layer] = layer_hits.get(layer, 0) + 1
        except Exception:
            pass

    conn.close()
    return {
        "by_category": by_category,
        "by_day":      by_day,
        "layer_hits":  layer_hits,
        "days":        days,
    }


# ---------------------------------------------------------------------------
# Read — session logs (v2.0)
# ---------------------------------------------------------------------------

def get_session_logs(session_id: str) -> list[dict]:
    """Return all logs for a specific session_id, oldest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, prompt, timestamp, risk_level, decision, reason,
               svm_score, transformer_score, combined_score,
               attack_category, encoding_anomaly_score, nested_score,
               triggered_layers, triggered_rules
        FROM prompt_logs
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        for json_col in ("triggered_rules", "triggered_layers"):
            try:
                d[json_col] = json.loads(d.get(json_col) or "[]")
            except Exception:
                d[json_col] = []
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Session persistence (v2.0 — SQLite-backed for multi-worker safety)
# ---------------------------------------------------------------------------

def upsert_session_state(
    session_id: str,
    created_at: float,
    last_seen: float,
    total_prompts: int,
    total_blocked: int,
    total_suspicious: int,
    cumulative_suspicion: float,
    history_json: str,
) -> None:
    """Insert or update a session row in SQLite."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO sessions (
            session_id, created_at, last_seen,
            total_prompts, total_blocked, total_suspicious,
            cumulative_suspicion, history_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            last_seen            = excluded.last_seen,
            total_prompts        = excluded.total_prompts,
            total_blocked        = excluded.total_blocked,
            total_suspicious     = excluded.total_suspicious,
            cumulative_suspicion = excluded.cumulative_suspicion,
            history_json         = excluded.history_json
    """, (
        session_id, created_at, last_seen,
        total_prompts, total_blocked, total_suspicious,
        cumulative_suspicion, history_json,
    ))
    conn.commit()
    conn.close()


def load_session_state(session_id: str) -> dict | None:
    """Load a session row from SQLite. Returns None if not found."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def load_all_active_sessions(expiry_seconds: int = 1800) -> list[dict]:
    """Load all sessions whose last_seen is within the expiry window."""
    import time as _time
    cutoff = _time.time() - expiry_seconds
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE last_seen >= ?", (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_expired_sessions(expiry_seconds: int = 1800) -> int:
    """Delete sessions older than expiry_seconds. Returns number deleted."""
    import time as _time
    cutoff = _time.time() - expiry_seconds
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM sessions WHERE last_seen < ?", (cutoff,)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted:
        print(f"[DB] Cleaned up {deleted} expired session(s)")
    return deleted


# ---------------------------------------------------------------------------
# Auto-initialize on import
# ---------------------------------------------------------------------------
init_db()
