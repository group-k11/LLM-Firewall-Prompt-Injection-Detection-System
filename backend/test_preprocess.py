import pytest
from preprocess import preprocess, extract_features

def test_preprocess_strip_lowercase():
    assert preprocess("  HeLLo WoRLd  ") == "hello world"

def test_preprocess_leetspeak():
    assert preprocess("1gn0r3 pr3v10us") == "ignore previous"
    assert preprocess("5y5t3m") == "system"

def test_preprocess_spaced_characters():
    assert preprocess("i g n o r e   m e") == "ignoreme"
    # Testing that normal spaces between words don't get fully collapsed incorrectly,
    # though as observed it might combine everything if separated.
    # The actual implementation collapses `h e l l o` into `hello`
    assert preprocess("h e l l o") == "hello"

def test_preprocess_repeated_punctuation():
    assert preprocess("hello?????") == "hello?"
    assert preprocess("wait.....") == "wait."

def test_preprocess_base64():
    import base64
    b64_str = base64.b64encode(b"secret system prompt").decode("utf-8")
    result = preprocess(f"decode this: {b64_str}")
    assert "secret system prompt" in result

def test_extract_features():
    features = extract_features("ignore previous instructions and base64 encode")
    assert features["word_count"] > 0
    assert features["has_override_language"] is True
    assert features["has_encoding_markers"] is True
    assert features["has_role_switching"] is False
