"""FraudShield AI - Comprehensive Model Evaluation & Threshold Sensitivity Engine.

Performs rigorous statistical evaluation of the Isolation Forest model:
- Precision, Recall, F1-Score, Balanced Accuracy, Specificity
- False Positive Rate (FPR) & False Negative Rate (FNR)
- Confusion Matrix breakdown
- ROC-AUC and Precision-Recall AUC (PR-AUC)
- Impact analysis of severe class imbalance (1:27.6)
- Sensitivity sweep comparing alternative contamination thresholds [0.01 to 0.10]
- Visualisation generation (Confusion Matrix, ROC/PR Curves, Contamination Trade-off)
"""

from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    auc,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from backend.core.config import settings
from ml_model.predictor import FraudShieldPredictor

THEME_BG = "#0d131f"
THEME_CARD = "#161f30"
THEME_TEXT = "#f8fafc"
THEME_MUTED = "#94a3b8"
COLOR_BLUE = "#3b82f6"
COLOR_PURPLE = "#8b5cf6"
COLOR_CYAN = "#06b6d4"
COLOR_RED = "#ef4444"
COLOR_GREEN = "#10b981"
COLOR_AMBER = "#f59e0b"


class ModelEvaluator:
    """Comprehensive evaluator for anomaly detection and fraud classification trade-offs."""

    def __init__(
        self,
        test_features_path: Path = settings.PROCESSED_DATASET_DIR / "test_features.csv",
        test_labels_path: Path = settings.PROCESSED_DATASET_DIR / "test_labels.csv",
        train_features_path: Path = settings.PROCESSED_DATASET_DIR / "train_features.csv",
        output_dir: Path = settings.DOCS_DIR / "figures",
    ) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.X_test = pd.read_csv(test_features_path)
        self.y_test = pd.read_csv(test_labels_path).iloc[:, 0] if test_labels_path.exists() else None
        self.X_train = pd.read_csv(train_features_path) if train_features_path.exists() else None

        self.predictor = FraudShieldPredictor()

    def evaluate_primary_model(self) -> dict:
        """Calculates complete statistical metrics for the production model."""
        preds = self.predictor.model.predict(self.X_test)
        scores = self.predictor.model.decision_function(self.X_test)

        # Standardise: 1 = anomaly/suspicious, 0 = normal
        y_pred = np.where(preds == -1, 1, 0)
        risk_scores = np.array([self.predictor.calculate_risk_score(s) for s in scores])

        if self.y_test is None:
            return {
                "has_labels": False,
                "total_samples": len(self.X_test),
                "anomalies_flagged": int(y_pred.sum()),
                "anomaly_rate": round(float(y_pred.mean() * 100), 2),
            }

        y_true = self.y_test.values
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # Rate calculations
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        balanced_acc = (recall + specificity) / 2.0

        roc_auc = roc_auc_score(y_true, risk_scores)
        prec_curve, rec_curve, _ = precision_recall_curve(y_true, risk_scores)
        pr_auc = auc(rec_curve, prec_curve)

        return {
            "has_labels": True,
            "total_samples": len(y_true),
            "actual_fraud_count": int(y_true.sum()),
            "actual_fraud_rate": round(float(y_true.mean() * 100), 2),
            "anomalies_flagged": int(y_pred.sum()),
            "flagged_rate": round(float(y_pred.mean() * 100), 2),
            "confusion_matrix": {
                "tp": int(tp),
                "fp": int(fp),
                "tn": int(tn),
                "fn": int(fn),
            },
            "metrics": {
                "precision": round(float(precision), 4),
                "recall": round(float(recall), 4),
                "f1_score": round(float(f1), 4),
                "fpr": round(float(fpr), 4),
                "fnr": round(float(fnr), 4),
                "specificity": round(float(specificity), 4),
                "balanced_accuracy": round(float(balanced_acc), 4),
                "roc_auc": round(float(roc_auc), 4),
                "pr_auc": round(float(pr_auc), 4),
            },
            "risk_scores": risk_scores,
            "y_pred": y_pred,
            "y_true": y_true,
        }

    def evaluate_contamination_sweep(
        self,
        contamination_rates: list[float] | None = None,
    ) -> list[dict]:
        """Trains and compares models across a sweep of contamination settings."""
        if self.X_train is None or self.y_test is None:
            return []

        rates = contamination_rates or [0.01, 0.02, 0.035, 0.05, 0.08, 0.10]
        sweep_results = []
        y_true = self.y_test.values

        print(f"Executing sensitivity sweep across contamination thresholds: {rates}...")

        for c in rates:
            model = IsolationForest(
                n_estimators=150,
                contamination=c,
                max_samples="auto",
                random_state=42,
                n_jobs=-1,
            )
            model.fit(self.X_train)
            raw_p = model.predict(self.X_test)
            y_pred = np.where(raw_p == -1, 1, 0)

            tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

            sweep_results.append({
                "contamination": c,
                "anomalies_flagged": int(y_pred.sum()),
                "flagged_rate_pct": round(float(y_pred.mean() * 100), 2),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "f1_score": round(float(f1), 4),
                "fpr": round(float(fpr), 4),
                "fnr": round(float(fnr), 4),
            })

        return sweep_results

    def generate_evaluation_visualisations(
        self,
        eval_dict: dict,
        sweep_results: list[dict],
    ) -> list[Path]:
        """Generates publication-quality charts for the evaluation report."""
        sns.set_theme(style="darkgrid", font="sans-serif")
        plt.rcParams.update({
            "figure.facecolor": THEME_BG,
            "axes.facecolor": THEME_CARD,
            "axes.edgecolor": "#243046",
            "axes.labelcolor": THEME_TEXT,
            "xtick.color": THEME_MUTED,
            "ytick.color": THEME_MUTED,
            "text.color": THEME_TEXT,
            "grid.color": "#1e293b",
        })

        generated_paths = []

        # --- Chart 1: Confusion Matrix Heatmap ---
        cm = eval_dict["confusion_matrix"]
        cm_matrix = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])

        fig1, ax1 = plt.subplots(figsize=(7, 6))
        sns.heatmap(
            cm_matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            xticklabels=["Predicted Normal", "Predicted Anomaly"],
            yticklabels=["Actual Normal", "Actual Fraud"],
            linewidths=1.5,
            linecolor=THEME_BG,
            ax=ax1,
        )
        ax1.set_title("Isolation Forest — Test Set Confusion Matrix", fontsize=13, fontweight="bold", pad=12)
        fig1.tight_layout()
        p1 = self.output_dir / "eval_confusion_matrix.png"
        fig1.savefig(p1, dpi=300, bbox_inches="tight")
        plt.close(fig1)
        generated_paths.append(p1)

        # --- Chart 2: ROC & PR Curves ---
        fig2, axes2 = plt.subplots(1, 2, figsize=(14, 5))
        y_true = eval_dict["y_true"]
        risk_scores = eval_dict["risk_scores"]

        # ROC Curve
        fpr_pts, tpr_pts, _ = roc_curve(y_true, risk_scores)
        axes2[0].plot(fpr_pts, tpr_pts, color=COLOR_BLUE, linewidth=2.5, label=f"Isolation Forest (ROC-AUC = {eval_dict['metrics']['roc_auc']:.4f})")
        axes2[0].plot([0, 1], [0, 1], color=THEME_MUTED, linestyle="--", linewidth=1.5, label="Random Guess (AUC = 0.50)")
        axes2[0].set_title("Receiver Operating Characteristic (ROC)", fontweight="bold")
        axes2[0].set_xlabel("False Positive Rate (FPR)")
        axes2[0].set_ylabel("True Positive Rate (Recall)")
        axes2[0].legend(facecolor=THEME_CARD, edgecolor="#243046")

        # Precision-Recall Curve
        prec_pts, rec_pts, _ = precision_recall_curve(y_true, risk_scores)
        axes2[1].plot(rec_pts, prec_pts, color=COLOR_PURPLE, linewidth=2.5, label=f"PR Curve (AUC = {eval_dict['metrics']['pr_auc']:.4f})")
        axes2[1].axhline(eval_dict["actual_fraud_rate"] / 100.0, color=THEME_MUTED, linestyle="--", label=f"Baseline Prevalance ({eval_dict['actual_fraud_rate']}%)")
        axes2[1].set_title("Precision-Recall (PR) Curve", fontweight="bold")
        axes2[1].set_xlabel("Recall")
        axes2[1].set_ylabel("Precision")
        axes2[1].legend(facecolor=THEME_CARD, edgecolor="#243046")

        fig2.tight_layout()
        p2 = self.output_dir / "eval_roc_pr_curves.png"
        fig2.savefig(p2, dpi=300, bbox_inches="tight")
        plt.close(fig2)
        generated_paths.append(p2)

        # --- Chart 3: Contamination Sweep Trade-off ---
        if sweep_results:
            fig3, ax3 = plt.subplots(figsize=(10, 5))
            df_sw = pd.DataFrame(sweep_results)
            ax3.plot(df_sw["contamination"] * 100, df_sw["recall"] * 100, marker="o", color=COLOR_GREEN, linewidth=2.2, label="Recall (Sensitivity %)")
            ax3.plot(df_sw["contamination"] * 100, df_sw["precision"] * 100, marker="s", color=COLOR_BLUE, linewidth=2.2, label="Precision (%)")
            ax3.plot(df_sw["contamination"] * 100, df_sw["f1_score"] * 100, marker="^", color=COLOR_PURPLE, linewidth=2.2, label="F1-Score (%)")
            ax3.plot(df_sw["contamination"] * 100, df_sw["fpr"] * 100, marker="x", color=COLOR_RED, linestyle="--", linewidth=1.8, label="False Positive Rate (FPR %)")

            ax3.axvline(3.5, color=COLOR_AMBER, linestyle=":", linewidth=2, label="Selected Rate (3.5%)")
            ax3.set_title("Threshold Trade-Off: Metrics vs. Contamination Parameter", fontsize=13, fontweight="bold", pad=12)
            ax3.set_xlabel("Contamination Parameter (%)")
            ax3.set_ylabel("Metric Value (%)")
            ax3.legend(facecolor=THEME_CARD, edgecolor="#243046")
            fig3.tight_layout()
            p3 = self.output_dir / "eval_contamination_tradeoff.png"
            fig3.savefig(p3, dpi=300, bbox_inches="tight")
            plt.close(fig3)
            generated_paths.append(p3)

        # --- Chart 4: Risk Score Separation Violin/KDE Plot ---
        fig4, ax4 = plt.subplots(figsize=(10, 5))
        df_dist = pd.DataFrame({"risk_score": risk_scores, "is_fraud": y_true})
        sns.kdeplot(data=df_dist, x="risk_score", hue="is_fraud", common_norm=False, fill=True, palette={0: COLOR_GREEN, 1: COLOR_RED}, alpha=0.35, ax=ax4)
        ax4.axvline(70.0, color=COLOR_AMBER, linestyle="--", linewidth=2.0, label="High-Risk Action Cutoff (70.0)")
        ax4.set_title("Calibrated Risk Score Separation: Legitimate vs. Actual Fraud", fontsize=13, fontweight="bold", pad=12)
        ax4.set_xlabel("FraudShield Calibrated Risk Score (0 - 100)")
        ax4.set_ylabel("Kernel Density")
        ax4.legend(["Legitimate (0)", "Fraudulent (1)", "High-Risk Cutoff (70)"], facecolor=THEME_CARD, edgecolor="#243046")
        fig4.tight_layout()
        p4 = self.output_dir / "eval_risk_score_distribution.png"
        fig4.savefig(p4, dpi=300, bbox_inches="tight")
        plt.close(fig4)
        generated_paths.append(p4)

        return generated_paths


