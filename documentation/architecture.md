# FraudShield AI — System Architecture & Component Design

## Overview
FraudShield AI is a fintech fraud detection platform designed for real-time UPI and digital payment streams. It adopts a modular, 4-tier architecture:

1. **Frontend (Presentation Tier)**: Vanilla HTML5, modern CSS3 (Cybersecurity Dark Navy theme), Vanilla ES6+ and Chart.js for zero-build, ultra-fast client-side execution.
2. **Backend (Application Tier)**: Python & FastAPI for high-throughput, asynchronous REST request handling, Pydantic data validation, and orchestration.
3. **ML & Explainability Engine (Inference Tier)**: Scikit-Learn Isolation Forest anomaly detector coupled with domain heuristics and a transparent feature attribution engine (XAI).
4. **Database (Persistence Tier)**: SQLite database running in Write-Ahead-Logging (WAL) mode for atomic, high-concurrency local persistence.

---

## Folder Map & Responsibilities

```text
├── frontend/             # Client-side presentation layer
│   ├── css/              # Theme variables, layout, components
│   ├── js/               # API client, Chart.js managers, UI controllers
│   ├── assets/           # Icons and visual media
│   └── index.html        # Main dashboard HTML view
├── backend/              # Core API gateway and business logic
│   ├── api/              # REST endpoint routes
│   ├── core/             # Settings, thresholds, configurations
│   ├── services/         # Scoring service, alert manager, profile service
│   ├── schemas/          # Pydantic data validation contracts
│   └── main.py           # FastAPI app entrypoint
├── ml_model/             # Machine Learning pipeline
│   ├── training/         # Model training and hyperparameter scripts
│   ├── features/         # Feature engineering & normalization
│   ├── explainability/   # Factor attribution and reason codes
│   └── saved_models/     # Serialized .joblib artifacts
├── dataset/              # Data storage and synthesis
│   ├── raw/              # Seed data & unverified records
│   ├── processed/        # Feature-engineered training sets
│   └── generators/       # Synthetic UPI payment generators
├── database/             # Relational data layer
│   ├── schema.sql        # Declarative SQLite schema
│   ├── connection.py     # Connection factory & query utilities
│   ├── init_db.py        # Database initializer
│   └── seeds/            # Initial user behavioral profiles
├── tests/                # Automated testing
│   ├── unit/             # Schema, DB, and feature unit tests
│   └── integration/      # End-to-end API integration tests
└── documentation/        # Technical specifications & guides
```
