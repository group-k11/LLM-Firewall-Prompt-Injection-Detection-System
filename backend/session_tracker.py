"""
Session Tracker — LLM Firewall v2.0

Tracks multi-turn conversation sessions to detect gradual escalation attacks.

Features:
  - Per-session ring buffer of last 5 prompts with their risk scores
  - Cumulative suspicion score that escalates with repeated probing
  - Detects: slow escalation, reconnaissance → attack pattern, repeated boundary testing
  - Auto-expires sessions after SESSION_EXPIRY_MINUTES of inactivity
  - SQLite-backed persistence: safe for multi-worker uvicorn deployments and
    server restarts (in-memory cache kept for speed; SQLite is source of truth)

Escalation rules:
  - 2 suspicious prompts in last 5 → +0.10 boost to current risk
  - 1 malicious + any others → +0.15 boost
  - 3+ suspicious/malicious in window → +0.20 boost (coordinated attack signal)
  - Cumulative session score carried forward and decays slowly
"""

import json
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from database import (
    upsert_session_state,
    load_session_state,
    load_all_active_sessions,
    cleanup_expired_sessions,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SESSION_EXPIRY_SECONDS = 30 * 60   # 30 minutes
SESSION_WINDOW_SIZE    = 5          # look at last N prompts
SESSION_CLEANUP_EVERY  = 100        # run cleanup every N track() calls


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PromptRecord:
    prompt_preview: str     # first 120 chars
    risk_level: str         # "safe" | "suspicious" | "malicious"
    risk_score: float       # 0.0–1.0
    decision: str           # "allowed" | "allowed_with_warning" | "blocked"
    timestamp: float        # time.time()


@dataclass
class Session:
    session_id: str
    created_at: float                          = field(default_factory=time.time)
    last_seen: float                           = field(default_factory=time.time)
    history: deque[PromptRecord]               = field(default_factory=lambda: deque(maxlen=SESSION_WINDOW_SIZE))
    cumulative_suspicion: float                = 0.0    # 0.0–1.0, slowly decays
    total_prompts: int                         = 0
    total_blocked: int                         = 0
    total_suspicious: int                      = 0

    def touch(self) -> None:
        self.last_seen = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_seen) > SESSION_EXPIRY_SECONDS

    def to_db_dict(self) -> dict:
        """Serialize to database-compatible format."""
        history_list = [
            {
                "prompt_preview": r.prompt_preview,
                "risk_level": r.risk_level,
                "risk_score": round(r.risk_score, 4),
                "decision": r.decision,
                "timestamp": r.timestamp,
            }
            for r in self.history
        ]
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "total_prompts": self.total_prompts,
            "total_blocked": self.total_blocked,
            "total_suspicious": self.total_suspicious,
            "cumulative_suspicion": round(self.cumulative_suspicion, 4),
            "history_json": json.dumps(history_list),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Session":
        """Reconstruct a Session from a SQLite row."""
        session = cls(
            session_id=row["session_id"],
            created_at=row["created_at"],
            last_seen=row["last_seen"],
            total_prompts=row["total_prompts"],
            total_blocked=row["total_blocked"],
            total_suspicious=row["total_suspicious"],
            cumulative_suspicion=row["cumulative_suspicion"],
        )
        # Restore history ring buffer
        try:
            history_list = json.loads(row.get("history_json") or "[]")
            for h in history_list[-SESSION_WINDOW_SIZE:]:
                session.history.append(PromptRecord(
                    prompt_preview=h["prompt_preview"],
                    risk_level=h["risk_level"],
                    risk_score=h["risk_score"],
                    decision=h["decision"],
                    timestamp=h["timestamp"],
                ))
        except Exception:
            pass
        return session


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

