# Changelog

All notable changes to **LLM Firewall** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-04-25

### Added
- `encoding_normalizer.py` — Full adversarial encoding pipeline:
  - HTML entity decoding
  - Zero-width space (ZWSP) stripping
  - Unicode fullwidth → ASCII mapping
  - Homoglyph & leetspeak normalizer
  - Anomaly score output used in risk formula
- `nested_detector.py` — Detects injections wrapped inside:
  - Translation requests ("translate the following...")
  - Summarization wrappers ("summarize and then do X")
  - Hypothetical / fictional story frames
  - Quoted-string extractions
- `session_tracker.py` — Multi-turn context tracking:
  - Thread-safe in-memory ring buffer per `session_id`
  - Detects gradual escalation across conversation turns
  - Applies an automatic risk-score boost on repeated probing
- New API endpoints:
  - `GET /attack_trends` — time-series attack analytics (daily/weekly)
  - `GET /session/{session_id}` — full multi-turn session history
- `SessionTimeline.tsx` — frontend component visualizing escalating risk per turn
- `AttackChart.tsx` — SVG donut chart (attack categories) + bar chart (daily volume)
- Mobile-responsive stacked layout in `globals.css`

### Changed
- **Decision Engine** — scoring formula upgraded to 4-component weighted sum:
  ```
  final = 0.25×SVM + 0.30×Transformer + 0.25×Rules + 0.20×Encoding + session_boost
  ```
- **Malicious threshold** lowered from `0.70` → `0.60` for more aggressive blocking
- **High-severity rule override** now enforces a minimum floor score of `0.75`
- **Rule Engine** expanded by 18 new patterns (roleplay, hypotheticals, token injection)
- **SQLite schema** migrated — new columns:
  `session_id`, `normalized_prompt`, `attack_category`,
  `encoding_anomaly_score`, `triggered_layers`, `nested_score`
- **Architecture diagram** in README updated to reflect all 8 pipeline stages

### Contributors (v2.0)
- Sarthak Tagalpallewar — Encoding Normalizer, Nested Detector, Session Tracker, Decision Engine upgrade, README & CHANGELOG

---

## [1.0.0] — 2026-04-01

### Added
- Initial FastAPI backend with `/check_prompt` and `/stats` endpoints
- TF-IDF + SVM classifier (`train_model.py`)
- Sentence Transformer (`all-MiniLM-L6-v2`) + Logistic Regression
- Hybrid `HybridDetector` combining both ML models
- Rule Engine with 12 baseline regex patterns
- SQLite logging (`database.py`)
- Next.js dashboard with dark cyberpunk theme (Matrix rain, glassmorphism)
- Landing page with live stats bar and live demo panel
- OpenRouter primary + Ollama fallback LLM routing
- Docker Compose setup

---

> 📌 This project is developed for academic purposes — Software Engineering Course, 4th Semester, Group K11.
