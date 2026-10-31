# FraudShield AI — REST API Reference

All requests and responses use JSON. Base endpoint prefix: `/api/v1`.

---

## 1. System Health
- **Endpoint**: `GET /api/v1/system/health`
- **Description**: Verifies API status and SQLite database connection.
- **Response**:
```json
{
  "status": "healthy",
  "project": "FraudShield AI",
  "version": "1.0.0",
  "database": {
    "status": "healthy",
    "path": ".../database/fraudshield.db",
    "baseline_users_loaded": 5
  }
}
```

---

## 2. Transaction Evaluation
- **Endpoint**: `POST /api/v1/transactions/evaluate`
- **Description**: Scores a digital payment in real-time, computes anomaly score via Isolation Forest, generates explainability attribution, and persists result.
- **Request Body**:
```json
{
  "sender_upi": "arjun.sharma@okaxis",
  "receiver_upi": "merchant.store@icici",
  "amount": 2500.0,
  "channel": "UPI_APP",
  "device_id": "DEV-XIAOMI-12",
  "ip_address": "49.207.180.12",
  "location_city": "Mumbai"
}
```
- **Response**:
```json
{
  "tx_id": "TXN-20261030-9428",
  "sender_upi": "arjun.sharma@okaxis",
  "receiver_upi": "merchant.store@icici",
  "amount": 2500.0,
  "risk_score": 14.2,
  "risk_tier": "LOW",
  "status": "APPROVED",
  "primary_factor": "NORMAL_USAGE",
  "is_flagged": false,
  "explanations": [
    {
      "factor_name": "AMOUNT_RATIO",
      "weight": 0.12,
      "severity": "NORMAL",
      "description": "Amount is within 1.02x of user historical average."
    }
  ]
}
```

---

## 3. Alerts Management
- **Endpoint**: `GET /api/v1/alerts?status=PENDING`
- **Endpoint**: `PATCH /api/v1/alerts/{alert_id}`
  - **Payload**: `{"action": "APPROVE" | "BLOCK" | "DISMISS", "notes": "..."}`

---

## 4. Analytics & Metrics
- **Endpoint**: `GET /api/v1/analytics/metrics`
- **Description**: Returns live fraud rate, volume, risk distribution, and hourly trends for Chart.js.
