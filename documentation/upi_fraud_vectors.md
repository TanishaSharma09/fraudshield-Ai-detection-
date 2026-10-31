# UPI & Digital Payment Fraud Vectors Explained

This document outlines the fraud modalities simulated and detected by FraudShield AI:

### 1. Velocity Burst (Rapid Sequential Drain)
- **Mechanism**: The attacker initiates multiple small-to-mid transactions within a very narrow window (e.g. 5 transactions in under 2 minutes) to empty an account before the user notices SMS alerts.
- **Detection Feature**: `velocity_15m` (transaction count in past 15 minutes) and timestamp differential.

### 2. SIM Swap & Unrecognized Device Hijack
- **Mechanism**: An attacker takes over the victim's SIM or credentials and logs in from a brand new device hardware ID, immediately issuing high-value fund transfers.
- **Detection Feature**: `is_new_device` flag combined with `amount_to_avg_ratio > 5.0`.

### 3. Mule Account Fan-Out / Funneling
- **Mechanism**: Stolen funds are routed to newly created "mule" VPAs with low historical reputation, often at irregular hours.
- **Detection Feature**: `is_new_recipient` and `payee_risk_entropy`.

### 4. Midnight Anomaly (Off-Peak Exploit)
- **Mechanism**: Unauthorized transfers executed between 01:00 AM and 05:00 AM when victims are asleep and less likely to block cards or report to banks.
- **Detection Feature**: `is_unusual_hour`.
