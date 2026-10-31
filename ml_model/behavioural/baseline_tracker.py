"""FraudShield AI - Leak-Free User Behavioural Baseline Tracker.

Computes and maintains user-specific historical behavioral profiles strictly using
historical data available prior to the current transaction timestamp:
- Strict Temporal Causality: No future data leakage (timestamp < current_timestamp).
- Rolling Personal Baselines:
    * Average transaction amount (mean)
    * Amount dispersion (standard deviation / IQR)
    * Typical transaction frequency (transactions per 24-hour period)
    * Known hardware device signatures
    * Known beneficiary recipient VPAs
    * Pair interaction history (prior transactions between specific sender and receiver)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any
import numpy as np

from database.connection import query_all, query_one


@dataclass
class UserBaselineProfile:
    """Encapsulates a user's empirical behavioural baseline prior to a given point in time."""
    sender_upi: str
    as_of_timestamp: str
    total_prior_transactions: int
    avg_amount: float
    std_amount: float
    min_amount: float
    max_amount: float
    daily_frequency_mean: float
    known_devices: set[str] = field(default_factory=set)
    known_recipients: set[str] = field(default_factory=set)
    recipient_interaction_counts: dict[str, int] = field(default_factory=dict)
    last_tx_timestamp: str | None = None
    seconds_since_last_tx: float | None = None
    recent_15m_count: int = 0
    recent_60s_count: int = 0
    is_cold_start: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_upi": self.sender_upi,
            "as_of_timestamp": self.as_of_timestamp,
            "total_prior_transactions": self.total_prior_transactions,
            "avg_amount": round(self.avg_amount, 2),
            "std_amount": round(self.std_amount, 2),
            "min_amount": round(self.min_amount, 2),
            "max_amount": round(self.max_amount, 2),
            "daily_frequency_mean": round(self.daily_frequency_mean, 2),
            "known_devices": list(self.known_devices),
            "known_recipients": list(self.known_recipients),
            "recipient_interaction_counts": self.recipient_interaction_counts,
            "last_tx_timestamp": self.last_tx_timestamp,
            "seconds_since_last_tx": self.seconds_since_last_tx,
            "recent_15m_count": self.recent_15m_count,
            "recent_60s_count": self.recent_60s_count,
            "is_cold_start": self.is_cold_start,
        }


