# FraudShield AI — Isolation Forest Model Training & Independent Evaluation Report

---

## 1. Executive Summary & Model Architecture
- **Algorithm**: Scikit-Learn `IsolationForest` (Ensemble of Extremely Randomized Trees)
- **Model Role**: Primary Unsupervised Anomaly Detection Engine
- **Training Paradigm**: **Strictly Unsupervised** — no fraud labels were provided to the algorithm during training.
- **Ensemble Size**: 200 Isolation Trees (`n_estimators=200`)
- **Contamination Hyperparameter**: `0.035` (calibrated against empirical 3.5% outlier proportion from EDA)
- **Feature Matrix Dimension**: 13 features (scaled via leak-free `RobustScaler`)
- **Training Split**: Earlier 80% (9,600 transactions, chronologically ordered)
- **Test Split**: Subsequent 20% (2,400 transactions, chronologically evaluated)

---

## 2. Independent Test Set Evaluation Metrics

Because ground-truth labels exist in the benchmark test set, we conducted an **independent post-training validation**:

| Evaluation Metric | Test Score | Operational Interpretation |
| :--- | :--- | :--- |
| **ROC-AUC Score** | **97.26%** | Exceptional discrimination capability across the entire continuous risk threshold spectrum. |
| **Recall (Sensitivity)** | **82.80%** | Identified **77 out of 93** actual cyber-fraud incidents without supervision. |
| **Precision** | **54.61%** | 77 out of 141 flagged anomalies were confirmed fraud. |
| **F1 Score** | **65.81%** | Harmonic mean balancing recall and precision under severe class imbalance (`1:27.6`). |
| **Mean Risk Score** | **21.62 / 100** | Population baseline is low, reserving high scores for genuine outliers. |

---

## 3. Confusion Matrix Breakdown

```text
                  Predicted Normal (0)    Predicted Anomaly (1)
Actual Normal (0)      2,243 (TN)               64 (FP)
Actual Fraud  (1)         16 (FN)               77 (TP)
```

### Critical Finding: Why Anomalies $\neq$ Confirmed Fraud
- The model produced **64 False Positives (FP)**.
- **Analysis of False Positives**: Inspection reveals that these 64 transactions were legitimate customers exhibiting genuine statistical anomalies — for instance, a user purchasing high-value electronics (₹48,000) for the first time, or transferring rent late at night.
- **Operational Reality**: In real-world fintech cybersecurity (and banking SOC operations), **an anomaly is a risk signal, not a criminal conviction**. High-risk anomalies trigger step-up multi-factor authentication (MFA/biometric OTP) or analyst queueing, protecting the user while allowing legitimate high-value payments to proceed.

---

## 4. Score Calibration: Decision Boundary to 0–100 Risk Score

Isolation Forest decision function values:
- Average Path Length $> c(n) \implies$ Score $> 0$ (Normal baseline)
- Average Path Length $< c(n) \implies$ Score $< 0$ (Short path / Isolated Outlier)

We map the decision scores onto a calibrated 0 to 100 scale:

| Risk Tier | Risk Score Range | Decision Action | Operational Protocol |
| :--- | :--- | :--- | :--- |
| **LOW** | `0.00 - 39.99` | **APPROVED** | Automated friction-free payment pass-through. |
| **MEDIUM** | `40.00 - 69.99` | **APPROVED (WITH CAUTION)** | Monitored; logged for velocity tracking. |
| **HIGH** | `70.00 - 89.99` | **FLAGGED FOR REVIEW** | Held in SOC Alert Queue; step-up biometric prompt. |
| **CRITICAL** | `90.00 - 100.00` | **BLOCKED** | Immediate block on VPA / device; security alert sent. |

---

## 5. Serialized Artifacts
- **Model Weights**: [`ml_model/saved_models/isolation_forest.joblib`](file:///d:/new%20project/ml_model/saved_models/isolation_forest.joblib)
- **Feature Preprocessor**: [`ml_model/saved_models/preprocessor.joblib`](file:///d:/new%20project/ml_model/saved_models/preprocessor.joblib)
- **Calibration Config**: [`ml_model/saved_models/model_config.json`](file:///d:/new%20project/ml_model/saved_models/model_config.json)
