"""FraudShield AI - Reusable Dataset Loader Module.

Engineered to ingest Indian digital payment and UPI/PaySim transaction datasets:
- Robust file existence checks with beginner-friendly guidance.
- Automatic multi-encoding fallback (utf-8, utf-8-sig, latin-1, cp1252).
- Structural inspection: dimensions, column types, null counts.
- Automatic fraud label detection across common industry conventions.
- Sample inspection and clean terminal summary rendering.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence
import pandas as pd

# Standard fraud label column names used in public payment datasets
POTENTIAL_FRAUD_COLUMNS: list[str] = [
    "is_fraud",
    "isfraud",
    "fraud",
    "fraud_label",
    "class",
    "target",
    "is_anomaly",
    "label",
]

# Supported file encodings to handle diverse operating systems and export formats
SUPPORTED_ENCODINGS: list[str] = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]


@dataclass
class DatasetSummary:
    """Structured metadata summary of a loaded dataset."""
    file_path: str
    file_size_mb: float
    rows: int
    columns_count: int
    columns: list[str]
    column_types: dict[str, str]
    missing_values: dict[str, int]
    has_fraud_label: bool
    fraud_label_column: str | None
    fraud_distribution: dict[str, int] | None
    encoding_used: str
    sample_records: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class DatasetLoader:
    """Reusable loader for Indian digital payments and transaction datasets."""

    def __init__(
        self,
        default_dir: Path | None = None,
        encodings: Sequence[str] = SUPPORTED_ENCODINGS,
    ) -> None:
        self.default_dir = default_dir or Path(__file__).resolve().parent / "raw"
        self.encodings = list(encodings)

    def load_dataset(
        self,
        file_path: str | Path | None = None,
        nrows: int | None = None,
    ) -> tuple[pd.DataFrame, DatasetSummary]:
        """Loads a CSV dataset, handles encodings, and extracts diagnostic summary.

        Args:
            file_path: Path to the CSV file. If None, looks for any .csv in default_dir.
            nrows: Optional integer to preview the first N rows for large files.

        Returns:
            Tuple of (pd.DataFrame, DatasetSummary).

        Raises:
            FileNotFoundError: If the specified file or dataset directory has no CSV.
            ValueError: If the file is not a valid CSV or is unreadable.
        """
        resolved_path = self._resolve_file_path(file_path)

        # Attempt reading with multi-encoding fallback
        df: pd.DataFrame | None = None
        used_encoding: str | None = None
        last_error: Exception | None = None

        for encoding in self.encodings:
            try:
                df = pd.read_csv(resolved_path, encoding=encoding, nrows=nrows)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, UnicodeError) as err:
                last_error = err
                continue
            except Exception as err:
                raise ValueError(f"Failed to parse CSV file '{resolved_path.name}': {err}") from err

        if df is None:
            raise ValueError(
                f"Could not read '{resolved_path}' with any supported encoding ({', '.join(self.encodings)}). "
                f"Last error: {last_error}"
            )

        # Generate comprehensive summary
        summary = self._inspect_dataframe(df, resolved_path, used_encoding)
        return df, summary

    def _resolve_file_path(self, file_path: str | Path | None) -> Path:
        """Resolves target path or searches default directory."""
        if file_path is not None:
            target = Path(file_path)
            if not target.exists():
                raise FileNotFoundError(
                    f"Dataset file not found at: '{target.resolve()}'.\n"
                    f"Please place your dataset (e.g. upi_transactions.csv or PaySim CSV) into "
                    f"'{self.default_dir.resolve()}' or specify the full path via --path."
                )
            return target

        # Search default directory for any .csv
        if self.default_dir.exists():
            csv_candidates = list(self.default_dir.glob("*.csv"))
            if csv_candidates:
                return csv_candidates[0]

        raise FileNotFoundError(
            f"No CSV dataset found in directory '{self.default_dir.resolve()}'.\n"
            f"To supply a dataset:\n"
            f"1. Download a public UPI or PaySim dataset (see documentation/dataset_guide.md).\n"
            f"2. Place the CSV file into: {self.default_dir.resolve()}\n"
            f"3. Run: python -m dataset.loader --path <path_to_csv>"
        )

    def _inspect_dataframe(
        self,
        df: pd.DataFrame,
        file_path: Path,
        encoding: str,
    ) -> DatasetSummary:
        """Extracts column diagnostics, null counts, fraud labels, and samples."""
        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
        columns = list(df.columns)
        column_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
        missing_values = {col: int(count) for col, count in df.isnull().sum().items() if count > 0}

        # Check for fraud ground-truth label
        has_fraud_label = False
        fraud_col_name: str | None = None
        fraud_distribution: dict[str, int] | None = None

        for col in columns:
            normalized_col = col.strip().lower().replace(" ", "_")
            if normalized_col in POTENTIAL_FRAUD_COLUMNS:
                has_fraud_label = True
                fraud_col_name = col
                # Calculate class distribution
                val_counts = df[col].value_counts(dropna=False).to_dict()
                fraud_distribution = {str(k): int(v) for k, v in val_counts.items()}
                break

        # Extract up to 5 sample records as dicts
        sample_records = df.head(5).to_dict(orient="records")

        return DatasetSummary(
            file_path=str(file_path.resolve()),
            file_size_mb=file_size_mb,
            rows=len(df),
            columns_count=len(columns),
            columns=columns,
            column_types=column_types,
            missing_values=missing_values,
            has_fraud_label=has_fraud_label,
            fraud_label_column=fraud_col_name,
            fraud_distribution=fraud_distribution,
            encoding_used=encoding,
            sample_records=sample_records,
        )

    @staticmethod
    def print_summary(summary: DatasetSummary) -> None:
        """Renders an attractive, readable terminal report of dataset metadata."""
        separator = "=" * 70
        print(f"\n{separator}")
        print(f"  FRAUDSHIELD AI — DATASET INSPECTION REPORT")
        print(f"{separator}")
        print(f"  File Path      : {summary.file_path}")
        print(f"  File Size      : {summary.file_size_mb} MB")
        print(f"  Encoding Used  : {summary.encoding_used}")
        print(f"  Dimensions     : {summary.rows:,} rows x {summary.columns_count} columns")
        print(f"{separator}")
        print("  COLUMNS & DATA TYPES:")
        for col in summary.columns:
            dtype = summary.column_types[col]
            nulls = summary.missing_values.get(col, 0)
            null_info = f"({nulls} nulls)" if nulls > 0 else "(no nulls)"
            print(f"    • {col:<25} : {dtype:<12} {null_info}")

        print(f"{separator}")
        if summary.has_fraud_label:
            print(f"  GROUND TRUTH FRAUD LABELS: DETECTED (Column: '{summary.fraud_label_column}')")
            print("  Class Distribution:")
            for val, count in (summary.fraud_distribution or {}).items():
                pct = (count / summary.rows) * 100 if summary.rows > 0 else 0.0
                label_desc = "Fraud / Suspicious" if str(val) in ["1", "True", "true"] else "Normal / Legitimate"
                print(f"    - Value {val} ({label_desc}): {count:,} ({pct:.2f}%)")
        else:
            print("  GROUND TRUTH FRAUD LABELS: NONE DETECTED")
            print("  Note: Unsupervised Anomaly Detection (Isolation Forest) will be used")
            print("        to identify outliers without requiring historical fraud labels.")

        print(f"{separator}")
        print("  SAMPLE RECORDS (FIRST 2):")
        for i, rec in enumerate(summary.sample_records[:2], start=1):
            print(f"    [Record #{i}]: {rec}")
        print(f"{separator}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FraudShield AI Dataset Loader & Inspector")
    parser.add_argument("--path", type=str, default=None, help="Path to transaction CSV file")
    parser.add_argument("--preview", type=int, default=None, help="Limit number of rows to preview")
    args = parser.parse_args()

    loader = DatasetLoader()
    try:
        _, summary = loader.load_dataset(file_path=args.path, nrows=args.preview)
        loader.print_summary(summary)
    except FileNotFoundError as e:
        print(f"\n[ERROR] Dataset Missing:\n{e}\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to load dataset: {e}\n")