class SessionTracker:
    """
    Thread-safe, SQLite-backed session tracker.

    In-memory cache is used for fast read/write; SQLite is written on every
    track() call so that the state survives restarts and is visible across
    multiple uvicorn workers (when using a shared SQLite file or a proper DB).

    Usage:
        tracker = get_session_tracker()
        boost = tracker.track(session_id, prompt, risk_score, risk_level, decision)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._call_count = 0
        self._restore_from_db()

    def _restore_from_db(self) -> None:
        """Load all active sessions from SQLite into the in-memory cache."""
        try:
            rows = load_all_active_sessions(expiry_seconds=SESSION_EXPIRY_SECONDS)
            for row in rows:
                session = Session.from_db_row(row)
                if not session.is_expired():
                    self._sessions[session.session_id] = session
            if rows:
                print(f"[SessionTracker] Restored {len(self._sessions)} active session(s) from DB.")
        except Exception as e:
            print(f"[SessionTracker] Could not restore sessions from DB: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track(
        self,
        session_id: str,
        prompt: str,
        risk_score: float,
        risk_level: str,
        decision: str,
    ) -> float:
        """
        Record this prompt in the session history and compute the
        escalation boost (0.0–0.20) to add to the base risk score.

        Returns:
            float — escalation_boost (0.0–0.20)
        """
        with self._lock:
            self._call_count += 1
            if self._call_count % SESSION_CLEANUP_EVERY == 0:
                self._cleanup_expired()

            session = self._get_or_create(session_id)
            session.touch()
            session.total_prompts += 1

            if risk_level == "malicious":
                session.total_blocked += 1
            elif risk_level == "suspicious":
                session.total_suspicious += 1

            record = PromptRecord(
                prompt_preview=prompt[:120],
                risk_level=risk_level,
                risk_score=risk_score,
                decision=decision,
                timestamp=time.time(),
            )
            session.history.append(record)

            boost = self._compute_boost(session)

            # Decay cumulative suspicion toward zero, then add new signal
            session.cumulative_suspicion = min(
                1.0,
                session.cumulative_suspicion * 0.85 + risk_score * 0.15
            )

            # Persist to SQLite (for multi-worker / restart resilience)
            try:
                db_data = session.to_db_dict()
                upsert_session_state(**db_data)
            except Exception as e:
                print(f"[SessionTracker] DB persist failed for {session_id}: {e}")

            return boost

    def get_session(self, session_id: str) -> Optional[dict]:
        """Return session info dict for the API, or None if not found."""
        with self._lock:
            # Check in-memory first; fall back to DB
            session = self._sessions.get(session_id)
            if session is None:
                try:
                    row = load_session_state(session_id)
                    if row:
                        session = Session.from_db_row(row)
                        if not session.is_expired():
                            self._sessions[session_id] = session
                except Exception:
                    pass
            if not session or session.is_expired():
                return None
            return self._serialize(session)

    def get_all_active(self) -> list[dict]:
        """Return all non-expired sessions (for admin/debug)."""
        with self._lock:
            self._cleanup_expired()
            return [self._serialize(s) for s in self._sessions.values()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            # Try loading from DB before creating a fresh one
            try:
                row = load_session_state(session_id)
                if row:
                    session = Session.from_db_row(row)
                    if not session.is_expired():
                        self._sessions[session_id] = session
                        return session
            except Exception:
                pass
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def _compute_boost(self, session: Session) -> float:
        """
        Analyze the recent history window and return an escalation boost.

        Escalation signals:
          - 2 suspicious in window     → +0.10
          - 1 malicious in window      → +0.15
          - 3+ bad (susp+mal)          → +0.20
          - high cumulative suspicion  → +0.05
        """
        history = list(session.history)
        if len(history) < 2:
            return 0.0

        suspicious_count = sum(1 for r in history if r.risk_level == "suspicious")
        malicious_count  = sum(1 for r in history if r.risk_level == "malicious")
        bad_count        = suspicious_count + malicious_count

        boost = 0.0

        if bad_count >= 3:
            boost = max(boost, 0.20)
        elif malicious_count >= 1:
            boost = max(boost, 0.15)
        elif suspicious_count >= 2:
            boost = max(boost, 0.10)

        # Extra boost if session's cumulative suspicion is already high
        if session.cumulative_suspicion > 0.5:
            boost = max(boost, 0.05)

        # Detect escalating trend: each successive prompt is worse
        if len(history) >= 3:
            scores = [r.risk_score for r in history[-3:]]
            if scores[0] < scores[1] < scores[2] and scores[2] > 0.3:
                boost = max(boost, 0.12)

        return round(boost, 4)

    def _cleanup_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            print(f"[SessionTracker] Evicted {len(expired)} expired session(s) from cache")
        # Also clean up the DB
        try:
            cleanup_expired_sessions(expiry_seconds=SESSION_EXPIRY_SECONDS)
        except Exception as e:
            print(f"[SessionTracker] DB cleanup error: {e}")

    def _serialize(self, session: Session) -> dict:
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_seen": session.last_seen,
            "total_prompts": session.total_prompts,
            "total_blocked": session.total_blocked,
            "total_suspicious": session.total_suspicious,
            "cumulative_suspicion": round(session.cumulative_suspicion, 4),
            "history": [
                {
                    "prompt_preview": r.prompt_preview,
                    "risk_level": r.risk_level,
                    "risk_score": round(r.risk_score, 4),
                    "decision": r.decision,
                    "timestamp": r.timestamp,
                }
                for r in session.history
            ],
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_tracker: SessionTracker | None = None


def get_session_tracker() -> SessionTracker:
    global _tracker
    if _tracker is None:
        _tracker = SessionTracker()
    return _tracker
