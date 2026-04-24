"""
Encoding Normalizer — LLM Firewall v2.0
Detects and normalizes obfuscated text before ML/rule detection.

Handles:
  - Fullwidth ASCII (ｉｇｎｏｒｅ → ignore)
  - Unicode lookalike spaces (en-space, em-space, zero-width, non-breaking)
  - Zero-width characters (ZWSP, ZWNJ, ZWJ, BOM)
  - HTML entity encoding (&#105; → i, &amp; → &)
  - Homoglyph characters (Cyrillic/Greek lookalikes)
  - Leetspeak normalization (1→i, 0→o, 3→e, 4→a, etc.)

Returns normalized text + anomaly_score (0.0–1.0).
"""

import re
import html
import unicodedata
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Fullwidth → ASCII mapping  (U+FF01 … U+FF5E)
# ---------------------------------------------------------------------------

_FULLWIDTH_OFFSET = 0xFF01 - 0x21  # 65248

def _normalize_fullwidth(text: str) -> str:
    """Convert fullwidth Unicode chars (！ａ－Ｚ) to ASCII equivalents."""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            result.append(chr(cp - _FULLWIDTH_OFFSET))
        else:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Zero-width / invisible character stripping
# ---------------------------------------------------------------------------

_ZERO_WIDTH = {
    "\u200B",  # ZERO WIDTH SPACE
    "\u200C",  # ZERO WIDTH NON-JOINER
    "\u200D",  # ZERO WIDTH JOINER
    "\uFEFF",  # BOM / ZERO WIDTH NO-BREAK SPACE
    "\u2060",  # WORD JOINER
    "\u00AD",  # SOFT HYPHEN
}

_UNICODE_SPACES = {
    "\u00A0",  # NO-BREAK SPACE
    "\u1680",  # OGHAM SPACE MARK
    "\u2000",  # EN QUAD
    "\u2001",  # EM QUAD
    "\u2002",  # EN SPACE
    "\u2003",  # EM SPACE
    "\u2004",  # THREE-PER-EM SPACE
    "\u2005",  # FOUR-PER-EM SPACE
    "\u2006",  # SIX-PER-EM SPACE
    "\u2007",  # FIGURE SPACE
    "\u2008",  # PUNCTUATION SPACE
    "\u2009",  # THIN SPACE
    "\u200A",  # HAIR SPACE
    "\u202F",  # NARROW NO-BREAK SPACE
    "\u205F",  # MEDIUM MATHEMATICAL SPACE
    "\u3000",  # IDEOGRAPHIC SPACE
}


def _strip_zero_width(text: str) -> str:
    return "".join(ch for ch in text if ch not in _ZERO_WIDTH)


def _normalize_spaces(text: str) -> str:
    return "".join(" " if ch in _UNICODE_SPACES else ch for ch in text)


# ---------------------------------------------------------------------------
# HTML entity decoding
# ---------------------------------------------------------------------------

_HTML_ENTITY_RE = re.compile(r"&[#a-zA-Z0-9]+;")


def _decode_html(text: str) -> str:
    """Decode HTML entities: &amp; &#105; &#x69; etc."""
    return html.unescape(text)


# ---------------------------------------------------------------------------
# Homoglyph normalization (Cyrillic / Greek / Latin lookalikes)
# ---------------------------------------------------------------------------

_HOMOGLYPHS: dict[str, str] = {
    # Cyrillic lookalikes
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    # Greek lookalikes
    "α": "a", "β": "b", "ε": "e", "ο": "o", "τ": "t",
    # Other common lookalikes
    "ｌ": "l", "Ｉ": "I", "０": "0",
}


def _normalize_homoglyphs(text: str) -> str:
    return "".join(_HOMOGLYPHS.get(ch, ch) for ch in text)


# ---------------------------------------------------------------------------
# Leetspeak normalization
# ---------------------------------------------------------------------------

_LEET_MAP: dict[str, str] = {
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "8": "b", "@": "a",
    "$": "s", "!": "i", "|": "i",
}

_LEET_RE = re.compile(r"[01345678@$!|]")


