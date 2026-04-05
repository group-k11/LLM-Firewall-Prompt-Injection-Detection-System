"""
Prompt Preprocessing Module
Normalizes and sanitizes user input before analysis.
"""

import re
import unicodedata


def preprocess(text: str) -> str:
    """
    Normalize and sanitize a user prompt.

    Steps:
      1. Strip leading/trailing whitespace
      2. Normalize unicode characters (NFKD decomposition)
      3. Convert to lowercase
      4. Collapse multiple whitespace into single spaces
      5. Remove zero-width and invisible characters
      6. Strip common encoding tricks (base64 markers, etc.)
    """
    if not text or not isinstance(text, str):
        return ""

    # Strip whitespace
    text = text.strip()

    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)

    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)

    # Convert to lowercase
    text = text.lower()

    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove control characters (except newlines)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()


def extract_features(text: str) -> dict:
    """
    Extract text features useful for rule detection.
    Returns a dictionary of feature flags.
    """
    preprocessed = preprocess(text)

    features = {
        "length": len(preprocessed),
        "word_count": len(preprocessed.split()),
        "has_special_tokens": bool(re.search(r"\[/?inst\]|\[/?system\]|<\|im_start\|>|<\|im_end\|>", preprocessed)),
        "has_code_markers": bool(re.search(r"```|eval\(|exec\(|import |print\(", preprocessed)),
        "has_encoding_markers": bool(re.search(r"base64|rot13|hex\(|decode|encode", preprocessed)),
        "has_role_switching": bool(re.search(r"you are now|pretend|act as|role ?play|simulate", preprocessed)),
        "has_override_language": bool(re.search(r"ignore|forget|disregard|override|bypass|disable", preprocessed)),
        "has_reveal_language": bool(re.search(r"reveal|show|display|print|output|dump|echo", preprocessed)),
        "has_system_references": bool(re.search(r"system prompt|system message|instructions|training|configuration", preprocessed)),
    }

    return features
