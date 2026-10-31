"""FraudShield AI - Reusable Preprocessing & Feature Engineering Pipeline.

Provides clean, leak-free feature extraction for both batch training and real-time inference:
- Strict temporal causality: historical features only use data available *prior* to transaction time.
- Missing and duplicate record handling.
- Input validation (validates positive amounts, well-formed VPAs).
- Behavioural feature engineering:
    * Amount deviation (ratio and absolute difference from rolling historical mean)
    * Velocity (transaction counts in trailing 15-minute window)
    * Time delta (hours elapsed since user's previous transaction)
    * New recipient indicator (unseen payee VPA)
    * New device indicator (unseen hardware signature)
    * Temporal anomaly (off-peak midnight hour flag: 01:00 - 05:00 AM)
- One-hot categorical encoding for payment channels.
- Robust numerical scaling (using median and IQR via Scikit-Learn RobustScaler).
- Serialisation via joblib for identical training and real-time production transforms.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

# Channels known to the system
KNOWN_CHANNELS = ["UPI_APP", "QR_CODE", "INTENT_FLOW", "COLLECT_REQUEST"]

# Final feature columns selected for model ingestion (in strict deterministic order)
FEATURE_COLUMNS = [
    "amount_scaled",
    "amount_to_avg_ratio_scaled",
    "amount_diff_scaled",
    "velocity_15m_scaled",
    "time_since_last_tx_scaled",
    "is_new_device",
    "is_new_recipient",
    "is_unusual_hour",
    "hour_of_day_norm",
    "channel_UPI_APP",
    "channel_QR_CODE",
    "channel_INTENT_FLOW",
    "channel_COLLECT_REQUEST",
]

# Continuous features passed to RobustScaler
NUMERICAL_SCALE_COLS = [
    "amount",
    "amount_to_avg_ratio",
    "amount_diff",
    "velocity_15m",
    "time_since_last_tx",
]


@dataclass
class PreprocessedData:
    """Holds processed feature matrices and labels."""
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series | None
    y_test: pd.Series | None
    feature_names: list[str]


class FraudShieldPreprocessor:
    """Production-grade, leak-free preprocessing and feature transformer."""

    def __init__(self) -> None:
        self.scaler = RobustScaler()
        self.is_fitted = False
        self.population_mean_amount = 2500.0
        self.population_std_amount = 1200.0
        self.feature_names = list(FEATURE_COLUMNS)

    def clean_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates inputs, handles duplicates, drops invalid amounts, and parses timestamps."""
        df_clean = df.copy()

        # 1. Drop duplicates based on unique tx_id if present
        if "tx_id" in df_clean.columns:
            df_clean = df_clean.drop_duplicates(subset=["tx_id"], keep="first")

        # 2. Validate and clean amount (must be positive and <= NPCI limit)
        if "amount" in df_clean.columns:
            df_clean = df_clean[df_clean["amount"] > 0]
            df_clean = df_clean[df_clean["amount"] <= 100000.0]

        # 3. Clean VPA strings
        for col in ["sender_upi", "receiver_upi"]:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()

        # 4. Parse timestamp and sort chronologically for leak-free sequential processing
        if "timestamp" in df_clean.columns:
            df_clean["timestamp_dt"] = pd.to_datetime(df_clean["timestamp"], utc=True)
            df_clean = df_clean.sort_values("timestamp_dt").reset_index(drop=True)

        return df_clean

    def engineer_batch_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts behavioral features with STRICT causal history (ZERO future leakage)."""
        df_clean = self.clean_raw_data(df)
        total_rows = len(df_clean)

        # Stateful in-memory tracking of sender history
        # sender_history[vpa] = {
        #    'amounts': list[float],
        #    'timestamps': list[datetime],
        #    'devices': set[str],
        #    'recipients': set[str]
        # }
        sender_history: dict[str, dict[str, Any]] = {}

        engineered_rows: list[dict[str, Any]] = []

        for _, row in df_clean.iterrows():
            sender = row.get("sender_upi", "unknown@upi")
            receiver = row.get("receiver_upi", "unknown@upi")
            amt = float(row.get("amount", 0.0))
            device = str(row.get("device_id", "DEV-UNKNOWN"))
            channel = str(row.get("channel", "UPI_APP")).upper()
            ts: datetime = row["timestamp_dt"]

            # Initialize history structure if user seen for the first time
            if sender not in sender_history:
                sender_history[sender] = {
                    "amounts": [],
                    "timestamps": [],
                    "devices": set(),
                    "recipients": set(),
                }

            user_state = sender_history[sender]
            prior_amounts = user_state["amounts"]
            prior_timestamps = user_state["timestamps"]
            prior_devices = user_state["devices"]
            prior_recipients = user_state["recipients"]

            # --- 1. Historical Statistics strictly BEFORE this transaction ---
            if len(prior_amounts) > 0:
                user_hist_mean = float(np.mean(prior_amounts))
                user_hist_std = float(np.std(prior_amounts)) if len(prior_amounts) > 1 else 500.0
            else:
                # Use dataset baseline if provided in row, else population prior
                user_hist_mean = float(row.get("user_avg_amount", self.population_mean_amount))
                user_hist_std = self.population_std_amount

            amount_to_avg_ratio = amt / max(10.0, user_hist_mean)
            amount_diff = amt - user_hist_mean

            # --- 2. Time Since Last Transaction & 15-Minute Velocity ---
            if len(prior_timestamps) > 0:
                last_ts = prior_timestamps[-1]
                time_diff_sec = max(0.0, (ts - last_ts).total_seconds())
                time_since_last_tx = min(720.0, time_diff_sec / 3600.0)  # Capped at 30 days in hours

                # Count prior transactions within trailing 15 minutes (900 seconds)
                recent_15m = sum(1 for past_ts in prior_timestamps if (ts - past_ts).total_seconds() <= 900)
                velocity_15m = recent_15m + 1  # Including current tx
            else:
                time_since_last_tx = 72.0  # Cold-start prior: 3 days
                velocity_15m = int(row.get("velocity_15m", 1))

            # --- 3. New Recipient & New Device Flags ---
            is_new_recipient = 1 if (len(prior_recipients) > 0 and receiver not in prior_recipients) else (
                0 if len(prior_recipients) > 0 else 0
            )
            # Check row-level override from dataset generator if present
            if "is_new_device" in row:
                is_new_device = int(row["is_new_device"])
            else:
                is_new_device = 1 if (len(prior_devices) > 0 and device not in prior_devices) else 0

            # --- 4. Temporal Features ---
            hour = ts.hour
            is_unusual_hour = 1 if hour in [1, 2, 3, 4] else 0
            hour_norm = hour / 23.0

            # Store engineered feature row
            eng_row = {
                "amount": amt,
                "amount_to_avg_ratio": amount_to_avg_ratio,
                "amount_diff": amount_diff,
                "velocity_15m": float(velocity_15m),
                "time_since_last_tx": time_since_last_tx,
                "is_new_device": float(is_new_device),
                "is_new_recipient": float(is_new_recipient),
                "is_unusual_hour": float(is_unusual_hour),
                "hour_of_day_norm": float(hour_norm),
                "channel_UPI_APP": 1.0 if channel == "UPI_APP" else 0.0,
                "channel_QR_CODE": 1.0 if channel == "QR_CODE" else 0.0,
                "channel_INTENT_FLOW": 1.0 if channel == "INTENT_FLOW" else 0.0,
                "channel_COLLECT_REQUEST": 1.0 if channel == "COLLECT_REQUEST" else 0.0,
            }

            # Preserve labels / metadata if present
            if "is_fraud" in row:
                eng_row["is_fraud"] = int(row["is_fraud"])
            if "tx_id" in row:
                eng_row["tx_id"] = str(row["tx_id"])
            if "timestamp" in row:
                eng_row["timestamp"] = str(row["timestamp"])

            engineered_rows.append(eng_row)

            # --- UPDATE STATE: Append CURRENT transaction to user history ---
            user_state["amounts"].append(amt)
            user_state["timestamps"].append(ts)
            user_state["devices"].add(device)
            user_state["recipients"].add(receiver)

        return pd.DataFrame(engineered_rows)

    def fit(self, df: pd.DataFrame) -> "FraudShieldPreprocessor":
        """Fits the numerical RobustScaler on the training dataset."""
        df_engineered = self.engineer_batch_features(df)
        self.population_mean_amount = float(df_engineered["amount"].mean())
        self.population_std_amount = float(df_engineered["amount"].std())

        # Fit RobustScaler on continuous columns
        self.scaler.fit(df_engineered[NUMERICAL_SCALE_COLS])
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms an engineered dataframe using fitted scalers."""
        if not self.is_fitted:
            raise RuntimeError("FraudShieldPreprocessor must be fitted before calling transform().")

        df_engineered = self.engineer_batch_features(df)
        scaled_matrix = self.scaler.transform(df_engineered[NUMERICAL_SCALE_COLS])

        out_df = pd.DataFrame()
        out_df["amount_scaled"] = scaled_matrix[:, 0]
        out_df["amount_to_avg_ratio_scaled"] = scaled_matrix[:, 1]
        out_df["amount_diff_scaled"] = scaled_matrix[:, 2]
        out_df["velocity_15m_scaled"] = scaled_matrix[:, 3]
        out_df["time_since_last_tx_scaled"] = scaled_matrix[:, 4]

        # Copy non-scaled binary / normalized features
        for col in [
            "is_new_device",
            "is_new_recipient",
            "is_unusual_hour",
            "hour_of_day_norm",
            "channel_UPI_APP",
            "channel_QR_CODE",
            "channel_INTENT_FLOW",
            "channel_COLLECT_REQUEST",
        ]:
            out_df[col] = df_engineered[col].values

        # Ensure exact deterministic column order
        out_df = out_df[self.feature_names]

        # Carry target label if present
        if "is_fraud" in df_engineered.columns:
            out_df["is_fraud"] = df_engineered["is_fraud"].values
        if "tx_id" in df_engineered.columns:
            out_df["tx_id"] = df_engineered["tx_id"].values

        return out_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fits scalers and transforms the dataframe in one pass."""
        return self.fit(df).transform(df)

    def transform_single(
        self,
        tx: dict[str, Any],
        user_profile: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """Transforms a single incoming UPI transaction for real-time inference.

        Args:
            tx: Incoming transaction dictionary (amount, channel, device_id, timestamp, etc.)
            user_profile: Historical profile from database (avg_amount, known_devices, etc.)

        Returns:
            2D numpy array of shape (1, len(FEATURE_COLUMNS)) ready for model prediction.
        """
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted before live inference.")

        amt = float(tx.get("amount", 0.0))
        channel = str(tx.get("channel", "UPI_APP")).upper()
        device = str(tx.get("device_id", "DEV-UNKNOWN"))
        receiver = str(tx.get("receiver_upi", "")).strip().lower()

        # Parse timestamp or default to current time
        ts_val = tx.get("timestamp")
        if ts_val:
            try:
                dt = pd.to_datetime(ts_val, utc=True)
            except Exception:
                dt = datetime.now()
        else:
            dt = datetime.now()

        # Extract baseline statistics
        profile = user_profile or {}
        user_avg = float(profile.get("avg_amount", self.population_mean_amount))
        known_devices = profile.get("known_devices", [])
        known_recipients = profile.get("known_recipients", [])

        amount_to_avg_ratio = amt / max(10.0, user_avg)
        amount_diff = amt - user_avg

        # Dynamic velocity or default
        velocity_15m = float(tx.get("velocity_15m", 1.0))
        time_since_last_tx = float(tx.get("time_since_last_tx", 24.0))

        # Flags
        is_new_device = 1.0 if (len(known_devices) > 0 and device not in known_devices) else (
            1.0 if "NEW" in device.upper() else 0.0
        )
        is_new_recipient = 1.0 if (len(known_recipients) > 0 and receiver not in known_recipients) else 0.0
        hour = dt.hour
        is_unusual_hour = 1.0 if hour in [1, 2, 3, 4] else 0.0
        hour_norm = hour / 23.0

        # Scale continuous numerical features using the fitted scaler
        num_df = pd.DataFrame(
            [[amt, amount_to_avg_ratio, amount_diff, velocity_15m, time_since_last_tx]],
            columns=NUMERICAL_SCALE_COLS,
        )
        scaled_num = self.scaler.transform(num_df)[0]

        feature_vector = [
            scaled_num[0],       # amount_scaled
            scaled_num[1],       # amount_to_avg_ratio_scaled
            scaled_num[2],       # amount_diff_scaled
            scaled_num[3],       # velocity_15m_scaled
            scaled_num[4],       # time_since_last_tx_scaled
            is_new_device,
            is_new_recipient,
            is_unusual_hour,
            hour_norm,
            1.0 if channel == "UPI_APP" else 0.0,
            1.0 if channel == "QR_CODE" else 0.0,
            1.0 if channel == "INTENT_FLOW" else 0.0,
            1.0 if channel == "COLLECT_REQUEST" else 0.0,
        ]

        return np.array([feature_vector], dtype=np.float64)

    def split_dataset(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        temporal: bool = True,
    ) -> PreprocessedData:
        """Splits raw dataset into leak-free train and test feature matrices.

        When temporal=True (default), sorts by timestamp and uses the earlier (1-test_size)
        fraction for training and the chronologically subsequent fraction for testing,
        preventing lookahead bias.
        """
        df_clean = self.clean_raw_data(df)

        if temporal:
            split_idx = int(len(df_clean) * (1.0 - test_size))
            train_raw = df_clean.iloc[:split_idx].copy()
            test_raw = df_clean.iloc[split_idx:].copy()
        else:
            from sklearn.model_selection import train_test_split
            stratify_col = df_clean["is_fraud"] if "is_fraud" in df_clean.columns else None
            train_raw, test_raw = train_test_split(
                df_clean, test_size=test_size, random_state=42, stratify=stratify_col
            )

        # Fit preprocessor strictly on TRAIN split to prevent data leakage
        self.fit(train_raw)

        # Transform both splits using parameters fitted strictly on train
        train_processed = self.transform(train_raw)
        test_processed = self.transform(test_raw)

        y_train = train_processed["is_fraud"] if "is_fraud" in train_processed.columns else None
        y_test = test_processed["is_fraud"] if "is_fraud" in test_processed.columns else None

        X_train = train_processed[self.feature_names]
        X_test = test_processed[self.feature_names]

        return PreprocessedData(
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            feature_names=self.feature_names,
        )

    def save(self, file_path: str | Path) -> None:
        """Serialises the preprocessor instance to disk using joblib."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target)

    @classmethod
    def load(cls, file_path: str | Path) -> "FraudShieldPreprocessor":
        """Loads a persisted preprocessor instance from disk."""
        target = Path(file_path)
        if not target.exists():
            raise FileNotFoundError(f"Preprocessor artifact not found at: {target.resolve()}")
        obj = joblib.load(target)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded artifact is not a {cls.__name__}")
        return obj
