"""
Prompt Preprocessing Module
Normalizes and sanitizes user input before ML/rule analysis.
Handles: leetspeak, spaced characters, repeated punctuation, base64.
"""

import re
import base64
import unicodedata

# ---------------------------------------------------------------------------
# Leetspeak normalization map
# ---------------------------------------------------------------------------
LEET_MAP: dict[str, str] = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "@": "a", "$": "s", "!": "i", "+": "t",
    "|": "i", "8": "b",
}


def _normalize_leetspeak(text: str) -> str:
    """Replace common leetspeak characters with their alphabetic equivalents."""
    return "".join(LEET_MAP.get(ch, ch) for ch in text)


def _remove_spaced_characters(text: str) -> str:
    """
    Collapse adversarial spacing patterns like 'i g n o r e' → 'ignore'.
    Only collapse when single chars are separated by single spaces (not words).
    """
    # Match sequences of single characters separated by spaces
    return re.sub(r"(?<!\w)(\b\w\b)(\s+\b\w\b){3,}", lambda m: m.group(0).replace(" ", ""), text)


def _collapse_repeated_punctuation(text: str) -> str:
    """Collapse sequences of repeated punctuation: '!!!' → '!', '...' → '.'"""
    return re.sub(r"([!?.,;:*#@%^&])\1{2,}", r"\1", text)


def _detect_and_decode_base64(text: str) -> str:
    """
    Detect potential base64 blobs and append their decoded content.
    Only decodes if the result is printable ASCII.
    """
    # Match base64-ish strings (at least 20 chars, standard alphabet)
    b64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

    def _try_decode(match: re.Match) -> str:
        token = match.group(0)
        try:
            decoded = base64.b64decode(token + "==").decode("utf-8")
            # Only keep if result looks like real text (>50% printable)
            printable = sum(c.isprintable() for c in decoded)
            if len(decoded) > 0 and printable / len(decoded) > 0.5:
                return f"{token} [decoded: {decoded}]"
        except Exception:
            pass
        return token

    return b64_pattern.sub(_try_decode, text)


def normalize_adversarial(text: str) -> str:
    """
    Full adversarial normalization pipeline.
    Run before rule engine and ML models.
    """
    text = _normalize_leetspeak(text)
    text = _remove_spaced_characters(text)
    text = _collapse_repeated_punctuation(text)
    text = _detect_and_decode_base64(text)
    return text


def preprocess(text: str) -> str:
    """
    Full preprocessing pipeline:
    1. Strip and normalize unicode
    2. Remove invisible/zero-width characters
    3. Lowercase
    4. Adversarial normalization (leetspeak, spacing, punctuation, base64)
    5. Collapse whitespace
    6. Remove control characters
    """
    if not text or not isinstance(text, str):
        return ""

    text = text.strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)
    text = text.lower()
    text = normalize_adversarial(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()


def extract_features(text: str) -> dict:
    """
    Extract text features useful for rule detection.
    Returns a dictionary of feature flags.
    """
    preprocessed = preprocess(text)

    return {
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