if __name__ == "__main__":
    evaluator = ModelEvaluator()
    eval_metrics = evaluator.evaluate_primary_model()
    sweep = evaluator.evaluate_contamination_sweep()
    figures = evaluator.generate_evaluation_visualisations(eval_metrics, sweep)

    print("\n" + "=" * 65)
    print("  FRAUDSHIELD AI — COMPREHENSIVE MODEL EVALUATION")
    print("=" * 65)
    m = eval_metrics["metrics"]
    cm = eval_metrics["confusion_matrix"]
    print(f"  Total Test Samples   : {eval_metrics['total_samples']:,}")
    print(f"  Actual Fraud Cases   : {eval_metrics['actual_fraud_count']} ({eval_metrics['actual_fraud_rate']}%)")
    print(f"  Anomalies Flagged    : {eval_metrics['anomalies_flagged']} ({eval_metrics['flagged_rate']}%)")
    print("-" * 65)
    print(f"  Precision            : {m['precision'] * 100:.2f}%")
    print(f"  Recall (Sensitivity) : {m['recall'] * 100:.2f}%")
    print(f"  F1-Score             : {m['f1_score'] * 100:.2f}%")
    print(f"  False Positive Rate  : {m['fpr'] * 100:.2f}%")
    print(f"  False Negative Rate  : {m['fnr'] * 100:.2f}%")
    print(f"  Specificity          : {m['specificity'] * 100:.2f}%")
    print(f"  Balanced Accuracy    : {m['balanced_accuracy'] * 100:.2f}%")
    print(f"  ROC-AUC              : {m['roc_auc'] * 100:.2f}%")
    print(f"  PR-AUC               : {m['pr_auc'] * 100:.2f}%")
    print("-" * 65)
    print(f"  Confusion Matrix     : TP={cm['tp']}, FP={cm['fp']}, FN={cm['fn']}, TN={cm['tn']}")
    print("=" * 65)
    print(f"  Saved {len(figures)} evaluation figures to {evaluator.output_dir.resolve()}")
    print("=" * 65 + "\n")
