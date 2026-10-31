"""FraudShield AI - Synthetic UPI & Digital Payment Dataset Generator.

Generates realistic Indian UPI digital payment transactions following NPCI behavioural
patterns, retail spending distributions, and verified cyber-fraud attack vectors:
1. Normal Retail / P2P Spending (Log-normal distribution, daytime active hours)
2. Velocity Burst / Rapid Drain (Multiple sequential payments in short time windows)
3. SIM Swap & Unrecognised Device Surge (New hardware IMEI, off-peak hours, high amount)
4. Collect Request Phishing (Victim deceived by collect request approvals)
5. Mule Account Fan-Out (Stolen funds funnelled into fresh high-entropy VPAs)

All generated records strictly adhere to the NPCI ₹1,00,000 standard daily transaction limit.
"""

import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

# Indian Banks and Payment Service Provider Handles
UPI_HANDLES = ["okaxis", "okhdfcbank", "paytm", "icici", "ybl", "oksbi", "barodampay"]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad",
    "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Surat", "Indore"
]

PAYMENT_CHANNELS = ["UPI_APP", "QR_CODE", "INTENT_FLOW", "COLLECT_REQUEST"]

DEVICE_BRANDS = [
    "DEV-XIAOMI-12", "DEV-SAMSUNG-S23", "DEV-ONEPLUS-11",
    "DEV-IPHONE-15", "DEV-REALME-GT", "DEV-VIVO-V29", "DEV-PIXEL-8"
]


