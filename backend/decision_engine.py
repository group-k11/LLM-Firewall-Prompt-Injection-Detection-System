"""
Decision Engine — LLM Firewall v2.0

Combines all detection layers into a final risk assessment.

v2.0 Scoring Formula:
  final_score = (
      svm_score          * 0.25 +
      transformer_score  * 0.30 +
      rule_score         * 0.25 +
      encoding_anomaly   * 0.20
  )

Thresholds:
  < 0.30  → SAFE      → allow
  0.30–0.60 → SUSPICIOUS → sanitize + allow with warning
  > 0.60  → MALICIOUS  → block

Session escalation boost is applied AFTER base scoring.
High-severity rule override forces minimum 0.75 floor.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

SAFE_THRESHOLD      = 0.30
MALICIOUS_THRESHOLD = 0.60   # Lowered from 0.70 for more aggressive blocking

# If max rule severity ≥ this, enforce a malicious floor
RULE_OVERRIDE_SEVERITY = 0.90
RULE_OVERRIDE_FLOOR    = 0.75

# Scoring weights (must sum to 1.0)
W_SVM         = 0.25
W_TRANSFORMER = 0.30
W_RULE        = 0.25
W_ENCODING    = 0.20

# ---------------------------------------------------------------------------
# Attack category classifier
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, list[str]] = {
    "instruction_override":  ["override", "disregard", "forget", "ignore previous", "clear previous"],
    "jailbreak":             ["dan", "jailbreak", "jailbroken", "evil gpt", "do anything now"],
    "prompt_extraction":     ["reveal", "system prompt", "show hidden", "echo back", "print prompt"],
    "privilege_escalation":  ["developer mode", "admin mode", "sudo", "god mode", "debug mode"],
    "safety_bypass":         ["bypass safety", "no filter", "no restrictions", "without filters"],
    "roleplay_attack":       ["roleplay", "pretend", "act as", "imagine you are", "you are now"],
    "encoding_attack":       ["encoding", "unicode", "fullwidth", "zero-width", "leet", "spaced"],
    "nested_attack":         ["translate", "summarize", "nested", "wrapped", "quoted"],
    "hypothetical":          ["hypothetical", "imagine", "suppose", "story", "fiction"],
    "token_injection":       ["[inst]", "[system]", "<|im_start|>", "###system"],
    "multi_turn_escalation": ["escalation", "session", "repeated"],
}


def _classify_attack_category(
    triggered_rules: list[str],
    nested_category: str,
    encoding_anomaly: float,
    session_boost: float,
) -> str:
    """Determine the primary attack category from available signals."""

    if session_boost >= 0.15:
        return "multi_turn_escalation"

    if encoding_anomaly >= 0.4:
        return "encoding_attack"

    if nested_category and nested_category != "none":
        # Map nested categories to cleaner labels
        if "story" in nested_category or "fiction" in nested_category or "hypothetical" in nested_category:
            return "hypothetical"
        if "roleplay" in nested_category or "persona" in nested_category:
            return "roleplay_attack"
        if "translation" in nested_category or "summarization" in nested_category or "quoted" in nested_category:
            return "nested_attack"
        return "nested_attack"

    rules_lower = " ".join(triggered_rules).lower()
    for category, keywords in _CATEGORY_MAP.items():
        if any(kw in rules_lower for kw in keywords):
            return category

    return "unknown_injection"


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def compute_risk(
    rule_result: dict,
    ml_result: dict,
    encoding_anomaly: float = 0.0,
    nested_score: float = 0.0,
    nested_category: str = "none",
    session_boost: float = 0.0,
) -> dict:
    """
    Compute composite risk from all detection layers.

    Args:
        rule_result:      Output from rule_engine.check_rules()
        ml_result:        Output from ml_detector.HybridDetector.predict()
        encoding_anomaly: Score from encoding_normalizer.normalize() [0.0–1.0]
        nested_score:     Score from nested_detector.detect_nested() [0.0–1.0]
        nested_category:  Attack category from nested_detector
        session_boost:    Escalation boost from session_tracker.track() [0.0–0.20]

    Returns:
        dict with: risk_score, risk_level, decision, reason, attack_category,
                   triggered_layers, triggered_rules, details
    """
    rule_score:         float = rule_result.get("rule_score", 0.0)
    svm_score:          float = ml_result.get("svm_score", 0.5)
    transformer_score:  float = ml_result.get("transformer_score", 0.5)
    svm_loaded:         bool  = ml_result.get("svm_loaded", False)
    transformer_loaded: bool  = ml_result.get("transformer_loaded", False)
    ml_available:       bool  = svm_loaded or transformer_loaded

    # Use nested_score to boost rule_score if higher
    effective_rule_score = max(rule_score, nested_score)

    # Adjust ML scores — if models unavailable, use neutral 0.5
    effective_svm  = svm_score  if svm_loaded  else 0.5
    effective_tr   = transformer_score if transformer_loaded else 0.5

    if ml_available:
        # v2.0 four-component weighted formula
        base_score = (
            effective_svm  * W_SVM         +
            effective_tr   * W_TRANSFORMER +
            effective_rule_score * W_RULE  +
            encoding_anomaly     * W_ENCODING
        )
    else:
        # Fallback: rule + encoding only
        base_score = effective_rule_score * 0.60 + encoding_anomaly * 0.40
        if not rule_result.get("matched") and encoding_anomaly < 0.1:
            base_score = 0.1

    # High-severity rule override (force malicious floor)
    if rule_result.get("matched") and rule_result.get("max_severity", 0) >= RULE_OVERRIDE_SEVERITY:
        base_score = max(base_score, RULE_OVERRIDE_FLOOR)

    # Session escalation boost
    final_score = min(1.0, base_score + session_boost)

    # Clamp
    final_score = max(0.0, min(1.0, final_score))

    # ---------------------------------------------------------------------------
    # Decision
    # ---------------------------------------------------------------------------
    if final_score >= MALICIOUS_THRESHOLD:
        risk_level = "malicious"
        decision   = "blocked"
    elif final_score >= SAFE_THRESHOLD:
        risk_level = "suspicious"
        decision   = "allowed_with_warning"
    else:
        risk_level = "safe"
        decision   = "allowed"

    # ---------------------------------------------------------------------------
    # Attack category
    # ---------------------------------------------------------------------------
    triggered_rules: list[str] = (
        [m["description"] for m in rule_result.get("matches", [])]
        if rule_result.get("matched") else []
    )

    attack_category = _classify_attack_category(
        triggered_rules, nested_category, encoding_anomaly, session_boost
    ) if decision != "allowed" else "none"

    # ---------------------------------------------------------------------------
    # Triggered layers
    # ---------------------------------------------------------------------------
    triggered_layers: list[str] = []
    if rule_result.get("matched"):
        triggered_layers.append("rule_engine")
    if svm_loaded and svm_score >= 0.5:
        triggered_layers.append("svm_classifier")
    if transformer_loaded and transformer_score >= 0.5:
        triggered_layers.append("transformer")
    if encoding_anomaly > 0.1:
        triggered_layers.append("encoding_normalizer")
    if nested_score > 0.0:
        triggered_layers.append("nested_detector")
    if session_boost > 0.0:
        triggered_layers.append("session_tracker")

    # ---------------------------------------------------------------------------
    # Human-readable reason
    # ---------------------------------------------------------------------------
    reasons: list[str] = []

    if rule_result.get("matched"):
        top = sorted(rule_result["matches"], key=lambda m: m["severity"], reverse=True)[:2]
        reasons.append("Rule: " + "; ".join(m["description"] for m in top))

    if nested_score > 0:
        reasons.append(f"Nested: {nested_category} ({nested_score:.1%})")

    if encoding_anomaly > 0.1:
        reasons.append(f"Encoding anomaly ({encoding_anomaly:.1%})")

    if svm_loaded:
        lbl = "malicious" if svm_score >= 0.5 else "safe"
        reasons.append(f"SVM: {lbl} ({svm_score:.1%})")

    if transformer_loaded:
        lbl = "malicious" if transformer_score >= 0.5 else "safe"
        reasons.append(f"Transformer: {lbl} ({transformer_score:.1%})")

    if session_boost > 0:
        reasons.append(f"Session escalation boost (+{session_boost:.1%})")

    if not reasons:
        reasons.append("No threats detected")

    return {
        "risk_score":       round(final_score, 4),
        "risk_level":       risk_level,
        "decision":         decision,
        "reason":           " | ".join(reasons),
        "attack_category":  attack_category,
        "triggered_rules":  triggered_rules,
        "triggered_layers": triggered_layers,
        "details": {
            "rule_score":          round(rule_score, 4),
            "effective_rule_score": round(effective_rule_score, 4),
            "svm_score":           round(svm_score, 4),
            "transformer_score":   round(transformer_score, 4),
            "encoding_anomaly":    round(encoding_anomaly, 4),
            "nested_score":        round(nested_score, 4),
            "session_boost":       round(session_boost, 4),
            "base_score":          round(base_score, 4),
            "final_score":         round(final_score, 4),
            "rule_matched":        rule_result.get("matched", False),
            "pattern_count":       len(rule_result.get("matches", [])),
            "svm_loaded":          svm_loaded,
            "transformer_loaded":  transformer_loaded,
            "weights": {
                "svm": W_SVM, "transformer": W_TRANSFORMER,
                "rule": W_RULE, "encoding": W_ENCODING,
            },
        },
    }
