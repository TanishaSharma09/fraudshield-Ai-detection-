# FraudShield AI — Exploratory Data Analysis & Visualisation Findings

This report documents the empirical patterns, statistical distributions, and fraud indicators identified from the transaction dataset. All figures are persisted in high resolution (`300 DPI`) in the [`documentation/figures/`](file:///d:/new%20project/documentation/figures/) directory.

---

## 1. Visual Asset Index

| Figure ID | File Name | Primary Feature / Analytical Dimension | Key Takeaway |
| :--- | :--- | :--- | :--- |
| **Figure 1** | [`01_amount_distribution.png`](file:///d:/new%20project/documentation/figures/01_amount_distribution.png) | Transaction Amount (Linear & Log scale) | Legitimate transfers cluster around ₹1,000–₹3,500; fraud concentrates above ₹45,000. |
| **Figure 2** | [`02_fraud_vs_legit_distribution.png`](file:///d:/new%20project/documentation/figures/02_fraud_vs_legit_distribution.png) | Ground Truth Class Balance | Severe class imbalance (**3.50% Fraud / 96.50% Legit**), necessitating anomaly detection. |
| **Figure 3** | [`03_transaction_type_distribution.png`](file:///d:/new%20project/documentation/figures/03_transaction_type_distribution.png) | Payment Channel Breakdown | `COLLECT_REQUEST` exhibits the highest fraud rate (**~12.4%**), followed by `INTENT_FLOW`. |
| **Figure 4** | [`04_transaction_frequency_analysis.png`](file:///d:/new%20project/documentation/figures/04_transaction_frequency_analysis.png) | 15-Minute Rolling Velocity | Normal users rarely exceed 2 txs/15m; fraud spikes from 5 to 12 rapid bursts. |
| **Figure 5** | [`05_correlation_heatmap.png`](file:///d:/new%20project/documentation/figures/05_correlation_heatmap.png) | Spearman Rank Correlation Matrix | Strongest fraud correlations: `amount` (+0.58), `velocity_15m` (+0.44), `is_new_device` (+0.39). |
| **Figure 6** | [`06_time_based_patterns.png`](file:///d:/new%20project/documentation/figures/06_time_based_patterns.png) | 24-Hour Diurnal Density | Normal traffic peaks 09:00–22:00; fraud clusters disproportionately during 01:00–05:00 AM. |
| **Figure 7** | [`07_outlier_analysis.png`](file:///d:/new%20project/documentation/figures/07_outlier_analysis.png) | Boxplots & 1.5x IQR Outliers | Demonstrates clear separation of multivariate fraud outliers beyond the 1.5x IQR threshold. |
| **Overview** | [`eda_summary_dashboard.png`](file:///d:/new%20project/documentation/figures/eda_summary_dashboard.png) | 4-Panel Executive Overview | Consolidated executive dashboard combining amount, channel, velocity, and hourly trends. |

---

## 2. In-Depth Empirical Findings

### Finding A: Amount Bimodality & Extreme Positive Skew
- **Legitimate Payments**: Follow a log-normal distribution with median **₹2,582.68** and interquartile range (IQR) spanning ₹1,432 to ₹4,654.
- **Fraudulent Payments**: Mean **₹51,825.61**, clustering in the upper decile (near the ₹1,00,000 NPCI daily limit).
- **Implication**: Raw monetary amount is the single strongest univariate indicator, but standard scaling is heavily distorted by extreme values (+5.94 skewness). `RobustScaler` (median & IQR) is strictly required.

### Finding B: Collect Request Vulnerability
- Although `QR_CODE` and `UPI_APP` represent **78.3%** of all payment transactions, they exhibit a combined fraud rate of under 2.1%.
- Conversely, `COLLECT_REQUEST` accounts for only **5.38%** of total payment volume but carries **~12.4%** fraud incidence. In India, collect requests are routinely weaponized by scammers tricking users into entering PINs under the guise of receiving lottery prizes or buyer deposits.
- **Implication**: One-hot encoding of `channel_COLLECT_REQUEST` provides a strong categorical weighting factor for risk calibration.

### Finding C: 15-Minute Rolling Velocity as an Automated Attack Signature
- 98.4% of legitimate users perform **1 or 2 transactions** within any 15-minute window.
- In contrast, automated draining scripts and account takeovers repeatedly attempt transactions: **velocity values of 5 to 12** occur almost exclusively within the fraudulent cohort.
- **Implication**: When velocity $\ge 4$, anomaly tree decision path lengths collapse rapidly in Isolation Forest, driving risk scores above 80.

### Finding D: Diurnal Separation (The Midnight Danger Zone)
- Legitimate consumer spending plummets past 23:00 and reaches its absolute nadir between 02:00 and 04:30 AM (accounting for less than 1.2% of normal volume).
- Cyber-fraud incidents show elevated frequency during these exact off-peak hours (accounting for 33.3% of all fraud occurrences). Attackers deliberately leverage nighttime windows to minimize immediate victim notification awareness.
- **Implication**: The derived feature `is_unusual_hour` provides an orthogonal temporal signal that enhances anomaly isolation even when transaction amounts are kept intentionally moderate (e.g. ₹9,999).

### Finding E: Correlation Matrix Insights
- `amount` and `is_fraud` have a Spearman rank correlation coefficient of **+0.58**.
- `velocity_15m` and `is_fraud` have a correlation of **+0.44**.
- `is_new_device` and `is_fraud` have a correlation of **+0.39**.
- Multicollinearity between `velocity_15m` and `amount` is low (**+0.12**), indicating that velocity and amount provide **independent, non-redundant fraud signals**.

---

## 3. Modeling Strategy for Phase 3
1. **Unsupervised Anomaly Model**: Isolation Forest will effectively capture the multi-dimensional outliers formed by the interaction of high velocity, new device, and nocturnal hour.
2. **Supervised Baseline (XGBoost)**: Can use the 3.5% labels with `scale_pos_weight = 27.6` to handle class imbalance, providing a rigorous benchmark against Isolation Forest.
3. **Threshold Calibration**: Decision boundaries should set `CRITICAL` alert thresholds at scores $\ge 90$ to prioritize high precision, avoiding SOC analyst alert fatigue.
