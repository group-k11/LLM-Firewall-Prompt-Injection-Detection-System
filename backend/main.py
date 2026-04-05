"""
LLM Firewall - FastAPI Application
Main entry point for the Prompt Injection Detection System.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from preprocess import preprocess
from rule_engine import check_rules
from ml_detector import get_detector
from decision_engine import compute_risk
from database import log_prompt, get_stats, get_recent_logs

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LLM Firewall",
    description="Prompt Injection Detection System - Analyzes prompts for injection attacks, jailbreaks, and malicious instructions.",
    version="1.0.0",
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    status: str          # "allowed" | "allowed_with_warning" | "blocked"
    risk_level: str      # "safe" | "suspicious" | "malicious"
    risk_score: float    # 0.0 - 1.0
    reason: str          # Human-readable explanation
    details: Optional[dict] = None


class StatsResponse(BaseModel):
    total_prompts: int
    safe_prompts: int
    suspicious_prompts: int
    malicious_prompts: int
    blocked_attacks: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "name": "LLM Firewall",
        "version": "1.0.0",
        "description": "Prompt Injection Detection System",
        "endpoints": {
            "POST /check_prompt": "Analyze a prompt for injection attacks",
            "GET /stats": "Get dashboard statistics",
            "GET /logs": "Get recent detection logs",
        },
    }


@app.post("/check_prompt", response_model=PromptResponse)
async def check_prompt(request: PromptRequest):
    """
    Analyze a prompt for prompt injection attacks.

    Pipeline:
      1. Preprocess the text
      2. Run rule-based detection
      3. Run ML classification
      4. Compute composite risk score
      5. Make allow/block decision
      6. Log the result
    """
    raw_prompt = request.prompt

    if not raw_prompt or not raw_prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # 1. Preprocess
    cleaned = preprocess(raw_prompt)

    # 2. Rule-based detection
    rule_result = check_rules(cleaned)

    # 3. ML classification
    detector = get_detector()
    ml_result = detector.predict(cleaned)

    # 4. Compute risk
    risk = compute_risk(rule_result, ml_result)

    # 5. Log to database
    log_prompt(
        prompt=raw_prompt,
        risk_score=risk["risk_score"],
        risk_level=risk["risk_level"],
        decision=risk["decision"],
        reason=risk["reason"],
        rule_score=risk["details"]["rule_score"],
        ml_score=risk["details"]["ml_score"],
        pattern_count=risk["details"]["pattern_count"],
    )

    # 6. Return response
    return PromptResponse(
        status=risk["decision"],
        risk_level=risk["risk_level"],
        risk_score=risk["risk_score"],
        reason=risk["reason"],
        details=risk["details"],
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Get dashboard statistics."""
    return get_stats()


@app.get("/logs")
async def logs(limit: int = 50):
    """Get recent detection logs."""
    return get_recent_logs(limit=limit)


@app.get("/health")
async def health():
    """Health check endpoint."""
    detector = get_detector()
    return {
        "status": "healthy",
        "ml_model_loaded": detector.loaded,
    }
