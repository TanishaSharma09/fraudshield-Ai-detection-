# FraudShield AI — Explainable Alert Module Specification

---

## 1. Explainability Architecture & Why Transparent Feature Attribution

In compliance with AI explainability principles and financial regulations (RBI Cybersecurity Framework and DPDP Act 2023):
- **Why Not Fake SHAP?** Standard SHAP `TreeExplainer` is mathematically formulated for supervised tree models (e.g. XGBoost/Random Forest). While approximations exist for Isolation Forest, they suffer from significant computational overhead (incompatible with sub-50ms live payment scoring) and make restrictive independence assumptions.
- **FraudShield AI Approach**: We employ **Transparent Feature-Based Deviation Attribution**. It directly benchmarks an evaluated payment's behavioral vector against empirical population distributions and the user's personal historical baseline.
- **Full Transparency**: We never pretend these are SHAP Shapley values; they are transparent, auditable feature deviation attributions.

---

## 2. Mathematical Attribution Methodology

### Continuous Features (Amount, Velocity, Time Delta)
For each continuous feature $j$, the deviation score $D_j$ is calculated using robust empirical statistics:
$$D_j = \left| \frac{x_j - \text{Median}(X_j)}{\text{IQR}(X_j) + \epsilon} \right|$$
Where $\text{IQR} = Q_3 - Q_1$.

For user-relative features (such as `amount_to_avg_ratio`):
$$\text{Ratio} = \frac{\text{amount}}{\max(10, \mu_{\text{user\_hist}})}$$

### Discrete & Categorical Features
- **Unrecognised Device**: Evaluates hardware signature against verified devices. Active mismatch assigns categorical deviation weight.
- **Unfamiliar Payee VPA**: Checks whether the beneficiary account has ever been paid before.
- **Nocturnal Sleep Window**: Binary indicator evaluating whether transaction falls within 01:00 AM – 04:59 AM.

### Normalized Relative Impact Weights
Each triggered factor is assigned a calibrated raw weight $w_i$. The final reported impact weights are normalized to sum to **1.0 (100%)**:
$$\text{Impact Weight}_i = \frac{w_i}{\sum_{k=1}^m w_k}$$

---

## 3. Structured Explanation Payload Schema

For every suspicious transaction, the engine generates:

```json
{
  "alert_id": "ALT-20261031-849102",
  "transaction_id": "UPI-20261031-102941",
  "risk_level": "High risk",
  "risk_score": 89.4,
  "primary_reason": "High-frequency burst: 7 transactions initiated within 15 minutes (characteristic rapid account drain pattern).",
  "recommended_review_action": "CRITICAL SECURITY HOLD: Immediate freeze on outgoing UPI transfers from this device. Contact account holder via out-of-band verified telephony.",
  "contributing_factors": [
    {
      "factor_id": "VELOCITY_BURST",
      "factor_name": "Short-Interval Velocity Spike",
      "impact_weight": 0.42,
      "severity": "CRITICAL",
      "explanation": "High-frequency burst: 7 transactions initiated within 15 minutes (characteristic rapid account drain pattern).",
      "observed_value": "7 txs / 15m",
      "baseline_value": "1.3 txs / 15m (normal average)"
    },
    {
      "factor_id": "HARDWARE_DEVICE_MISMATCH",
      "factor_name": "Unrecognised Hardware Fingerprint",
      "impact_weight": 0.32,
      "severity": "HIGH",
      "explanation": "Payment initiated from hardware ID 'DEV-NEW-UNKNOWN', which does not match verified device signatures for this account (SIM swap or device takeover risk).",
      "observed_value": "DEV-NEW-UNKNOWN",
      "baseline_value": ["DEV-XIAOMI-12"]
    },
    {
      "factor_id": "AMOUNT_DEVIATION",
      "factor_name": "Historical Amount Spike",
      "impact_weight": 0.26,
      "severity": "HIGH",
      "explanation": "Payment value (₹42,000.00) is 16.8x higher than customer's rolling 30-day baseline average (₹2,500.00).",
      "observed_value": "₹42,000.00 (16.8x)",
      "baseline_value": "₹2,500.00"
    }
  ],
  "explanation_methodology": "Transparent Feature-Based Deviation Attribution (Empirical Baseline Comparison)",
  "disclaimer": "Notice: Suspicious activity indicates significant statistical deviation from normal payment baselines and elevated transaction risk. It warrants review or step-up authentication, but does not constitute definitive proof of criminal fraud.",
  "generated_at": "2026-10-31T00:03:00Z"
}
```

---

## 4. SOC Review Actions Runbook

| Risk Profile | Contributing Factors | Recommended Operational Action |
| :--- | :--- | :--- |
| **High risk** | Velocity Burst + Device Mismatch | **CRITICAL HOLD**: Freeze outgoing transfers. Initiate out-of-band call to account holder. |
| **High risk** | Amount Spike + Nocturnal Hours | **TEMPORARY 30-MIN HOLD**: Dispatch high-priority push prompt requesting biometric confirmation. |
| **Medium risk** | Phishing Channel (Collect Request) | **IN-APP WARNING**: Prompt user: *"You are paying, NOT receiving money"*. Require biometric OTP. |
| **Medium risk** | New Recipient VPA | **FRICTIONLESS STEP-UP**: Prompt for TouchID / FaceID on primary registered device. |
| **Low risk** | Baseline Conformance | **AUTOMATED APPROVAL**: Friction-free instant payment routing. |
