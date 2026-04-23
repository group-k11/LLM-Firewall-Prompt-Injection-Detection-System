"""
Hybrid ML Detector
Phase 1: TF-IDF + SVM
Phase 2: Sentence Transformer + Logistic Regression
Phase 3: Weighted hybrid scoring
"""

import os
import joblib
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


# ---------------------------------------------------------------------------
# Phase 1 — TF-IDF + SVM
# ---------------------------------------------------------------------------

class SVMDetector:
    """TF-IDF vectorizer + SVM classifier."""

    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.loaded: bool = False
        self._load()

    def _load(self) -> None:
        vec_path = os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl")
        clf_path = os.path.join(MODELS_DIR, "svm_classifier.pkl")

        if os.path.exists(vec_path) and os.path.exists(clf_path):
            try:
                self.vectorizer = joblib.load(vec_path)
                self.classifier = joblib.load(clf_path)
                self.loaded = True
                print("[+] SVM model loaded")
            except Exception as e:
                print(f"[!] SVM load error: {e}")
        else:
            print("[!] SVM model not found — run train_model.py first")

    def predict(self, text: str) -> dict:
        if not self.loaded:
            return {"prediction": -1, "confidence": 0.0, "svm_score": 0.5}

        try:
            vec = self.vectorizer.transform([text])
            pred = int(self.classifier.predict(vec)[0])
            proba = self.classifier.predict_proba(vec)[0]
            svm_score = float(proba[1]) if len(proba) > 1 else float(pred)
            return {
                "prediction": pred,
                "confidence": float(max(proba)),
                "svm_score": round(svm_score, 4),
            }
        except Exception as e:
            print(f"[!] SVM predict error: {e}")
            return {"prediction": -1, "confidence": 0.0, "svm_score": 0.5}


# ---------------------------------------------------------------------------
# Phase 2 — Sentence Transformer + Logistic Regression
# ---------------------------------------------------------------------------

class TransformerDetector:
    """Sentence Transformer embeddings + Logistic Regression classifier."""

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        self._encoder = None  # lazy-loaded SentenceTransformer
        self.classifier = None
        self.loaded: bool = False
        self._load()

    def _load(self) -> None:
        clf_path = os.path.join(MODELS_DIR, "transformer_classifier.pkl")

        if not os.path.exists(clf_path):
            print("[!] Transformer classifier not found — run train_model.py first")
            return

        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            self._encoder = SentenceTransformer(self.MODEL_NAME)
            self.classifier = joblib.load(clf_path)
            self.loaded = True
            print("[+] Transformer model loaded")
        except Exception as e:
            print(f"[!] Transformer load error: {e}")

    def _encode(self, text: str) -> np.ndarray:
        return self._encoder.encode([text], convert_to_numpy=True)

    def predict(self, text: str) -> dict:
        if not self.loaded:
            return {"prediction": -1, "confidence": 0.0, "transformer_score": 0.5}

        try:
            embedding = self._encode(text)
            pred = int(self.classifier.predict(embedding)[0])
            proba = self.classifier.predict_proba(embedding)[0]
            transformer_score = float(proba[1]) if len(proba) > 1 else float(pred)
            return {
                "prediction": pred,
                "confidence": float(max(proba)),
                "transformer_score": round(transformer_score, 4),
            }
        except Exception as e:
            print(f"[!] Transformer predict error: {e}")
            return {"prediction": -1, "confidence": 0.0, "transformer_score": 0.5}


# ---------------------------------------------------------------------------
# Phase 3 — Hybrid Detector
# ---------------------------------------------------------------------------

class HybridDetector:
    """
    Combines SVM and Transformer predictions into a single weighted score.

    Scoring rules:
      - Default: 50% SVM + 50% Transformer
      - If either model scores > 0.9: boost its weight to 70%
      - If only one model available: use it exclusively
    """

    def __init__(self):
        self.svm = SVMDetector()
        self.transformer = TransformerDetector()

    @property
    def loaded(self) -> bool:
        return self.svm.loaded or self.transformer.loaded

    def predict(self, text: str) -> dict:
        svm_res = self.svm.predict(text)
        tr_res = self.transformer.predict(text)

        svm_score: float = svm_res["svm_score"]
        tr_score: float = tr_res["transformer_score"]
        svm_ok: bool = svm_res["prediction"] != -1
        tr_ok: bool = tr_res["prediction"] != -1

        if svm_ok and tr_ok:
            if svm_score > 0.9:
                combined = svm_score * 0.7 + tr_score * 0.3
            elif tr_score > 0.9:
                combined = svm_score * 0.3 + tr_score * 0.7
            else:
                combined = svm_score * 0.5 + tr_score * 0.5
        elif svm_ok:
            combined = svm_score
        elif tr_ok:
            combined = tr_score
        else:
            combined = 0.5  # neutral when both unavailable

        return {
            "svm_score": round(svm_score, 4),
            "transformer_score": round(tr_score, 4),
            "combined_score": round(max(0.0, min(1.0, combined)), 4),
            "svm_loaded": svm_ok,
            "transformer_loaded": tr_ok,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_detector: HybridDetector | None = None


def get_detector() -> HybridDetector:
    global _detector
    if _detector is None:
        _detector = HybridDetector()
    return _detector
