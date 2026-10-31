"""Unit tests for the DatasetLoader module.

Tests:
1. Missing file error handling and instructional error messaging.
2. UTF-8 encoded dataset loading and metadata extraction.
3. Latin-1 / non-UTF-8 encoding fallback.
4. Ground-truth fraud label detection and class distribution computation.
5. Unlabeled transaction dataset handling.
"""

import pytest
import pandas as pd
from pathlib import Path
from dataset.loader import DatasetLoader, DatasetSummary


def test_missing_file_raises_filenotfound(tmp_path: Path):
    """Verify that a non-existent path raises FileNotFoundError with helpful guidance."""
    loader = DatasetLoader(default_dir=tmp_path)
    non_existent = tmp_path / "missing_transactions.csv"

    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load_dataset(file_path=non_existent)

    assert "Dataset file not found at" in str(exc_info.value)
    assert "Please place your dataset" in str(exc_info.value)


def test_empty_directory_raises_filenotfound(tmp_path: Path):
    """Verify that calling loader with no path on an empty directory raises FileNotFoundError."""
    loader = DatasetLoader(default_dir=tmp_path)

    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load_dataset()

    assert "No CSV dataset found" in str(exc_info.value)
    assert "documentation/dataset_guide.md" in str(exc_info.value)


def test_load_valid_labeled_csv_utf8(tmp_path: Path):
    """Verify loading a UTF-8 labeled UPI dataset."""
    sample_csv = tmp_path / "upi_sample.csv"
    data = {
        "tx_id": ["TX101", "TX102", "TX103", "TX104"],
        "sender_upi": ["user1@okaxis", "user2@paytm", "user3@okhdfc", "user4@icici"],
        "receiver_upi": ["merchant@icici", "friend@axis", "mule@ybl", "store@paytm"],
        "amount": [1200.0, 450.0, 95000.0, 310.0],
        "channel": ["UPI_APP", "QR_CODE", "INTENT_FLOW", "UPI_APP"],
        "is_fraud": [0, 0, 1, 0],
    }
    df_src = pd.DataFrame(data)
    df_src.to_csv(sample_csv, index=False, encoding="utf-8")

    loader = DatasetLoader()
    df, summary = loader.load_dataset(file_path=sample_csv)

    assert len(df) == 4
    assert summary.rows == 4
    assert summary.columns_count == 6
    assert "amount" in summary.columns
    assert summary.has_fraud_label is True
    assert summary.fraud_label_column == "is_fraud"
    assert summary.fraud_distribution == {"0": 3, "1": 1}
    assert summary.encoding_used == "utf-8"
    assert len(summary.sample_records) == 4


def test_load_csv_latin1_encoding(tmp_path: Path):
    """Verify multi-encoding fallback handles Latin-1 / Windows-1252 bytes gracefully."""
    sample_csv = tmp_path / "latin1_sample.csv"
    # Content with Latin-1 byte that would crash strict UTF-8
    content = "tx_id,sender_upi,notes\nTX1,alice@okaxis,Caf\xe9 payment\nTX2,bob@paytm,Regular\n"
    sample_csv.write_bytes(content.encode("latin-1"))

    loader = DatasetLoader()
    df, summary = loader.load_dataset(file_path=sample_csv)

    assert len(df) == 2
    assert summary.encoding_used in ["latin-1", "cp1252"]
    assert "Café payment" in df["notes"].values[0]


def test_load_unlabeled_csv(tmp_path: Path):
    """Verify dataset without fraud ground-truth labels is handled properly."""
    sample_csv = tmp_path / "unlabeled.csv"
    data = {
        "tx_id": ["TX201", "TX202"],
        "amount": [500.0, 1200.0],
    }
    pd.DataFrame(data).to_csv(sample_csv, index=False)

    loader = DatasetLoader()
    df, summary = loader.load_dataset(file_path=sample_csv)

    assert len(df) == 2
    assert summary.has_fraud_label is False
    assert summary.fraud_label_column is None
    assert summary.fraud_distribution is None