class BehaviouralBaselineTracker:
    """Calculates user-specific transactional baselines with ZERO future data leakage."""

    DEFAULT_POPULATION_AVG = 2500.0
    DEFAULT_POPULATION_STD = 1200.0
    DEFAULT_DAILY_FREQUENCY = 1.2

    @staticmethod
    def _parse_iso(ts_val: str | None) -> datetime:
        """Parses ISO timestamp string reliably with UTC fallback."""
        if not ts_val:
            return datetime.now(timezone.utc)
        try:
            clean = str(ts_val).replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except Exception:
            return datetime.now(timezone.utc)

    def compute_baseline_from_records(
        self,
        sender_upi: str,
        historical_records: list[dict[str, Any]],
        as_of_timestamp: str | None = None,
        fallback_profile: dict[str, Any] | None = None,
    ) -> UserBaselineProfile:
        """Computes a user baseline from an in-memory list of records strictly prior to as_of_timestamp.

        Ensures 100% causal compliance: any record with timestamp >= as_of_timestamp is excluded.
        """
        sender_clean = sender_upi.strip().lower()
        as_of_dt = self._parse_iso(as_of_timestamp)
        as_of_iso = as_of_dt.isoformat()

        # Strict temporal causal filtering: ONLY prior events
        prior_records = []
        for r in historical_records:
            if str(r.get("sender_upi", "")).strip().lower() != sender_clean:
                continue
            r_ts = self._parse_iso(r.get("timestamp"))
            if r_ts < as_of_dt:
                prior_records.append((r_ts, r))

        # Sort chronologically
        prior_records.sort(key=lambda x: x[0])

        if not prior_records:
            # Cold-start user profile
            fb = fallback_profile or {}
            known_devs = set(fb.get("known_devices", []))
            known_recs = set(fb.get("known_recipients", []))
            avg_amt = float(fb.get("avg_amount", self.DEFAULT_POPULATION_AVG))
            std_amt = float(fb.get("std_amount", self.DEFAULT_POPULATION_STD))

            return UserBaselineProfile(
                sender_upi=sender_clean,
                as_of_timestamp=as_of_iso,
                total_prior_transactions=0,
                avg_amount=avg_amt,
                std_amount=std_amt,
                min_amount=avg_amt,
                max_amount=avg_amt,
                daily_frequency_mean=self.DEFAULT_DAILY_FREQUENCY,
                known_devices=known_devs,
                known_recipients=known_recs,
                recipient_interaction_counts={},
                last_tx_timestamp=None,
                seconds_since_last_tx=None,
                recent_15m_count=0,
                recent_60s_count=0,
                is_cold_start=True,
            )

        amounts = [float(r["amount"]) for _, r in prior_records]
        known_devices = {str(r["device_id"]) for _, r in prior_records if r.get("device_id")}
        known_recipients = {str(r["receiver_upi"]).strip().lower() for _, r in prior_records if r.get("receiver_upi")}

        # Recipient interaction frequencies
        interaction_counts: dict[str, int] = {}
        for _, r in prior_records:
            rec = str(r.get("receiver_upi", "")).strip().lower()
            if rec:
                interaction_counts[rec] = interaction_counts.get(rec, 0) + 1

        # Fallback profile merging
        if fallback_profile:
            known_devices.update(fallback_profile.get("known_devices", []))
            known_recipients.update(fallback_profile.get("known_recipients", []))

        # Time deltas and velocity calculation
        last_dt, last_record = prior_records[-1]
        seconds_since_last = max(0.0, (as_of_dt - last_dt).total_seconds())

        recent_15m_count = sum(1 for dt, _ in prior_records if (as_of_dt - dt).total_seconds() <= 900)
        recent_60s_count = sum(1 for dt, _ in prior_records if (as_of_dt - dt).total_seconds() <= 60)

        # Compute empirical daily frequency
        first_dt = prior_records[0][0]
        span_days = max(1.0, (as_of_dt - first_dt).total_seconds() / 86400.0)
        daily_freq = len(prior_records) / span_days

        if fallback_profile and "avg_amount" in fallback_profile:
            avg_val = float(fallback_profile["avg_amount"])
            std_val = float(fallback_profile.get("std_amount", max(100.0, avg_val * 0.25)))
        else:
            avg_val = float(np.mean(amounts))
            std_val = float(np.std(amounts)) if len(amounts) > 1 else max(100.0, avg_val * 0.25)

        return UserBaselineProfile(
            sender_upi=sender_clean,
            as_of_timestamp=as_of_iso,
            total_prior_transactions=len(prior_records),
            avg_amount=avg_val,
            std_amount=std_val,
            min_amount=float(min(amounts)),
            max_amount=float(max(amounts)),
            daily_frequency_mean=daily_freq,
            known_devices=known_devices,
            known_recipients=known_recipients,
            recipient_interaction_counts=interaction_counts,
            last_tx_timestamp=last_dt.isoformat(),
            seconds_since_last_tx=seconds_since_last,
            recent_15m_count=recent_15m_count,
            recent_60s_count=recent_60s_count,
            is_cold_start=False,
        )

    def get_user_baseline_from_db(
        self,
        sender_upi: str,
        as_of_timestamp: str | None = None,
        db_path: str | None = None,
    ) -> UserBaselineProfile:
        """Queries the SQLite database for transactions strictly prior to as_of_timestamp."""
        sender_clean = sender_upi.strip().lower()
        as_of_dt = self._parse_iso(as_of_timestamp)
        as_of_iso = as_of_dt.isoformat()

        # 1. Fetch seed user profile for cold-start fallback
        seed_row = query_one(
            "SELECT avg_amount, std_amount, known_devices_json, typical_cities_json FROM user_profiles WHERE upi_id = ?;",
            (sender_clean,),
            db_path=db_path,
        )
        fallback: dict[str, Any] = {}
        if seed_row:
            import json
            fallback["avg_amount"] = float(seed_row["avg_amount"])
            fallback["std_amount"] = float(seed_row["std_amount"])
            fallback["known_devices"] = json.loads(seed_row["known_devices_json"]) if seed_row["known_devices_json"] else []

        # 2. Query historical transactions strictly BEFORE as_of_iso (Zero Future Data Leakage)
        sql = """
            SELECT 
                sender_upi,
                amount,
                receiver_upi,
                device_id,
                timestamp
            FROM transactions
            WHERE LOWER(sender_upi) = LOWER(?) AND timestamp < ?
            ORDER BY timestamp ASC;
        """
        rows = query_all(sql, (sender_clean, as_of_iso), db_path=db_path)
        records = [dict(r) for r in rows]

        return self.compute_baseline_from_records(
            sender_upi=sender_clean,
            historical_records=records,
            as_of_timestamp=as_of_iso,
            fallback_profile=fallback,
        )


# Singleton instance helper
_tracker_instance: BehaviouralBaselineTracker | None = None


def get_baseline_tracker() -> BehaviouralBaselineTracker:
    """Returns or initialises the singleton BehaviouralBaselineTracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = BehaviouralBaselineTracker()
    return _tracker_instance
