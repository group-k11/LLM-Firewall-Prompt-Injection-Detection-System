"""
Decision Engine
Combines rule engine, SVM, and Transformer outputs into a final risk assessment.

Thresholds:
  combined_score < 0.3  → SAFE     → allow
  0.3 ≤ score < 0.7    → SUSPICIOUS → sanitize + allow with warning
  score ≥ 0.7          → MALICIOUS  → block
"""


SAFE_THRESHOLD = 0.3
MALICIOUS_THRESHOLD = 0.7

# Rule-engine override: if max rule severity ≥ this, floor the score
RULE_OVERRIDE_SEVERITY = 0.9
RULE_OVERRIDE_FLOOR = 0.75


def compute_risk(rule_result: dict, ml_result: dict) -> dict:
    """
    Compute composite risk from rule engine + hybrid ML (SVM + Transformer).

    Args:
        rule_result:  Output from rule_engine.check_rules()
        ml_result:    Output from ml_detector.HybridDetector.predict()

    Returns:
        dict with: risk_score, risk_level, decision, reason, details
    """
    rule_score: float = rule_result.get("rule_score", 0.0)
    svm_score: float = ml_result.get("svm_score", 0.5)
    transformer_score: float = ml_result.get("transformer_score", 0.5)
    combined_ml: float = ml_result.get("combined_score", 0.5)
    svm_loaded: bool = ml_result.get("svm_loaded", False)
    transformer_loaded: bool = ml_result.get("transformer_loaded", False)
    ml_available: bool = svm_loaded or transformer_loaded

    # --- Composite risk score ---
    if ml_available:
        # 50% rule engine, 50% hybrid ML
        risk_score = (0.5 * rule_score) + (0.5 * combined_ml)
    else:
        risk_score = rule_score if rule_result.get("matched") else 0.1

    # If a high-severity rule fires, enforce a minimum malicious floor
    if rule_result.get("matched") and rule_result.get("max_severity", 0) >= RULE_OVERRIDE_SEVERITY:
        risk_score = max(risk_score, RULE_OVERRIDE_FLOOR)

    # Clamp
    risk_score = max(0.0, min(1.0, risk_score))

    # --- Risk level and decision ---
    if risk_score >= MALICIOUS_THRESHOLD:
        risk_level = "malicious"
        decision = "blocked"
    elif risk_score >= SAFE_THRESHOLD:
        risk_level = "suspicious"
        decision = "allowed_with_warning"
    else:
        risk_level = "safe"
        decision = "allowed"

    # --- Human-readable reason ---
    reasons: list[str] = []

    if rule_result.get("matched"):
        top = sorted(rule_result["matches"], key=lambda m: m["severity"], reverse=True)[:3]
        reasons.append("Rule: " + "; ".join(m["description"] for m in top))

    if svm_loaded:
        lbl = "malicious" if svm_score >= 0.5 else "safe"
        reasons.append(f"SVM: {lbl} ({svm_score:.1%})")

    if transformer_loaded:
        lbl = "malicious" if transformer_score >= 0.5 else "safe"
        reasons.append(f"Transformer: {lbl} ({transformer_score:.1%})")

    if not reasons:
        reasons.append("No threats detected")

    # Triggered rule names (for blocked response schema)
    triggered_rules: list[str] = (
        [m["description"] for m in rule_result.get("matches", [])]
        if rule_result.get("matched")
        else []
    )

    return {
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level,
        "decision": decision,
        "reason": " | ".join(reasons),
        "triggered_rules": triggered_rules,
        "details": {
            "rule_score": round(rule_score, 4),
            "svm_score": round(svm_score, 4),
            "transformer_score": round(transformer_score, 4),
            "combined_ml_score": round(combined_ml, 4),
            "rule_matched": rule_result.get("matched", False),
            "pattern_count": len(rule_result.get("matches", [])),
            "svm_loaded": svm_loaded,
            "transformer_loaded": transformer_loaded,
        },
    }
