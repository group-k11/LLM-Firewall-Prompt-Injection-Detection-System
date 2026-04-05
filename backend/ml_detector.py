"""
Machine Learning Detector
Loads a pre-trained TF-IDF + Naive Bayes classifier to classify prompts.
"""

import os
import joblib

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


class MLDetector:
    """ML-based prompt injection detector using TF-IDF + Naive Bayes."""

    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.loaded = False
        self._load_model()

    def _load_model(self):
        """Load the trained model and vectorizer from disk."""
        vectorizer_path = os.path.join(MODELS_DIR, "vectorizer.pkl")
        classifier_path = os.path.join(MODELS_DIR, "classifier.pkl")

        if os.path.exists(vectorizer_path) and os.path.exists(classifier_path):
            try:
                self.vectorizer = joblib.load(vectorizer_path)
                self.classifier = joblib.load(classifier_path)
                self.loaded = True
                print("[+] ML model loaded successfully")
            except Exception as e:
                print(f"[!] Error loading ML model: {e}")
                self.loaded = False
        else:
            print("[!] ML model not found. Run train_model.py first.")
            self.loaded = False

    def predict(self, text: str) -> dict:
        """
        Classify a prompt using the ML model.

        Returns:
            dict with keys:
              - prediction: int (0=safe, 1=malicious)
              - confidence: float (probability of the predicted class)
              - ml_score: float (probability of being malicious, 0.0-1.0)
        """
        if not self.loaded:
            return {
                "prediction": -1,
                "confidence": 0.0,
                "ml_score": 0.5,  # neutral if model not available
            }

        try:
            # Vectorize the input text
            text_vector = self.vectorizer.transform([text])

            # Get prediction
            prediction = self.classifier.predict(text_vector)[0]

            # Get probability scores
            probabilities = self.classifier.predict_proba(text_vector)[0]

            # probabilities[0] = P(safe), probabilities[1] = P(malicious)
            ml_score = float(probabilities[1]) if len(probabilities) > 1 else float(prediction)
            confidence = float(max(probabilities))

            return {
                "prediction": int(prediction),
                "confidence": confidence,
                "ml_score": ml_score,
            }
        except Exception as e:
            print(f"[!] ML prediction error: {e}")
            return {
                "prediction": -1,
                "confidence": 0.0,
                "ml_score": 0.5,
            }


# Singleton instance
_detector = None


def get_detector() -> MLDetector:
    """Get the singleton ML detector instance."""
    global _detector
    if _detector is None:
        _detector = MLDetector()
    return _detector