class UPIDataGenerator:
    """Configurable synthetic UPI transaction dataset generator."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        self._init_entities()

    def _init_entities(self) -> None:
        """Pre-seeds realistic user profiles and merchant handles."""
        first_names = [
            "arjun", "priya", "rahul", "sneha", "vikram", "ananya", "rohit",
            "pooja", "aditya", "kavita", "manoj", "divya", "suresh", "deepa",
            "karan", "neha", "amit", "meera", "rajesh", "sunita"
        ]
        last_names = [
            "sharma", "verma", "kumar", "patel", "singh", "reddy", "gupta",
            "joshi", "nair", "rao", "deshmukh", "mishra", "bose", "chatterjee"
        ]

        # Generate 150 unique sender profiles with baselines
        self.senders = []
        for i in range(150):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            handle = random.choice(UPI_HANDLES)
            vpa = f"{fn}.{ln}{i+1}@{handle}"
            primary_device = random.choice(DEVICE_BRANDS)
            primary_city = random.choice(INDIAN_CITIES)
            mean_amount = float(np.random.choice([850, 1500, 2400, 3800, 5200]))
            std_amount = round(mean_amount * random.uniform(0.3, 0.5), 2)
            self.senders.append({
                "vpa": vpa,
                "primary_device": primary_device,
                "primary_city": primary_city,
                "mean_amount": mean_amount,
                "std_amount": std_amount,
            })

        # Generate 60 verified merchant VPAs
        merchants = [
            "swiggy.pay", "zomato.order", "amazon.pay", "flipkart.checkout",
            "dmart.supermarket", "reliance.retail", "uber.rides", "ola.cabs",
            "apollo.pharmacy", "irctc.tickets", "tata.neu", "bigbasket.order"
        ]
        self.merchants = [f"{m}@{random.choice(UPI_HANDLES)}" for m in merchants]

        # Generate 15 flagged suspicious mule VPAs
        self.mule_vpas = [
            f"fast.cash.transfer{i}@{random.choice(['ybl', 'paytm'])}" for i in range(1, 16)
        ]

    def generate_dataset(
        self,
        n_samples: int = 12000,
        fraud_ratio: float = 0.035,
        start_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Generates a DataFrame of synthetic UPI transactions."""
        if start_date is None:
            start_date = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

        n_fraud = int(n_samples * fraud_ratio)
        n_normal = n_samples - n_fraud

        records: list[dict] = []

        # 1. Generate Normal Transactions
        current_time = start_date
        for i in range(n_normal):
            sender = random.choice(self.senders)
            receiver = (
                random.choice(self.merchants)
                if random.random() < 0.65
                else random.choice(self.senders)["vpa"]
            )
            # Avoid self-transfer
            if receiver == sender["vpa"]:
                receiver = random.choice(self.merchants)

            # Normal retail amount: log-normal distribution centered near user baseline
            amount = round(float(np.random.lognormal(
                mean=np.log(sender["mean_amount"]),
                sigma=0.45,
            )), 2)
            # Clip between ₹10 and ₹35,000 for normal consumer payments
            amount = float(np.clip(amount, 10.0, 35000.0))

            # Daytime preference: 85% between 08:00 and 23:00
            if random.random() < 0.85:
                hour = random.randint(8, 22)
            else:
                hour = random.choice([6, 7, 23, 0])
            minute = random.randint(0, 59)
            second = random.randint(0, 59)

            tx_time = current_time + timedelta(
                days=random.randint(0, 27),
                hours=hour,
                minutes=minute,
                seconds=second,
            )

            channel = np.random.choice(
                PAYMENT_CHANNELS,
                p=[0.45, 0.35, 0.15, 0.05],  # Collect request is naturally rare in normal usage
            )

            records.append({
                "tx_id": f"UPI-{tx_time.strftime('%Y%m%d')}-{i+100000:06d}",
                "timestamp": tx_time.isoformat(),
                "sender_upi": sender["vpa"],
                "receiver_upi": receiver,
                "amount": amount,
                "channel": channel,
                "device_id": sender["primary_device"],
                "location_city": sender["primary_city"],
                "user_avg_amount": sender["mean_amount"],
                "is_new_device": 0,
                "velocity_15m": random.choice([1, 1, 1, 1, 2, 2, 3]),
                "is_fraud": 0,
                "fraud_scenario": "NORMAL_TRANSACTION",
            })

        # 2. Generate Fraud Scenarios
        fraud_scenarios = [
            "VELOCITY_BURST",
            "SIM_SWAP_DEVICE_CHANGE",
            "MIDNIGHT_HIGH_VALUE_DRAIN",
            "COLLECT_REQUEST_PHISHING",
            "MULE_ACCOUNT_FANOUT",
        ]

        for j in range(n_fraud):
            scenario = random.choice(fraud_scenarios)
            sender = random.choice(self.senders)
            tx_time = start_date + timedelta(
                days=random.randint(0, 27),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            if scenario == "VELOCITY_BURST":
                # Multiple rapid transfers just under limits
                receiver = random.choice(self.mule_vpas)
                amount = round(random.uniform(8000.0, 25000.0), 2)
                device_id = sender["primary_device"]
                city = sender["primary_city"]
                channel = "UPI_APP"
                is_new_device = 0
                velocity = random.randint(5, 12)

            elif scenario == "SIM_SWAP_DEVICE_CHANGE":
                # Unrecognised device draining high sum
                receiver = random.choice(self.mule_vpas)
                amount = round(random.uniform(45000.0, 98000.0), 2)
                device_id = "DEV-SUSPICIOUS-NEW-HARDWARE"
                city = random.choice([c for c in INDIAN_CITIES if c != sender["primary_city"]])
                channel = "INTENT_FLOW"
                is_new_device = 1
                velocity = random.randint(3, 7)

            elif scenario == "MIDNIGHT_HIGH_VALUE_DRAIN":
                # Off-peak transfer at 2:00 AM - 4:00 AM
                receiver = random.choice(self.mule_vpas)
                amount = round(random.uniform(50000.0, 95000.0), 2)
                tx_time = tx_time.replace(hour=random.choice([1, 2, 3, 4]))
                device_id = sender["primary_device"]
                city = sender["primary_city"]
                channel = "UPI_APP"
                is_new_device = random.choice([0, 1])
                velocity = random.randint(2, 6)

            elif scenario == "COLLECT_REQUEST_PHISHING":
                # Phishing collect request tricked into approval
                receiver = f"unverified.merchant{j}@{random.choice(['ybl', 'paytm'])}"
                amount = round(random.uniform(15000.0, 60000.0), 2)
                device_id = sender["primary_device"]
                city = sender["primary_city"]
                channel = "COLLECT_REQUEST"
                is_new_device = 0
                velocity = 2

            else:  # MULE_ACCOUNT_FANOUT
                # Splitting funds to mule
                receiver = random.choice(self.mule_vpas)
                amount = round(random.uniform(35000.0, 85000.0), 2)
                device_id = "DEV-UNRECOGNISED-EMULATOR"
                city = random.choice(INDIAN_CITIES)
                channel = "INTENT_FLOW"
                is_new_device = 1
                velocity = random.randint(4, 9)

            records.append({
                "tx_id": f"UPI-{tx_time.strftime('%Y%m%d')}-{n_normal+j+100000:06d}",
                "timestamp": tx_time.isoformat(),
                "sender_upi": sender["vpa"],
                "receiver_upi": receiver,
                "amount": amount,
                "channel": channel,
                "device_id": device_id,
                "location_city": city,
                "user_avg_amount": sender["mean_amount"],
                "is_new_device": is_new_device,
                "velocity_15m": velocity,
                "is_fraud": 1,
                "fraud_scenario": scenario,
            })

        # Shuffle records to eliminate ordering bias
        df = pd.DataFrame(records)
        df = df.sample(frac=1.0, random_state=self.seed).reset_index(drop=True)
        return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Synthetic UPI Payments Dataset")
    parser.add_argument("--samples", type=int, default=12000, help="Total number of transaction records")
    parser.add_argument("--fraud-ratio", type=float, default=0.035, help="Proportion of fraudulent transactions")
    parser.add_argument("--output", type=str, default="dataset/raw/upi_transactions.csv", help="Destination CSV path")
    args = parser.parse_args()

    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.samples:,} synthetic UPI transactions (Fraud Ratio: {args.fraud_ratio*100:.1f}%)...")
    generator = UPIDataGenerator()
    df_generated = generator.generate_dataset(n_samples=args.samples, fraud_ratio=args.fraud_ratio)
    df_generated.to_csv(dest, index=False)
    print(f"Dataset successfully created at: {dest.resolve()}")
    print(f"Shape: {df_generated.shape[0]:,} rows x {df_generated.shape[1]} columns")
    print(f"Fraud distribution:\n{df_generated['is_fraud'].value_counts().to_dict()}")
