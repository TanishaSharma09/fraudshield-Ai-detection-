"""FraudShield AI - Preprocessing Pipeline Runner.

Applies the leak-free FraudShieldPreprocessor on the active UPI dataset,
persists the fitted preprocessor artifact, and outputs train/test splits.
"""

from pathlib import Path
from dataset.loader import DatasetLoader
from ml_model.features.preprocessor import FraudShieldPreprocessor


def run_pipeline(
    raw_dataset_path: str | Path = "dataset/raw/upi_transactions.csv",
    saved_preprocessor_path: str | Path = "ml_model/saved_models/preprocessor.joblib",
    processed_dir: str | Path = "dataset/processed",
    test_size: float = 0.2,
) -> None:
    """Executes the full preprocessing and feature engineering pipeline."""
    print("=" * 60)
    print("  FRAUDSHIELD AI — RUNNING PREPROCESSING PIPELINE")
    print("=" * 60)

    # 1. Load Raw Dataset
    loader = DatasetLoader()
    print(f"Loading raw dataset from: {raw_dataset_path}")
    df_raw, summary = loader.load_dataset(file_path=raw_dataset_path)
    print(f"Loaded {len(df_raw):,} raw records with {summary.columns_count} columns.")

    # 2. Initialize Preprocessor & Execute Leak-Free Split
    preprocessor = FraudShieldPreprocessor()
    print(f"Splitting chronologically into Train ({(1-test_size)*100:.0f}%) and Test ({test_size*100:.0f}%)...")
    split_data = preprocessor.split_dataset(df_raw, test_size=test_size, temporal=True)

    print(f"Train features shape : {split_data.X_train.shape}")
    print(f"Test features shape  : {split_data.X_test.shape}")
    if split_data.y_train is not None:
        print(f"Train fraud count    : {split_data.y_train.sum()} ({split_data.y_train.mean()*100:.2f}%)")
        print(f"Test fraud count     : {split_data.y_test.sum()} ({split_data.y_test.mean()*100:.2f}%)")

    # 3. Save Fitted Preprocessor Artifact
    prep_dest = Path(saved_preprocessor_path)
    prep_dest.parent.mkdir(parents=True, exist_ok=True)
    preprocessor.save(prep_dest)
    print(f"Fitted preprocessor artifact saved to: {prep_dest.resolve()}")

    # 4. Save Processed Train/Test Datasets
    p_dir = Path(processed_dir)
    p_dir.mkdir(parents=True, exist_ok=True)

    split_data.X_train.to_csv(p_dir / "train_features.csv", index=False)
    split_data.X_test.to_csv(p_dir / "test_features.csv", index=False)
    if split_data.y_train is not None:
        split_data.y_train.to_csv(p_dir / "train_labels.csv", index=False)
    if split_data.y_test is not None:
        split_data.y_test.to_csv(p_dir / "test_labels.csv", index=False)

    print(f"Processed feature matrices saved to: {p_dir.resolve()}")
    print("=" * 60)
    print("  PREPROCESSING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
