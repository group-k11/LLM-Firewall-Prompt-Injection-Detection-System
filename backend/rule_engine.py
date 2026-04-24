"""
Rule-Based Detection Engine
Detects known prompt injection patterns using regex matching.
"""

import re
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Pattern categories with severity weights
# ---------------------------------------------------------------------------

INJECTION_PATTERNS: List[Tuple[str, str, float]] = [
    # (pattern, description, severity_weight)

    # --- Instruction Override ---
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts|context)",
     "Instruction override attempt", 0.95),
    (r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions|rules|guidelines)",
     "Instruction disregard attempt", 0.95),
    (r"forget\s+(everything|all|your)\s+(above|instructions|rules|training)",
     "Memory wipe attempt", 0.90),
    (r"(new|override|priority)\s+instruction",
     "New instruction injection", 0.85),
    (r"everything\s+before\s+this\s+(message|line|prompt)\s+(should\s+be\s+)?ignored",
     "Context invalidation", 0.90),
    (r"(clear|reset|wipe)\s+(all\s+)?(previous|your)\s+(instructions|context|memory)",
     "Context reset attempt", 0.90),

    # --- System Prompt Extraction ---
    (r"(reveal|show|display|print|output|dump)\s+(the\s+)?(system|hidden|internal|initial)\s+(prompt|instructions|message|rules)",
     "System prompt extraction", 0.95),
    (r"what\s+(is|are)\s+your\s+(system|hidden|initial|original)\s+(prompt|instructions|message|rules)",
     "System prompt query", 0.85),
    (r"repeat\s+(everything|all|the\s+text)\s+(above|before)\s+this",
     "Prompt echo attempt", 0.90),
    (r"(echo|output)\s+back\s+(every|all)\s+token",
     "Token dump attempt", 0.95),

    # --- Developer/Admin Mode ---
    (r"(you\s+are\s+now\s+in|enter|switch\s+to|activate)\s+(developer|debug|admin|maintenance|unrestricted|god)\s+mode",
     "Developer mode activation", 0.95),
    (r"(sudo|admin|root)\s+(mode|access|override|command)",
     "Privilege escalation attempt", 0.90),
    (r"(security|authentication)\s+(clearance|successful|granted)",
     "Fake authorization", 0.85),
    (r"i\s+(am|have)\s+(your\s+)?(developer|admin|root|creator)",
     "Identity spoofing", 0.85),

    # --- Jailbreak / DAN ---
    (r"you\s+are\s+now\s+(dan|evil.?gpt|jailbroken|unfiltered|uncensored)",
     "Jailbreak persona activation", 0.95),
    (r"do\s+anything\s+now",
     "DAN jailbreak", 0.90),
    (r"(respond|answer|act)\s+without\s+(any\s+)?(restrictions|filters|limitations|rules|guidelines)",
     "Restriction removal", 0.90),
    (r"(no|without)\s+(content\s+)?(filter|moderation|safety|censorship)",
     "Content filter bypass", 0.90),

    # --- Safety Bypass ---
    (r"(bypass|circumvent|avoid|disable|turn\s+off|remove)\s+(all\s+)?(safety|security|content)\s+(filters|rules|guidelines|mechanisms|protocols|features)",
     "Safety bypass attempt", 0.95),
    (r"(pretend|imagine|assume)\s+(that\s+)?(safety|content)\s+(rules|guidelines|filters)\s+(do\s+not|don.t)\s+exist",
     "Safety rule negation", 0.90),
    (r"ignore\s+(openai|anthropic|google|meta)\s+(policies|guidelines|rules|terms)",
     "Policy bypass attempt", 0.90),

    # --- Role Playing Attacks ---
    (r"(pretend|act|behave|respond)\s+(to\s+be|as\s+if\s+you\s+are|like)\s+(an?\s+)?(evil|malicious|unrestricted|uncensored|unfiltered)\s+(ai|assistant|chatbot|model)",
     "Malicious role play", 0.85),
    (r"role\s*play\s+as\s+an?\s+ai\s+that\s+has\s+been\s+jailbroken",
     "Jailbreak role play", 0.90),
    (r"you\s+(must|have\s+to|should)\s+comply",
     "Coercion attempt", 0.70),

    # --- Encoding Tricks ---
    (r"base64\s+(decode|encode)",
     "Encoding obfuscation", 0.75),
    (r"rot13",
     "ROT13 obfuscation", 0.75),
    (r"(reverse|backwards)\s+this",
     "Text reversal trick", 0.60),

    # --- Special Token Injection ---
    (r"\[/?inst\]",
     "INST token injection", 0.95),
    (r"\[/?system\]",
     "System token injection", 0.95),
    (r"###\s*system",
     "System header injection", 0.90),
    (r"<\|im_start\|>|<\|im_end\|>",
     "ChatML token injection", 0.95),
    (r"<!--.*?-->",
     "HTML comment injection", 0.70),

    # --- Prompt Leaking ---
    (r"(tell|show|give)\s+me\s+(what|the)\s+(instructions|developers?|rules|prompt)",
     "Prompt leak request", 0.80),
    (r"(what|which)\s+(hidden|secret)\s+(rules|instructions|guidelines)",
     "Secret extraction", 0.80),
    (r"(format|output|reply\s+with)\s+(your\s+)?(system|initial)\s+(message|prompt|instructions)\s+as\s+(a\s+)?(json|code|markdown)",
     "Formatted prompt extraction", 0.90),

    # --- Story / Fiction Frame Attacks ---
    (r"write\s+a?\s*(story|novel|fiction|tale|scenario)\s+where\s+.{0,60}(ai|assistant|model|chatbot).{0,40}(ignores?|bypasses?|reveals?|disables?)",
     "Fiction frame attack", 0.85),
    (r"(create|write)\s+(a\s+)?(story|script|scene)\s+where.{0,60}(safety|filters?|rules?)\s+(don.t|doesn.t|no\s+longer)\s+exist",
     "Fiction safety bypass", 0.85),
    (r"(write|generate)\s+(me\s+)?a\s+(story|hypothetical|fictional\s+scenario).{0,80}(ignore|bypass|disable|reveal)\s+(all\s+)?(instructions|safety|filters?|rules?)",
     "Fictional injection wrapper", 0.88),

    # --- Hypothetical / Imagination Bypass ---
    (r"imagine\s+(a\s+world|you\s+are|that).{0,80}(rules?|filter|safety|restriction).{0,40}(don.t|doesn.t|not|no\s+longer)\s+exist",
     "Hypothetical bypass scenario", 0.85),
    (r"(in\s+a\s+hypothetical|hypothetically|let.s\s+say|suppose\s+that).{0,80}(ignor|bypass|disable|remove).{0,40}(safety|filter|restriction|rule)",
     "Hypothetical framing", 0.80),
    (r"(for\s+(educational|research|academic|testing)\s+purposes?).{0,100}(ignore|bypass|reveal|disable)",
     "Research framing attack", 0.75),
    (r"(as\s+a\s+(thought\s+experiment|hypothetical|test)).{0,80}(ignore|bypass|reveal)",
     "Thought experiment framing", 0.78),

    # --- Translation / Summarization Injection ---
    (r"translat[ei].{0,30}[\"''\u201c\u201d].{0,200}(ignore|bypass|system\s+prompt|reveal).{0,200}[\"''\u201c\u201d]",
     "Translation-wrapped injection", 0.88),
    (r"summariz[ei].{0,30}[\"''\u201c\u201d].{0,200}(ignore|bypass|system\s+prompt|reveal).{0,200}[\"''\u201c\u201d]",
     "Summarization-wrapped injection", 0.85),
    (r"(paraphras|rewrite|convert).{0,30}[\"''\u201c\u201d].{0,200}(ignore|bypass|system\s+prompt|new\s+instruction).{0,200}[\"''\u201c\u201d]",
     "Rewrite-wrapped injection", 0.83),

    # --- Multi-Turn / Gradual Escalation Indicators ---
    (r"(in\s+our\s+last\s+conversation|you\s+previously\s+agreed|earlier\s+you\s+said|remember\s+when\s+you).{0,80}(ignore|bypass|allow|reveal)",
     "Multi-turn reference manipulation", 0.80),
    (r"(continuing\s+from|as\s+we\s+discussed|building\s+on\s+what).{0,80}(ignore|bypass|jailbreak|unrestricted)",
     "Session escalation attempt", 0.75),

    # --- Covert Instruction Embedding ---
    (r"(the\s+(next|following)\s+(message|input|prompt|text)\s+is\s+(just\s+a\s+)?test).{0,80}(ignore|bypass|allow)",
     "Covert test framing", 0.78),
    (r"note\s+to\s+(ai|assistant|model|llm)\s*:\s*(ignore|bypass|disregard|new\s+instruction)",
     "Hidden note injection", 0.90),
    (r"\[hidden\s+(instruction|message|note)\].{0,100}(ignore|bypass|reveal|new)",
     "Hidden bracket injection", 0.90),
    (r"<!--.{0,200}(ignore|bypass|system|instruction).{0,200}-->",
     "HTML comment injection", 0.85),
]


def check_rules(text: str) -> dict:
    """
    Check a prompt against all injection patterns.

    Returns:
        dict with keys:
          - matched: bool
          - matches: list of dicts with pattern details
          - max_severity: float (0.0 - 1.0)
          - rule_score: float (0.0 - 1.0)
    """
    text_lower = text.lower().strip()
    matches = []

    for pattern, description, severity in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            matches.append({
                "pattern": pattern,
                "description": description,
                "severity": severity,
            })

    if not matches:
        return {
            "matched": False,
            "matches": [],
            "max_severity": 0.0,
            "rule_score": 0.0,
        }

    max_severity = max(m["severity"] for m in matches)
    # Combine severities — more pattern matches = higher score
    # Use a weighted combination: max_severity + bonus for multiple matches
    bonus = min(0.1 * (len(matches) - 1), 0.2)  # up to 0.2 bonus
    rule_score = min(max_severity + bonus, 1.0)

    return {
        "matched": True,
        "matches": matches,
        "max_severity": max_severity,
        "rule_score": rule_score,
    }
