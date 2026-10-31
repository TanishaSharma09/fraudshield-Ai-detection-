"""Unit tests for the ModelEvaluator module."""

import pytest
from pathlib import Path
from ml_model.training.evaluate_models import ModelEvaluator


@pytest.fixture(scope="module")
def evaluation_results() -> dict:
    evaluator = ModelEvaluator()
    return evaluator.evaluate_primary_model()


def test_evaluator_metrics_mathematical_consistency(evaluation_results: dict):
    """Verify that confusion matrix and derived rates satisfy mathematical identities."""
    cm = evaluation_results["confusion_matrix"]
    m = evaluation_results["metrics"]

    total = cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"]
    assert total == evaluation_results["total_samples"]

    # Identity 1: Recall + False Negative Rate == 1.0
    assert abs((m["recall"] + m["fnr"]) - 1.0) < 1e-4

    # Identity 2: Specificity + False Positive Rate == 1.0
    assert abs((m["specificity"] + m["fpr"]) - 1.0) < 1e-4

    # Performance thresholds on 2,400 test set
    assert m["roc_auc"] > 0.95
    assert m["recall"] > 0.80
    assert m["precision"] > 0.50
    assert m["fpr"] < 0.05  # False positive rate under 5%


def test_contamination_sweep():
    """Verify contamination sweep exhibits expected precision/recall trade-off."""
    evaluator = ModelEvaluator()
    sweep = evaluator.evaluate_contamination_sweep(contamination_rates=[0.02, 0.05, 0.08])

    assert len(sweep) == 3
    # As contamination increases, recall increases while precision decreases
    assert sweep[0]["recall"] < sweep[2]["recall"]
    assert sweep[0]["precision"] > sweep[2]["precision"]


def test_evaluation_visualisations_exist():
    """Verify that evaluation charts are generated in documentation/figures."""
    evaluator = ModelEvaluator()
    eval_dict = evaluator.evaluate_primary_model()
    sweep = evaluator.evaluate_contamination_sweep(contamination_rates=[0.02, 0.05])
    figures = evaluator.generate_evaluation_visualisations(eval_dict, sweep)

    assert len(figures) == 4
    for fig in figures:
        assert fig.exists()
        assert fig.suffix == ".png"
        assert fig.stat().st_size > 10000
