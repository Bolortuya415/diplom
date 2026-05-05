"""
Training script for the Sensitive Content Classifier.

Trains a multi-class classifier to detect harmful content in Mongolian text.
Uses TF-IDF features with Logistic Regression (primary) and SVM (comparison).

Thesis note:
    This script demonstrates a complete ML training pipeline including
    data loading, preprocessing, model training with hyperparameter tuning,
    cross-validation, and model persistence. Two models are compared:
    Logistic Regression and Linear SVM. The best model is saved for deployment.

Usage:
    python training/scripts/train.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from training.scripts.preprocess import (
    load_dataset,
    preprocess_dataset,
    create_features,
    LABEL_MAP,
)


def train_logistic_regression(X_train, y_train) -> LogisticRegression:
    """
    Train Logistic Regression with hyperparameter tuning.

    Uses GridSearchCV with 5-fold cross-validation to find
    the best regularization strength (C parameter).
    """
    param_grid = {
        "C": [0.01, 0.1, 1.0, 10.0],
        "class_weight": ["balanced"],
        "max_iter": [1000],
    }

    # Note: `multi_class="multinomial"` was removed in scikit-learn 1.7 —
    # modern lbfgs handles multinomial classification automatically when y has >2 classes.
    grid = GridSearchCV(
        LogisticRegression(solver="lbfgs", random_state=42),
        param_grid,
        cv=5,
        scoring="f1_macro",
        n_jobs=-1,
        verbose=1,
    )
    grid.fit(X_train, y_train)

    print(f"\nLogistic Regression best params: {grid.best_params_}")
    print(f"Logistic Regression best CV F1 (macro): {grid.best_score_:.4f}")

    return grid.best_estimator_


def train_svm(X_train, y_train) -> CalibratedClassifierCV:
    """
    Train Linear SVM with probability calibration.

    LinearSVC is faster but doesn't output probabilities natively.
    CalibratedClassifierCV wraps it to provide predict_proba().
    """
    param_grid = {
        "C": [0.01, 0.1, 1.0, 10.0],
        "class_weight": ["balanced"],
        "max_iter": [2000],
    }

    # `dual='auto'` is the sklearn>=1.3 recommended value and keeps behavior compatible
    # across sklearn versions; the old default `dual=True` emits deprecation warnings.
    grid = GridSearchCV(
        LinearSVC(random_state=42, dual="auto"),
        param_grid,
        cv=5,
        scoring="f1_macro",
        n_jobs=-1,
        verbose=1,
    )
    grid.fit(X_train, y_train)

    print(f"\nSVM best params: {grid.best_params_}")
    print(f"SVM best CV F1 (macro): {grid.best_score_:.4f}")

    # Wrap with calibration for probability output
    calibrated = CalibratedClassifierCV(grid.best_estimator_, cv=3)
    calibrated.fit(X_train, y_train)

    return calibrated


def evaluate_model(model, X_test, y_test, model_name: str) -> dict:
    """Evaluate model and return metrics."""
    y_pred = model.predict(X_test)

    report = classification_report(
        y_test, y_pred,
        target_names=[LABEL_MAP[i] for i in sorted(LABEL_MAP.keys())],
        output_dict=True,
    )
    report_str = classification_report(
        y_test, y_pred,
        target_names=[LABEL_MAP[i] for i in sorted(LABEL_MAP.keys())],
    )
    cm = confusion_matrix(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro")

    print(f"\n{'='*60}")
    print(f"  {model_name} — Test Set Results")
    print(f"{'='*60}")
    print(report_str)
    print(f"Confusion Matrix:\n{cm}")

    return {
        "model_name": model_name,
        "f1_macro": float(f1_macro),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }


def cross_validate_model(model, X_train, y_train, model_name: str):
    """Run cross-validation and print results."""
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring="f1_macro", n_jobs=-1)
    print(f"\n{model_name} — 5-Fold CV F1 (macro): {scores.mean():.4f} (+/- {scores.std():.4f})")
    return scores


def main():
    # ── Paths ──
    project_root = Path(__file__).parent.parent
    # Use expanded dataset if available, otherwise fall back to original
    expanded_path = project_root / "data" / "dataset_expanded.csv"
    data_path = expanded_path if expanded_path.exists() else project_root / "data" / "dataset.csv"
    model_dir = project_root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # ── Load & preprocess ──
    print("Loading dataset...")
    df = load_dataset(str(data_path))
    df = preprocess_dataset(df)

    # ── Create features ──
    print("\nCreating TF-IDF features...")
    features = create_features(df, save_dir=str(model_dir))

    X_train = features["X_train"]
    X_test = features["X_test"]
    y_train = features["y_train"]
    y_test = features["y_test"]

    # ── Train models ──
    print("\n" + "="*60)
    print("  Training Logistic Regression")
    print("="*60)
    lr_model = train_logistic_regression(X_train, y_train)

    print("\n" + "="*60)
    print("  Training Linear SVM")
    print("="*60)
    svm_model = train_svm(X_train, y_train)

    # ── Evaluate both ──
    lr_results = evaluate_model(lr_model, X_test, y_test, "Logistic Regression")
    svm_results = evaluate_model(svm_model, X_test, y_test, "Linear SVM")

    # ── Select best model ──
    if lr_results["f1_macro"] >= svm_results["f1_macro"]:
        best_model = lr_model
        best_name = "logistic_regression"
        best_results = lr_results
    else:
        best_model = svm_model
        best_name = "linear_svm"
        best_results = svm_results

    print(f"\n{'='*60}")
    print(f"  Best model: {best_name} (F1 macro: {best_results['f1_macro']:.4f})")
    print(f"{'='*60}")

    # ── Save best model ──
    model_path = model_dir / "sensitive_classifier.pkl"
    joblib.dump(best_model, model_path)
    print(f"Model saved to: {model_path}")

    # ── Save training metadata ──
    metadata = {
        "model_type": best_name,
        "trained_at": datetime.now().isoformat(),
        "dataset_size": len(df),
        "train_size": X_train.shape[0],
        "test_size": X_test.shape[0],
        "num_features": X_train.shape[1],
        "labels": LABEL_MAP,
        "f1_macro": best_results["f1_macro"],
        "classification_report": best_results["classification_report"],
        "confusion_matrix": best_results["confusion_matrix"],
    }

    metadata_path = model_dir / "training_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Metadata saved to: {metadata_path}")

    return best_model, best_results


if __name__ == "__main__":
    main()
