"""
Decision Engine
Combines rule-based detection and ML classification into a final risk assessment.
"""

from typing import Optional


# Risk level thresholds
SAFE_THRESHOLD = 0.3
SUSPICIOUS_THRESHOLD = 0.7


def compute_risk(rule_result: dict, ml_result: dict) -> dict:
    """
    Compute a composite risk score from rule engine and ML classifier outputs.

    The risk score is a weighted combination:
      - Rule engine weight: 0.5
      - ML classifier weight: 0.5
    If the rule engine detects a high-severity match, it can override the ML score.

    Args:
        rule_result: Output from rule_engine.check_rules()
        ml_result: Output from ml_detector.predict()

    Returns:
        dict with keys:
          - risk_score: float (0.0 - 1.0)
          - risk_level: str ("safe", "suspicious", "malicious")
          - decision: str ("allowed", "allowed_with_warning", "blocked")
          - reason: str (human-readable explanation)
          - details: dict (detailed breakdown)
    """
    rule_score = rule_result.get("rule_score", 0.0)
    ml_score = ml_result.get("ml_score", 0.5)
    ml_loaded = ml_result.get("prediction", -1) != -1

    # --- Compute composite risk score ---
    if ml_loaded:
        # Both engines active: weighted combination
        risk_score = (0.5 * rule_score) + (0.5 * ml_score)

        # If rule engine has high confidence match, boost the score
        if rule_result.get("matched") and rule_result.get("max_severity", 0) >= 0.9:
            risk_score = max(risk_score, 0.8)
    else:
        # ML not available: rely on rules + bump to neutral floor
        risk_score = rule_score if rule_result.get("matched") else 0.1

    # Clamp
    risk_score = max(0.0, min(1.0, risk_score))

    # --- Determine risk level ---
    if risk_score >= SUSPICIOUS_THRESHOLD:
        risk_level = "malicious"
        decision = "blocked"
    elif risk_score >= SAFE_THRESHOLD:
        risk_level = "suspicious"
        decision = "allowed_with_warning"
    else:
        risk_level = "safe"
        decision = "allowed"

    # --- Build reason string ---
    reasons = []

    if rule_result.get("matched"):
        top_matches = sorted(rule_result["matches"], key=lambda m: m["severity"], reverse=True)[:3]
        rule_reasons = [m["description"] for m in top_matches]
        reasons.append(f"Rule detection: {'; '.join(rule_reasons)}")

    if ml_loaded:
        ml_label = "malicious" if ml_result["prediction"] == 1 else "safe"
        reasons.append(f"ML classifier: {ml_label} (confidence: {ml_result['confidence']:.1%})")

    if not reasons:
        reasons.append("No threats detected")

    reason = " | ".join(reasons)

    return {
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level,
        "decision": decision,
        "reason": reason,
        "details": {
            "rule_score": round(rule_score, 4),
            "ml_score": round(ml_score, 4),
            "ml_loaded": ml_loaded,
            "rule_matched": rule_result.get("matched", False),
            "pattern_count": len(rule_result.get("matches", [])),
        },
    }