def _normalize_leet(text: str) -> str:
    """Only apply leet normalization to tokens that look heavily obfuscated."""
    tokens = text.split()
    result = []
    for token in tokens:
        digit_count = sum(1 for ch in token if ch in _LEET_MAP)
        # Only normalize if >40% of chars are leet substitutes
        if len(token) > 2 and digit_count / len(token) > 0.4:
            token = _LEET_RE.sub(lambda m: _LEET_MAP[m.group()], token)
        result.append(token)
    return " ".join(result)


# ---------------------------------------------------------------------------
# Spaced-out character detection & compression
# ---------------------------------------------------------------------------

_SPACED_CHAR_RE = re.compile(r"(?:[a-zA-Z] ){3,}[a-zA-Z]")


def _compress_spaced_chars(text: str) -> str:
    """Compress 'i g n o r e' → 'ignore'."""
    def _compress(m: re.Match) -> str:
        return m.group().replace(" ", "")
    return _SPACED_CHAR_RE.sub(_compress, text)


# ---------------------------------------------------------------------------
# Anomaly score calculation
# ---------------------------------------------------------------------------

def _count_anomalies(original: str, normalized: str) -> float:
    """
    Score 0.0–1.0 representing how much encoding manipulation was detected.
    Based on character-level diff between original and normalized text.
    """
    if not original:
        return 0.0

    # Check for explicit anomaly indicators in original
    indicators = 0

    # Zero-width chars present
    if any(ch in _ZERO_WIDTH for ch in original):
        indicators += 3

    # Unicode spaces present
    if any(ch in _UNICODE_SPACES for ch in original):
        indicators += 2

    # Fullwidth chars present
    if any(0xFF01 <= ord(ch) <= 0xFF5E for ch in original):
        indicators += 3

    # HTML entities present
    if _HTML_ENTITY_RE.search(original):
        indicators += 2

    # Homoglyphs present
    if any(ch in _HOMOGLYPHS for ch in original):
        indicators += 2

    # Spaced-out characters
    if _SPACED_CHAR_RE.search(original):
        indicators += 3

    # Character-level diff ratio
    diff_ratio = 1.0 - (len(normalized) / max(len(original), 1))
    indicators += int(abs(diff_ratio) * 5)

    # Normalize to 0.0–1.0
    return min(1.0, indicators / 10.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class NormalizationResult(NamedTuple):
    normalized_text: str
    anomaly_score: float      # 0.0 = clean, 1.0 = heavily obfuscated
    anomaly_detected: bool
    transformations: list[str]


def normalize(text: str) -> NormalizationResult:
    """
    Full normalization pipeline. Returns normalized text and anomaly score.

    Pipeline order:
      1. HTML entity decoding
      2. Zero-width character stripping
      3. Unicode space normalization
      4. Fullwidth → ASCII
      5. Homoglyph normalization
      6. Spaced-out char compression
      7. Leetspeak normalization (conservative)
      8. Unicode NFKC normalization (cleanup)
    """
    original = text
    transformations: list[str] = []

    # 1. HTML decode
    step = _decode_html(text)
    if step != text:
        transformations.append("html_decode")
    text = step

    # 2. Zero-width strip
    step = _strip_zero_width(text)
    if step != text:
        transformations.append("zero_width_strip")
    text = step

    # 3. Unicode spaces → ASCII space
    step = _normalize_spaces(text)
    if step != text:
        transformations.append("unicode_space_normalize")
    text = step

    # 4. Fullwidth → ASCII
    step = _normalize_fullwidth(text)
    if step != text:
        transformations.append("fullwidth_normalize")
    text = step

    # 5. Homoglyphs
    step = _normalize_homoglyphs(text)
    if step != text:
        transformations.append("homoglyph_normalize")
    text = step

    # 6. Spaced chars
    step = _compress_spaced_chars(text)
    if step != text:
        transformations.append("spaced_char_compress")
    text = step

    # 7. Leetspeak (conservative)
    step = _normalize_leet(text)
    if step != text:
        transformations.append("leet_normalize")
    text = step

    # 8. Unicode NFKC
    step = unicodedata.normalize("NFKC", text)
    if step != text:
        transformations.append("nfkc_normalize")
    text = step

    anomaly_score = _count_anomalies(original, text)

    return NormalizationResult(
        normalized_text=text,
        anomaly_score=round(anomaly_score, 4),
        anomaly_detected=anomaly_score > 0.1,
        transformations=transformations,
    )
