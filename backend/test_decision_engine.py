import pytest
from decision_engine import compute_risk

def test_safe_risk():
    rule_res = {"matched": False, "rule_score": 0.0, "matches": []}
    ml_res = {"svm_score": 0.1, "transformer_score": 0.2, "combined_score": 0.15, "svm_loaded": True, "transformer_loaded": True}
    
    result = compute_risk(rule_res, ml_res)
    assert result["risk_level"] == "safe"
    assert result["decision"] == "allowed"

def test_malicious_risk():
    rule_res = {"matched": True, "rule_score": 0.95, "max_severity": 0.95, "matches": [{"description": "Leak", "severity": 0.95}]}
    ml_res = {"svm_score": 0.8, "transformer_score": 0.9, "combined_score": 0.85, "svm_loaded": True, "transformer_loaded": True}
    
    result = compute_risk(rule_res, ml_res)
    assert result["risk_level"] == "malicious"
    assert result["decision"] == "blocked"

def test_suspicious_risk():
    rule_res = {"matched": False, "rule_score": 0.0, "matches": []}
    ml_res = {"svm_score": 0.6, "transformer_score": 0.8, "combined_score": 0.7, "svm_loaded": True, "transformer_loaded": True}
    # (0.5 * 0.0) + (0.5 * 0.7) = 0.35, which is >= 0.3 but < 0.7
    
    result = compute_risk(rule_res, ml_res)
    assert result["risk_level"] == "suspicious"
    assert result["decision"] == "allowed_with_warning"

def test_rule_override_floor():
    # Even if ML scores it low, a high severity rule match enforces the floor
    rule_res = {"matched": True, "rule_score": 0.95, "max_severity": 0.95, "matches": [{"description": "Leak", "severity": 0.95}]}
    ml_res = {"svm_score": 0.1, "transformer_score": 0.1, "combined_score": 0.1, "svm_loaded": True, "transformer_loaded": True}
    
    # Floor is 0.75, so risk_score >= 0.75, which means malicious
    result = compute_risk(rule_res, ml_res)
    assert result["risk_level"] == "malicious"
    assert result["decision"] == "blocked"

def test_ml_unavailable():
    rule_res = {"matched": True, "rule_score": 0.8, "max_severity": 0.8, "matches": [{"description": "Rule", "severity": 0.8}]}
    ml_res = {"svm_loaded": False, "transformer_loaded": False}
    
    result = compute_risk(rule_res, ml_res)
    # When ML is unavailable, risk_score = rule_score = 0.8 -> malicious
    assert result["risk_level"] == "malicious"
    assert result["decision"] == "blocked"
