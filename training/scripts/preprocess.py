"""
Preprocessing module for the Sensitive Content Classifier.

Handles text cleaning, normalization, and feature extraction
for Mongolian text classification.

Thesis note:
    This module demonstrates standard NLP preprocessing steps
    adapted for Mongolian Cyrillic text. The preprocessing pipeline
    includes normalization, cleaning, and TF-IDF vectorization.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
import joblib


# Mongolian stopwords (common words that don't carry classification signal)
MONGOLIAN_STOPWORDS = [
    "бол", "нь", "байна", "байгаа", "гэж", "гэдэг", "гэсэн", "юм",
    "энэ", "тэр", "бүх", "ч", "мөн", "болон", "буюу", "эсвэл",
    "хэдийгээр", "гэвч", "харин", "тийм", "ийм", "ингэж", "тэгж",
    "бас", "дахин", "ямар", "хэн", "юу", "хаана", "хэзээ", "яагаад",
    "хэрхэн", "их", "бага", "маш", "тун", "нэг", "хоёр", "бүгд",
    "зарим", "олон", "цөөн", "өөр", "адил", "хамт", "дотор", "дээр",
    "доор", "өмнө", "хойно", "дараа", "тухай", "талаар", "учир",
]


def clean_mongolian_text(text: str) -> str:
    """
    Clean and normalize Mongolian text.

    Steps:
        1. Lowercase
        2. Remove URLs
        3. Remove emails
        4. Remove special characters (keep Cyrillic, digits, spaces)
        5. Normalize whitespace
    """
    if not isinstance(text, str):
        return ""

    text = text.lower().strip()
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Remove emails
    text = re.sub(r"\S+@\S+", "", text)
    # Keep Mongolian Cyrillic (U+0400-U+04FF), digits, spaces
    text = re.sub(r"[^\u0400-\u04ff\s0-9]", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_stopwords(text: str, stopwords: list = None) -> str:
    """Remove Mongolian stopwords from text."""
    if stopwords is None:
        stopwords = MONGOLIAN_STOPWORDS
    words = text.split()
    return " ".join(w for w in words if w not in stopwords)


def load_dataset(csv_path: str) -> pd.DataFrame:
    """Load and validate the labeled dataset."""
    df = pd.read_csv(csv_path)
    required_cols = {"text", "label", "label_name"}
    assert required_cols.issubset(df.columns), f"Missing columns: {required_cols - set(df.columns)}"

    print(f"Dataset loaded: {len(df)} samples")
    print(f"Label distribution:\n{df['label_name'].value_counts()}")

    return df


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Apply cleaning pipeline to the dataset."""
    df = df.copy()
    df["text_clean"] = df["text"].apply(clean_mongolian_text)
    df["text_clean"] = df["text_clean"].apply(remove_stopwords)

    # Remove empty rows after cleaning
    empty_mask = df["text_clean"].str.strip() == ""
    if empty_mask.any():
        print(f"Warning: Removing {empty_mask.sum()} empty rows after cleaning")
        df = df[~empty_mask].reset_index(drop=True)

    return df


def create_features(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    max_features: int = 5000,
    save_dir: str = None,
) -> dict:
    """
    Create TF-IDF features and train/test split.

    Args:
        df: Preprocessed DataFrame with 'text_clean' and 'label' columns
        test_size: Fraction of data for testing
        random_state: Random seed for reproducibility
        max_features: Maximum number of TF-IDF features
        save_dir: Directory to save the vectorizer

    Returns:
        Dictionary with X_train, X_test, y_train, y_test, vectorizer
    """
    X_train_text, X_test_text, y_train, y_test = train_test_split(
        df["text_clean"].values,
        df["label"].values,
        test_size=test_size,
        random_state=random_state,
        stratify=df["label"].values,
    )

    # TF-IDF with character n-grams (robust for Mongolian morphology)
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",       # Character n-grams at word boundaries
        ngram_range=(2, 5),       # Bigrams to 5-grams
        max_features=max_features,
        sublinear_tf=True,        # Apply sublinear TF scaling
        min_df=2,                 # Ignore very rare n-grams
    )

    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    if save_dir:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        joblib.dump(vectorizer, save_path / "tfidf_vectorizer.pkl")
        print(f"Vectorizer saved to {save_path / 'tfidf_vectorizer.pkl'}")

    print(f"Feature matrix: {X_train.shape[1]} features")
    print(f"Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples")

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "vectorizer": vectorizer,
        "X_train_text": X_train_text,
        "X_test_text": X_test_text,
    }


# Label mapping used across the project
LABEL_MAP = {
    0: "safe",
    1: "hate_speech",
    2: "harassment",
    3: "discrimination",
    4: "self_harm",
}

LABEL_MAP_REVERSE = {v: k for k, v in LABEL_MAP.items()}


if __name__ == "__main__":
    # Quick test
    data_path = Path(__file__).parent.parent / "data" / "dataset.csv"
    df = load_dataset(str(data_path))
    df = preprocess_dataset(df)
    features = create_features(df, save_dir=str(Path(__file__).parent.parent / "models"))
    print("\nPreprocessing complete.")
    print(f"Sample cleaned text: {df['text_clean'].iloc[0]}")
