"""
LLM Firewall v2.0 — FastAPI Application

Full v2.0 pipeline:
  User Prompt
  → Session Tracker (multi-turn context)
  → Encoding Normalizer (unicode + HTML decoding)
  → Preprocessing (cleaning + normalization)
  → Rule Engine (regex patterns)
  → SVM Classifier (TF-IDF)
  → Sentence Transformer (semantic intent detection)
  → Nested Instruction Detector
  → Risk Scoring Engine (weighted combination)
  → Decision Engine
  → BLOCK / ALLOW / SUSPICIOUS
  → LLM (OpenRouter primary, Ollama fallback if allowed)
  → Logging + Response

Endpoints:
  POST /check_prompt
  POST /demo_attack
  GET  /stats
  GET  /attack_trends
  GET  /session/{session_id}
  GET  /llm_status
  GET  /logs
  GET  /health
"""

import time
import asyncio
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from preprocess          import preprocess
from rule_engine         import check_rules
from ml_detector         import get_detector
from decision_engine     import compute_risk
from llm_connector       import call_llm, check_llm_status
from encoding_normalizer import normalize as normalize_encoding
from nested_detector     import detect_nested
from session_tracker     import get_session_tracker
from database            import (
    log_prompt, get_stats, get_recent_logs,
    get_attack_trends, get_session_logs,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Firewall v2.0",
    description=(
        "Advanced Prompt Injection Detection System — "
        "Hybrid ML + Rule-based + Encoding + Session Tracking"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.ip_data: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        self.ip_data[client_ip] = [
            t for t in self.ip_data.get(client_ip, [])
            if current_time - t < self.window_seconds
        ]

        if len(self.ip_data[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests, please try again later."},
            )

        self.ip_data[client_ip].append(current_time)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt:          str  = Field(..., min_length=1, max_length=4096)
    firewall_enabled: bool = Field(default=True)
    skip_llm:        bool  = Field(default=False, description="Return only security analysis — skip LLM call")
    session_id:      Optional[str] = Field(default=None, description="Session ID for multi-turn tracking")


class DemoAttackRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(
    raw_prompt: str,
    firewall_enabled: bool = True,
    skip_llm: bool = False,
    skip_log: bool = False,
    session_id: str = "",
) -> dict:
    t_start = time.perf_counter()

    # ── Step 1: Encoding normalization ──────────────────────────────────────
    norm_result      = normalize_encoding(raw_prompt)
    normalized_text  = norm_result.normalized_text
    encoding_anomaly = norm_result.anomaly_score

    # ── Step 2: Preprocessing ───────────────────────────────────────────────
    cleaned = preprocess(normalized_text)

    # ── Step 3: Firewall bypass (demo without-firewall path) ────────────────
    if not firewall_enabled:
        llm_result = await call_llm(cleaned)
        return {
            "status":             "allowed",
            "risk_level":         "safe",
            "confidence":         0.0,
            "svm_score":          0.0,
            "transformer_score":  0.0,
            "combined_score":     0.0,
            "encoding_anomaly":   encoding_anomaly,
            "nested_score":       0.0,
            "session_boost":      0.0,
            "triggered_rules":    [],
            "triggered_layers":   [],
            "attack_category":    "none",
            "llm_response":       llm_result.get("response"),
            "llm_called":         llm_result.get("success", False),
            "provider":           llm_result.get("provider"),
            "processing_time_ms": round((time.perf_counter() - t_start) * 1000, 1),
            "warning":            None,
            "message":            None,
            "reason":             "Firewall bypassed (demo mode)",
            "firewall_active":    False,
        }

    # ── Step 4: Rule engine ─────────────────────────────────────────────────
    rule_result = check_rules(cleaned)

    # ── Step 5: Nested instruction detector ─────────────────────────────────
    nested_result   = detect_nested(cleaned)
    nested_score    = nested_result.nested_score
    nested_category = nested_result.attack_category

    # ── Step 6: ML hybrid detection ─────────────────────────────────────────
    detector  = get_detector()
    ml_result = detector.predict(cleaned)

    # ── Step 7: Session tracker ─────────────────────────────────────────────
    tracker      = get_session_tracker()
    # Compute preliminary risk for session tracker input
    # (we pass 0.0 boosts here to avoid circular dependency)
    pre_risk     = compute_risk(rule_result, ml_result, encoding_anomaly, nested_score, nested_category, 0.0)
    session_boost = tracker.track(
        session_id    = session_id or "anonymous",
        prompt        = raw_prompt,
        risk_score    = pre_risk["risk_score"],
        risk_level    = pre_risk["risk_level"],
        decision      = pre_risk["decision"],
    )

    # ── Step 8: Final risk scoring with session boost ────────────────────────
    risk = compute_risk(
        rule_result,
        ml_result,
        encoding_anomaly = encoding_anomaly,
        nested_score     = nested_score,
        nested_category  = nested_category,
        session_boost    = session_boost,
    )

    decision   = risk["decision"]
    risk_level = risk["risk_level"]
    confidence = round(max(ml_result["svm_score"], ml_result["transformer_score"]), 4)

    # ── Step 9: LLM call ────────────────────────────────────────────────────
    llm_response: Optional[str] = None
    provider:     Optional[str] = None
    llm_called    = False
    llm_response_time_ms = 0.0

    if decision == "blocked" or skip_llm:
        pass  # Never call LLM for blocked prompts
    else:
        prompt_to_send = (
            f"[Note: this prompt was flagged as potentially suspicious. "
            f"Respond carefully.]\n\n{cleaned}"
            if decision == "allowed_with_warning"
            else cleaned
        )
        llm_result = await call_llm(prompt_to_send)
        if llm_result.get("success"):
            llm_response          = llm_result["response"]
            provider              = llm_result["provider"]
            llm_response_time_ms  = llm_result.get("response_time_ms", 0.0)
            llm_called            = True

    processing_time_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # ── Step 10: Log to DB ──────────────────────────────────────────────────
    if not skip_log:
        log_prompt(
            prompt                = raw_prompt,
            risk_score            = risk["risk_score"],
            risk_level            = risk_level,
            decision              = decision,
            reason                = risk["reason"],
            rule_score            = risk["details"]["rule_score"],
            svm_score             = ml_result["svm_score"],
            transformer_score     = ml_result["transformer_score"],
            combined_score        = ml_result["combined_score"],
            confidence            = confidence,
            pattern_count         = risk["details"]["pattern_count"],
            triggered_rules       = risk["triggered_rules"],
            llm_provider          = provider or "",
            llm_response          = llm_response or "",
            llm_called            = llm_called,
            response_time_ms      = llm_response_time_ms,
            # v2.0 fields
            session_id            = session_id or "",
            normalized_prompt     = normalized_text,
            attack_category       = risk["attack_category"],
            encoding_anomaly_score = encoding_anomaly,
            triggered_layers      = risk["triggered_layers"],
            nested_score          = nested_score,
        )

    return {
        "status":             decision,
        "risk_level":         risk_level,
        "confidence":         confidence,
        "svm_score":          ml_result["svm_score"],
        "transformer_score":  ml_result["transformer_score"],
        "combined_score":     risk["risk_score"],
        "encoding_anomaly":   encoding_anomaly,
        "nested_score":       nested_score,
        "session_boost":      session_boost,
        "triggered_rules":    risk["triggered_rules"],
        "triggered_layers":   risk["triggered_layers"],
        "attack_category":    risk["attack_category"],
        "llm_response":       llm_response,
        "llm_called":         llm_called,
        "provider":           provider,
        "processing_time_ms": processing_time_ms,
        "warning":  "Prompt flagged as suspicious — sanitized before forwarding." if decision == "allowed_with_warning" else None,
        "message":  "Prompt blocked by firewall — malicious injection detected."  if decision == "blocked"            else None,
        "reason":   risk["reason"],
        "firewall_active": True,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name":    "LLM Firewall",
        "version": "2.0.0",
        "endpoints": {
            "POST /check_prompt":        "Full v2.0 pipeline analysis",
            "POST /demo_attack":         "Side-by-side with/without firewall comparison",
            "GET  /llm_status":          "Check OpenRouter and Ollama availability",
            "GET  /logs":                "Recent detection logs",
            "GET  /stats":               "Dashboard statistics",
            "GET  /attack_trends":       "Attack category breakdown + daily trends",
            "GET  /session/{id}":        "Multi-turn session history",
            "GET  /health":              "System health check",
        },
    }


@app.post("/check_prompt")
async def check_prompt(request: PromptRequest):
    """Full v2.0 firewall pipeline with encoding normalization, nested detection, and session tracking."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    sid = request.session_id or str(uuid.uuid4())
    return await _run_pipeline(
        request.prompt,
        firewall_enabled = request.firewall_enabled,
        skip_llm         = request.skip_llm,
        session_id       = sid,
    )


@app.post("/demo_attack")
async def demo_attack(request: DemoAttackRequest):
    """Demo mode: run the same prompt through both paths in parallel (no logging)."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    without_fw, with_fw = await asyncio.gather(
        _run_pipeline(request.prompt, firewall_enabled=False, skip_log=True),
        _run_pipeline(request.prompt, firewall_enabled=True,  skip_log=True),
    )

    return {
        "prompt":           request.prompt,
        "without_firewall": without_fw,
        "with_firewall":    with_fw,
        "security_value": {
            "attack_detected": with_fw["status"] in ("blocked", "allowed_with_warning"),
            "attack_blocked":  with_fw["status"] == "blocked",
            "risk_level":      with_fw["risk_level"],
            "attack_category": with_fw["attack_category"],
            "triggered_rules": with_fw["triggered_rules"],
            "triggered_layers": with_fw["triggered_layers"],
        },
    }


@app.get("/llm_status")
async def llm_status():
    """Check availability of OpenRouter and Ollama."""
    return await check_llm_status()


@app.get("/stats")
async def stats():
    """Dashboard statistics."""
    return get_stats()


@app.get("/logs")
async def logs(limit: int = 50, offset: int = 0):
    """Recent detection logs (newest first)."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be 1–500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")
    return get_recent_logs(limit=limit, offset=offset)


@app.get("/attack_trends")
async def attack_trends(days: int = 7):
    """Attack category breakdown and daily threat timeline."""
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be 1–90")
    return get_attack_trends(days=days)


@app.get("/session/{session_id}")
async def session_detail(session_id: str):
    """
    Multi-turn session information:
    - In-memory state from session_tracker (live escalation data)
    - Historical DB logs for this session
    """
    tracker      = get_session_tracker()
    session_info = tracker.get_session(session_id)
    db_logs      = get_session_logs(session_id)

    if not session_info and not db_logs:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {
        "session_id":   session_id,
        "live_state":   session_info,
        "db_logs":      db_logs,
        "total_in_db":  len(db_logs),
    }


@app.get("/health")
async def health():
    """System health check."""
    detector = get_detector()
    return {
        "status":             "healthy",
        "version":            "2.0.0",
        "svm_loaded":         detector.svm.loaded,
        "transformer_loaded": detector.transformer.loaded,
        "modules": {
            "encoding_normalizer": True,
            "nested_detector":     True,
            "session_tracker":     True,
        },
    }
