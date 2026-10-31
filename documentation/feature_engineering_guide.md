# FraudShield AI — Feature Engineering & Preprocessing Guide

## 1. Overview & Data Leakage Prevention Principles
The feature engineering pipeline transforms raw digital payment attributes into structured behavioral vectors for machine learning anomaly detection. 

### Critical Design Rule: Strict Temporal Causality
To prevent **lookahead data leakage**:
- All historical statistics (rolling mean, prior timestamps, known devices, known recipients) for transaction $i$ are computed **strictly using transactions occurring prior to transaction $i$'s timestamp ($t < t_i$)**.
- The user history state is updated with transaction $i$'s parameters **only after** transaction $i$'s feature row has been computed.
- The `RobustScaler` is fitted **exclusively on the chronologically earlier Training split (80%)** and subsequently applied to the chronologically later Test split (20%) and live production inferences.

---

## 2. Engineered Feature Catalog

The preprocessor outputs a deterministic 13-dimensional feature matrix:

| Feature Name | Source / Formula | Mathematical Range | Fraud Detection Significance |
| :--- | :--- | :--- | :--- |
| **`amount_scaled`** | $\text{RobustScale}(\text{amount})$ | $[-\infty, +\infty]$ | Captures raw financial exposure. Fraud events in UPI frequently target near-limit sums (₹45,000–₹95,000). |
| **`amount_to_avg_ratio_scaled`** | $\text{RobustScale}\left(\frac{\text{amount}}{\max(10, \mu_{\text{user\_hist}})}\right)$ | $[-\infty, +\infty]$ | **Critical Anomaly Signal**: Measures sudden spikes relative to individual financial capacity. A ₹40,000 payment is normal for a corporate user but a 15x anomaly for a student. |
| **`amount_diff_scaled`** | $\text{RobustScale}(\text{amount} - \mu_{\text{user\_hist}})$ | $[-\infty, +\infty]$ | Absolute rupee deviation from customer's personal average. |
| **`velocity_15m_scaled`** | $\text{RobustScale}(\text{tx\_count}_{\text{trailing } 15 \text{ min}})$ | $[-\infty, +\infty]$ | **Automated Drain Signal**: Human users execute 1–2 payments within 15 minutes. Botnets, account takeover scripts, and phishing drains burst 5–12 rapid transfers. |
| **`time_since_last_tx_scaled`** | $\text{RobustScale}(\Delta t_{\text{hours}})$ | $[-\infty, +\infty]$ | Hours elapsed since the user's prior transaction. Identifies sudden bursts after long dormancy (dormant account activation fraud). |
| **`is_new_device`** | $1 \text{ if } \text{device} \notin \text{known\_devices} \text{ else } 0$ | $\{0, 1\}$ | **Hardware Hijack Signal**: Flags SIM swaps, credential theft, and unauthorized web emulators. |
| **`is_new_recipient`** | $1 \text{ if } \text{payee} \notin \text{known\_payees} \text{ else } 0$ | $\{0, 1\}$ | **Mule Routing Signal**: First-time payments to unfamiliar VPAs, especially in high amounts, represent elevated fraud risk. |
| **`is_unusual_hour`** | $1 \text{ if } \text{hour} \in \{1, 2, 3, 4\} \text{ else } 0$ | $\{0, 1\}$ | **Sleep-Hour Drain**: Identifies fraudulent transfers initiated when victims are asleep and unable to notice SMS notifications. |
| **`hour_of_day_norm`** | $\frac{\text{hour}}{23.0}$ | $[0.0, 1.0]$ | Continuous diurnal progression encoding time-of-day dynamics. |
| **`channel_UPI_APP`** | One-hot binary indicator | $\{0, 1\}$ | Standard mobile app initiation (Google Pay, PhonePe, Paytm, BHIM). |
| **`channel_QR_CODE`** | One-hot binary indicator | $\{0, 1\}$ | Offline merchant point-of-sale scanning (statistically lowest fraud rate). |
| **`channel_INTENT_FLOW`** | One-hot binary indicator | $\{0, 1\}$ | E-commerce merchant mobile app redirects. |
| **`channel_COLLECT_REQUEST`** | One-hot binary indicator | $\{0, 1\}$ | **High-Risk Phishing Signal**: Payee initiates a pull request. Widely exploited in OLX/classifieds scams where victims are tricked into entering UPI PINs to "receive money". |

---

## 3. Scaling Strategy: Why `RobustScaler`?
Standard $z$-score normalization ($\frac{x - \mu}{\sigma}$) is vulnerable to extreme financial outliers:
- A single fraud transfer of ₹96,000 dramatically inflates $\mu$ and $\sigma$, compressing normal transfers into a tiny cluster near zero.
- `RobustScaler` centers on the **Median** ($Q_2$) and scales by the **Interquartile Range** ($\text{IQR} = Q_3 - Q_1$):
  $$x_{\text{scaled}} = \frac{x - \text{median}(X)}{\text{IQR}(X)}$$
This preserves non-linear separation for extreme outliers while ensuring standard transactions are not squashed.

---

## 4. Live vs. Batch Equivalence
The preprocessor exposes:
- **`fit_transform(df)`**: For batch historical model training.
- **`transform_single(tx_dict, user_profile)`**: For sub-50ms live scoring in the FastAPI backend.
Both methods utilize identical scaling parameters, numerical clipping, and categorical definitions, guaranteeing **zero train-serving skew**.
