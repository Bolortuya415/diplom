"""
Evaluation script for the Sensitive Content Classifier.

Generates detailed evaluation metrics, visualizations, and error analysis
suitable for inclusion in a bachelor thesis.

Thesis note:
    This script produces all evaluation artifacts needed for the thesis:
    confusion matrix heatmap, per-class metrics bar chart, ROC curves,
    and error analysis report.

Usage:
    python training/scripts/evaluate.py
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    roc_curve,
    auc,
    precision_recall_curve,
)
from sklearn.preprocessing import label_binarize

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from training.scripts.preprocess import (
    load_dataset,
    preprocess_dataset,
    LABEL_MAP,
)


def load_trained_model(model_dir: str) -> tuple:
    """Load the trained model and vectorizer."""
    model = joblib.load(Path(model_dir) / "sensitive_classifier.pkl")
    vectorizer = joblib.load(Path(model_dir) / "tfidf_vectorizer.pkl")
    return model, vectorizer


def plot_confusion_matrix(y_true, y_pred, labels, save_path: str):
    """Generate and save confusion matrix heatmap."""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=labels, yticklabels=labels,
    )
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix — Sensitive Content Classifier")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Confusion matrix saved to: {save_path}")


def plot_per_class_metrics(report_dict, labels, save_path: str):
    """Bar chart of precision, recall, F1 per class."""
    metrics_df = pd.DataFrame({
        "Precision": [report_dict[l]["precision"] for l in labels],
        "Recall": [report_dict[l]["recall"] for l in labels],
        "F1-Score": [report_dict[l]["f1-score"] for l in labels],
    }, index=labels)

    ax = metrics_df.plot(kind="bar", figsize=(10, 6), width=0.8)
    plt.ylabel("Score")
    plt.title("Per-Class Metrics — Sensitive Content Classifier")
    plt.xticks(rotation=45, ha="right")
    plt.ylim(0, 1.05)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Per-class metrics plot saved to: {save_path}")


def plot_roc_curves(y_true, y_proba, labels, save_path: str):
    """Plot One-vs-Rest ROC curves for each class."""
    n_classes = len(labels)
    y_bin = label_binarize(y_true, classes=list(range(n_classes)))

    plt.figure(figsize=(8, 6))
    for i, label in enumerate(labels):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{label} (AUC={roc_auc:.2f})")

    plt.plot([0, 1], [0, 1], "k--", alpha=0.3)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves (One-vs-Rest)")
    plt.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"ROC curves saved to: {save_path}")


def error_analysis(X_test_text, y_true, y_pred, save_path: str):
    """Generate error analysis report."""
    errors = []
    for text, true, pred in zip(X_test_text, y_true, y_pred):
        if true != pred:
            errors.append({
                "text": text,
                "true_label": LABEL_MAP[true],
                "predicted_label": LABEL_MAP[pred],
            })

    error_df = pd.DataFrame(errors)
    if len(error_df) > 0:
        error_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"\nError analysis ({len(errors)} misclassifications) saved to: {save_path}")
        print("\nSample errors:")
        for _, row in error_df.head(5).iterrows():
            print(f"  Text: {row['text'][:60]}...")
            print(f"  True: {row['true_label']} → Predicted: {row['predicted_label']}")
            print()
    else:
        print("No misclassifications found on test set!")

    return error_df


def main():
    project_root = Path(__file__).parent.parent
    model_dir = project_root / "models"
    eval_dir = project_root / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    # Load saved model and vectorizer (must use the SAME vectorizer as training)
    model, vectorizer = load_trained_model(str(model_dir))

    # Load and preprocess data
    data_path = project_root / "data" / "dataset.csv"
    df = load_dataset(str(data_path))
    df = preprocess_dataset(df)

    # Split data with same random_state as training to get the same test set
    from sklearn.model_selection import train_test_split
    _, X_test_text, _, y_test = train_test_split(
        df["text_clean"].values,
        df["label"].values,
        test_size=0.2,
        random_state=42,
        stratify=df["label"].values,
    )

    # Transform with the SAVED vectorizer (not a new one)
    X_test = vectorizer.transform(X_test_text)

    # Predictions
    y_pred = model.predict(X_test)
    labels = [LABEL_MAP[i] for i in sorted(LABEL_MAP.keys())]

    # Overall metrics
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro")),
        "f1_weighted": float(f1_score(y_test, y_pred, average="weighted")),
        "precision_macro": float(precision_score(y_test, y_pred, average="macro")),
        "recall_macro": float(recall_score(y_test, y_pred, average="macro")),
    }

    print("\n" + "="*60)
    print("  EVALUATION RESULTS")
    print("="*60)
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    # Full classification report
    report_str = classification_report(y_test, y_pred, target_names=labels)
    report_dict = classification_report(y_test, y_pred, target_names=labels, output_dict=True)
    print(f"\n{report_str}")

    # Save metrics
    with open(eval_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Plots
    plot_confusion_matrix(y_test, y_pred, labels, str(eval_dir / "confusion_matrix.png"))
    plot_per_class_metrics(report_dict, labels, str(eval_dir / "per_class_metrics.png"))

    # ROC curves (if model supports predict_proba)
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)
        plot_roc_curves(y_test, y_proba, labels, str(eval_dir / "roc_curves.png"))

    # Error analysis
    error_analysis(X_test_text, y_test, y_pred, str(eval_dir / "error_analysis.csv"))

    print(f"\nAll evaluation artifacts saved to: {eval_dir}")


if __name__ == "__main__":
    main()
