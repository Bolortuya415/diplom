"""
Inference wrapper for the Sensitive Content Classifier.

Provides a clean API for the backend to classify user input.
Loads the trained model once and exposes a predict() function.

Thesis note:
    This module bridges the trained classifier and the chatbot backend.
    It loads the saved TF-IDF vectorizer and classification model,
    preprocesses input text, and returns a structured prediction
    with label and confidence score.

Usage:
    from training.scripts.inference import SensitiveContentClassifier

    clf = SensitiveContentClassifier()
    result = clf.predict("Эмэгтэйчүүд удирдах албан тушаал хашихад тохиромжгүй")
    # result = {"label": "hate_speech", "label_id": 1, "confidence": 0.92, "is_safe": False}
"""

import sys
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from training.scripts.preprocess import (
    clean_mongolian_text,
    remove_stopwords,
    LABEL_MAP,
)


class SensitiveContentClassifier:
    """
    Wraps the trained sensitive content classifier for inference.

    Attributes:
        model: Trained sklearn classifier
        vectorizer: Fitted TF-IDF vectorizer
        confidence_threshold: Minimum confidence to trust the prediction
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        confidence_threshold: float = 0.5,
    ):
        if model_dir is None:
            model_dir = str(Path(__file__).parent.parent / "models")

        model_path = Path(model_dir) / "sensitive_classifier.pkl"
        vectorizer_path = Path(model_dir) / "tfidf_vectorizer.pkl"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run training/scripts/train.py first."
            )
        if not vectorizer_path.exists():
            raise FileNotFoundError(
                f"Vectorizer not found at {vectorizer_path}. Run training/scripts/train.py first."
            )

        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)
        self.confidence_threshold = confidence_threshold
        self.label_map = LABEL_MAP

    def preprocess(self, text: str) -> str:
        """Clean and normalize input text."""
        text = clean_mongolian_text(text)
        text = remove_stopwords(text)
        return text

    def predict(self, text: str) -> dict:
        """
        Classify a single text input.

        Args:
            text: Raw user input in Mongolian

        Returns:
            dict with keys: label, label_id, confidence, is_safe, all_scores
        """
        cleaned = self.preprocess(text)

        if not cleaned.strip():
            return {
                "label": "safe",
                "label_id": 0,
                "confidence": 1.0,
                "is_safe": True,
                "all_scores": {v: 0.0 for v in self.label_map.values()},
            }

        X = self.vectorizer.transform([cleaned])

        # Get prediction and probabilities
        label_id = int(self.model.predict(X)[0])

        if hasattr(self.model, "predict_proba"):
            probas = self.model.predict_proba(X)[0]
            confidence = float(probas[label_id])
            all_scores = {
                self.label_map[i]: float(probas[i])
                for i in range(len(probas))
            }
        else:
            confidence = 1.0
            all_scores = {self.label_map[label_id]: 1.0}

        label_name = self.label_map[label_id]

        # If confidence is below threshold, default to safe
        if confidence < self.confidence_threshold and label_id != 0:
            label_name = "safe"
            label_id = 0

        return {
            "label": label_name,
            "label_id": label_id,
            "confidence": round(confidence, 4),
            "is_safe": label_id == 0,
            "all_scores": {k: round(v, 4) for k, v in all_scores.items()},
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        """Classify multiple texts."""
        return [self.predict(text) for text in texts]


# Safety response templates for each unsafe category
SAFETY_RESPONSES = {
    "hate_speech": {
        "mn": (
            "Таны оруулсан текстэд үзэн ядалтын шинжтэй агуулга илэрсэн тул "
            "энэхүү асуултад хариулах боломжгүй байна. Хүн бүр тэгш эрхтэй, "
            "хүндлэл хүлээх ёстой гэдгийг сануулъя. Хүйсийн тэгш байдлын "
            "талаар илүү ихийг мэдэхийг хүсвэл асуугаарай."
        ),
    },
    "harassment": {
        "mn": (
            "Таны оруулсан текстэд дарамт, доромжлолын шинжтэй агуулга илэрлээ. "
            "Хэрэв та дарамтад өртөж байгаа бол дараах байгууллагуудад хандана уу:\n"
            "• Хүүхдийн тусламжийн утас: 108\n"
            "• Гэр бүлийн хүчирхийллийн эсрэг утас: 1222"
        ),
    },
    "discrimination": {
        "mn": (
            "Таны оруулсан текстэд ялгаварлан гадуурхалтын шинжтэй агуулга илэрлээ. "
            "Монгол Улсын Үндсэн хуулийн 14 дүгээр зүйлд 'Хүнийг үндэс, угсаа, хэл, "
            "арьсны өнгө, нас, хүйс, нийгмийн гарал байдал, хөрөнгө чинээ, эрхэлсэн "
            "ажил, албан тушаал, шашин шүтлэг, үзэл бодол, боловсролоор нь ялгаварлан "
            "гадуурхаж үл болно' гэж заасан байдаг."
        ),
    },
    "self_harm": {
        "mn": (
            "Таны бичсэн зүйлээс та хүнд нөхцөл байдалд байж магадгүй гэж ойлгож байна. "
            "Та ганцаараа биш. Тусламж авах боломжтой:\n\n"
            "🆘 Яаралтай тусламж: 103\n"
            "📞 Сэтгэл зүйн зөвлөгөө: 7012-0505\n"
            "📞 Хүүхдийн тусламжийн утас: 108\n\n"
            "Та одоо яг энэ мөчид аюулгүй байна уу?"
        ),
    },
}


if __name__ == "__main__":
    clf = SensitiveContentClassifier()

    test_inputs = [
        "Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?",
        "Эмэгтэйчүүд удирдах албан тушаал хашихад тохиромжгүй",
        "Чи юу ч мэдэхгүй тэнэг юм",
        "Эрэгтэй хүн илүү цалин авах ёстой",
        "Би амьдрахыг хүсэхгүй байна",
    ]

    print("Sensitive Content Classifier — Test Results\n")
    for text in test_inputs:
        result = clf.predict(text)
        status = "✅ SAFE" if result["is_safe"] else "⚠️ UNSAFE"
        print(f"Input: {text}")
        print(f"  {status} | Label: {result['label']} | Confidence: {result['confidence']}")
        if not result["is_safe"]:
            print(f"  Safety response: {SAFETY_RESPONSES[result['label']]['mn'][:80]}...")
        print()
