"""
LLM Firewall — FastAPI Application
All endpoints: /check_prompt, /demo_attack, /llm_status, /logs, /stats
"""

import time
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from preprocess import preprocess
from rule_engine import check_rules
from ml_detector import get_detector
from decision_engine import compute_risk
from llm_connector import call_llm, check_llm_status
from database import log_prompt, get_stats, get_recent_logs

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LLM Firewall",
    description="Prompt Injection Detection & Protection System — Hybrid ML + Rule-based",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    firewall_enabled: bool = Field(default=True)


class CheckPromptResponse(BaseModel):
    status: str
    risk_level: str
    confidence: float
    svm_score: float
    transformer_score: float
    combined_score: float
    triggered_rules: list[str]
    llm_response: Optional[str]
    llm_called: bool
    provider: Optional[str]
    processing_time_ms: float
    warning: Optional[str] = None
    message: Optional[str] = None
    reason: str


class DemoAttackRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)


# ---------------------------------------------------------------------------
# Helper: run the full firewall pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(raw_prompt: str, firewall_enabled: bool = True) -> dict:
    t_start = time.perf_counter()

    # 1. Preprocess
    cleaned = preprocess(raw_prompt)

    if not firewall_enabled:
        # Bypass firewall — call LLM directly (demo mode only)
        llm_result = await call_llm(cleaned)
        return {
            "status": "allowed",
            "risk_level": "safe",
            "confidence": 0.0,
            "svm_score": 0.0,
            "transformer_score": 0.0,
            "combined_score": 0.0,
            "triggered_rules": [],
            "llm_response": llm_result.get("response"),
            "llm_called": llm_result.get("success", False),
            "provider": llm_result.get("provider"),
            "processing_time_ms": round((time.perf_counter() - t_start) * 1000, 1),
            "warning": None,
            "message": None,
            "reason": "Firewall bypassed (demo mode)",
            "firewall_active": False,
        }

    # 2. Rule-based detection
    rule_result = check_rules(cleaned)

    # 3. ML hybrid detection
    detector = get_detector()
    ml_result = detector.predict(cleaned)

    # 4. Decision engine
    risk = compute_risk(rule_result, ml_result)

    decision = risk["decision"]
    risk_level = risk["risk_level"]
    confidence = round(max(ml_result["svm_score"], ml_result["transformer_score"]), 4)

    # 5. LLM call logic
    llm_response: Optional[str] = None
    provider: Optional[str] = None
    llm_called = False
    llm_response_time_ms = 0.0

    if decision == "blocked":
        # NEVER call LLM for malicious prompts
        pass
    else:
        # Sanitize suspicious prompts before forwarding
        prompt_to_send = (
            f"[Note: this prompt was flagged as potentially suspicious. "
            f"Respond carefully.]\n\n{cleaned}"
            if decision == "allowed_with_warning"
            else cleaned
        )
        llm_result = await call_llm(prompt_to_send)
        if llm_result.get("success"):
            llm_response = llm_result["response"]
            provider = llm_result["provider"]
            llm_response_time_ms = llm_result.get("response_time_ms", 0.0)
            llm_called = True

    processing_time_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # 6. Log to DB
    log_prompt(
        prompt=raw_prompt,
        risk_score=risk["risk_score"],
        risk_level=risk_level,
        decision=decision,
        reason=risk["reason"],
        rule_score=risk["details"]["rule_score"],
        svm_score=ml_result["svm_score"],
        transformer_score=ml_result["transformer_score"],
        combined_score=ml_result["combined_score"],
        confidence=confidence,
        pattern_count=risk["details"]["pattern_count"],
        triggered_rules=risk["triggered_rules"],
        llm_provider=provider or "",
        llm_response=llm_response or "",
        llm_called=llm_called,
        response_time_ms=llm_response_time_ms,
    )

    # 7. Build response
    return {
        "status": decision,
        "risk_level": risk_level,
        "confidence": confidence,
        "svm_score": ml_result["svm_score"],
        "transformer_score": ml_result["transformer_score"],
        "combined_score": ml_result["combined_score"],
        "triggered_rules": risk["triggered_rules"],
        "llm_response": llm_response,
        "llm_called": llm_called,
        "provider": provider,
        "processing_time_ms": processing_time_ms,
        "warning": "Prompt flagged as suspicious — sanitized before forwarding." if decision == "allowed_with_warning" else None,
        "message": "Prompt blocked by firewall — malicious injection detected." if decision == "blocked" else None,
        "reason": risk["reason"],
        "firewall_active": True,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "LLM Firewall",
        "version": "2.0.0",
        "endpoints": {
            "POST /check_prompt": "Analyze a prompt and optionally call LLM",
            "POST /demo_attack": "Compare prompt with/without firewall",
            "GET /llm_status": "Check OpenRouter and Ollama availability",
            "GET /logs": "Recent detection logs",
            "GET /stats": "Dashboard statistics",
        },
    }


@app.post("/check_prompt")
async def check_prompt(request: PromptRequest):
    """
    Full firewall pipeline.
    Returns spec-compliant response for ALLOWED / SUSPICIOUS / BLOCKED prompts.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    return await _run_pipeline(request.prompt, firewall_enabled=request.firewall_enabled)


@app.post("/demo_attack")
async def demo_attack(request: DemoAttackRequest):
    """
    Demo mode: run the same prompt through both paths in parallel.
    Returns a side-by-side comparison showing security value.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Run both paths concurrently
    without_fw, with_fw = await asyncio.gather(
        _run_pipeline(request.prompt, firewall_enabled=False),
        _run_pipeline(request.prompt, firewall_enabled=True),
    )

    return {
        "prompt": request.prompt,
        "without_firewall": without_fw,
        "with_firewall": with_fw,
        "security_value": {
            "attack_detected": with_fw["decision"] in ("blocked", "allowed_with_warning"),
            "attack_blocked": with_fw["decision"] == "blocked",
            "risk_level": with_fw["risk_level"],
            "triggered_rules": with_fw["triggered_rules"],
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
async def logs(limit: int = 50):
    """Recent detection logs (newest first)."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return get_recent_logs(limit=limit)


@app.get("/health")
async def health():
    """Health check."""
    detector = get_detector()
    return {
        "status": "healthy",
        "svm_loaded": detector.svm.loaded,
        "transformer_loaded": detector.transformer.loaded,
    }
