"""Unit tests for the DatasetExplorer module."""

from pathlib import Path
from dataset.explorer import DatasetExplorer


def test_dataset_explorer_metrics():
    """Verify that DatasetExplorer calculates complete metrics on the active dataset."""
    explorer = DatasetExplorer()
    results = explorer.analyze()

    assert results["shape"][0] == 12000
    assert results["shape"][1] == 13
    assert results["duplicates_count"] == 0
    assert len(results["missing_values"]) == 0

    # Verify amount statistics
    amt = results["amount_stats"]
    assert amt["min"] > 0
    assert amt["max"] <= 100000.0  # NPCI daily limit
    assert amt["skewness"] > 0     # Positively skewed

    # Verify fraud statistics
    fraud = results["fraud_stats"]
    assert fraud["fraud_count"] == 420
    assert fraud["legitimate_count"] == 11580
    assert fraud["fraud_percentage"] == 3.5
    assert fraud["fraud_amount_mean"] > fraud["legit_amount_mean"]

    # Verify temporal statistics
    tstats = results["time_stats"]
    assert tstats["daytime_tx_count_08_to_22"] > tstats["midnight_tx_count_01_to_04"]

    # Verify feature utility presence
    assert len(results["feature_utility"]) >= 5


def test_markdown_report_generation(tmp_path: Path):
    """Verify that explorer writes a complete Markdown report."""
    explorer = DatasetExplorer()
    results = explorer.analyze()
    target_report = tmp_path / "test_report.md"

    md = explorer.generate_markdown_report(results, target_report)
    assert target_report.exists()
    assert "# FraudShield AI — Comprehensive Transaction Dataset Analysis Report" in md
    assert "Executive Summary" in md
    assert "Feature Utility Matrix" in md
