# Crypta Core AI — Implementation Plan

A full-stack AI-powered fraud detection platform for e-commerce, combining NLP, machine learning, and anomaly detection to identify fake reviews, return fraud, suspicious users, and payment fraud. Outputs a human-readable risk score (0–100) with SHAP-powered explanations for every decision.

---

## User Review Required

> [!IMPORTANT]
> **Model Strategy**: To avoid requiring GPU hardware or heavy downloads, all ML models will use **pre-trained / fine-tuned lightweight versions** with synthetic training data baked in. `DistilBERT` (66MB) is used instead of full BERT. All models are serialized and bundled with the project. No external API keys are needed.

> [!IMPORTANT]
> **Database**: PostgreSQL is the primary database. A `docker-compose.yml` will be provided to spin up the DB. If you prefer SQLite for local development (no Docker needed), please let me know before I begin.

> [!IMPORTANT]
> **Dependencies**: The project requires Python 3.9+, Node.js 18+, and either Docker (for PostgreSQL) or a local PostgreSQL installation. Make sure these are available.

---

## Proposed Changes

### 1. Project Scaffold

**Monorepo structure at `e:\cryptacoreAi`:**

```
cryptacoreAi/
├── backend/          # FastAPI (Python)
├── frontend/         # React + Vite
├── ml/               # ML model training & inference
├── docker-compose.yml
└── README.md
```

---

### 2. ML Layer (`ml/`)

#### [NEW] `ml/models/fake_review_detector.py`
- **DistilBERT** text classifier fine-tuned on review authenticity
- Uses HuggingFace `transformers` pipeline (`text-classification`)
- Detects: spam language, bot patterns, repeated phrases, excessive positivity/negativity
- Output: `{label: "FAKE"|"GENUINE", confidence: float, reasons: [str]}`

#### [NEW] `ml/models/return_fraud_detector.py`
- **XGBoost** classifier trained on user return history features:
  - `return_rate`, `avg_days_to_return`, `refund_abuse_count`, `items_returned_damaged`
  - `account_age_days`, `total_orders`, `total_returns`
- Output: `{risk_score: 0-100, label: "HIGH"|"MEDIUM"|"LOW", explanation: [str]}`

#### [NEW] `ml/models/user_behavior_analyzer.py`
- **Isolation Forest** (anomaly detection) + **Random Forest** classifier on:
  - Login frequency, IP changes, device fingerprint changes
  - Session duration, cart abandonment rate
  - Order velocity (orders per day)
- Output: `{anomaly_score: float, risk_level: str, flags: [str]}`

#### [NEW] `ml/models/payment_fraud_detector.py`
- **XGBoost** + **Isolation Forest** ensemble on:
  - Transaction amount vs. user average
  - Payment method changes, failed payment attempts
  - Geolocation mismatch, time-of-day pattern
  - Card BIN risk score
- Output: `{fraud_probability: float, risk_score: 0-100, flags: [str]}`

#### [NEW] `ml/risk_score_engine.py`
- Composite scorer combining all 4 model outputs
- Weighted average: `fake_review * 0.2 + return_fraud * 0.3 + behavior * 0.25 + payment * 0.25`
- Generates final 0–100 **Crypta Risk Score**
- Uses **SHAP values** for explainability (top 3 contributing factors)

#### [NEW] `ml/synthetic_data_generator.py`
- Generates realistic synthetic datasets for model training
- Creates 10,000 labeled samples for each model
- No real user data required

#### [NEW] `ml/train_models.py`
- Script to train all models and save to `ml/saved_models/`
- Serializes via `joblib` and HuggingFace `save_pretrained`

---

### 3. Backend (`backend/`)

#### [NEW] `backend/main.py`
FastAPI app entry point with CORS, router mounting, and lifespan events to load ML models.

#### [NEW] `backend/database.py`
SQLAlchemy async engine setup for PostgreSQL. Connection pooling configured.

#### [NEW] `backend/models/` (SQLAlchemy ORM)
- `User` — user profile, account age, total orders/returns, risk score
- `Review` — product review text, fraud label, confidence
- `Order` — order details, return status, payment info
- `FraudAlert` — flagged entity, fraud type, risk score, explanation

#### [NEW] `backend/routers/reviews.py`
- `POST /api/reviews/analyze` — runs DistilBERT on review text, saves result

#### [NEW] `backend/routers/returns.py`
- `POST /api/returns/evaluate` — evaluates return fraud using XGBoost, saves alert

#### [NEW] `backend/routers/users.py`
- `POST /api/users/risk-score` — calculates composite user risk score
- `GET /api/users/flagged` — returns list of high-risk users (risk > 70)

#### [NEW] `backend/routers/payments.py`
- `POST /api/payments/analyze` — payment fraud detection

#### [NEW] `backend/routers/dashboard.py`
- `GET /api/dashboard/stats` — summary counts, avg risk, recent alerts
- `GET /api/orders/suspicious` — orders with high fraud probability

#### [NEW] `backend/schemas/` (Pydantic models)
Request/response schemas for all endpoints.

#### [NEW] `backend/requirements.txt`
All Python dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `transformers`, `torch`, `xgboost`, `scikit-learn`, `shap`, `joblib`, `pydantic`, `alembic`, `python-dotenv`

---

### 4. Frontend (`frontend/`)

React + Vite SPA with a dark-themed premium dashboard.

#### [NEW] `frontend/src/pages/Dashboard.jsx`
- **Crypta Risk Summary** — live stats cards (total flagged, avg risk, alerts today)
- **Risk Score Gauge** — animated circular gauge (Chart.js / Recharts)
- **Fraud Type Breakdown** — donut chart (fake reviews / return fraud / payment / behavior)
- **Recent Alerts Feed** — real-time list of new fraud alerts

#### [NEW] `frontend/src/pages/FlaggedUsers.jsx`
- Table of high-risk users with sortable columns
- Risk score badge (color-coded: red/orange/green)
- Expandable row → SHAP explanation + contributing factors

#### [NEW] `frontend/src/pages/ReviewAnalyzer.jsx`
- Text input for review analysis
- Instant fake review detection with confidence bar
- Highlighted reasons (spam keywords, bot patterns)

#### [NEW] `frontend/src/pages/Orders.jsx`
- Suspicious orders table
- Columns: Order ID, User, Amount, Risk Score, Payment Flags, Action
- Filter by risk level

#### [NEW] `frontend/src/pages/RiskScoreExplorer.jsx`
- Input panel: userId / orderId / reviewText
- Real-time risk score computation
- Animated score meter + SHAP explanation breakdown

#### [NEW] `frontend/src/components/`
- `Navbar.jsx` — sidebar navigation with Crypta branding
- `RiskGauge.jsx` — animated gauge component
- `ScoreBadge.jsx` — color-coded risk badge
- `AlertFeed.jsx` — live alert stream
- `ShapExplainer.jsx` — visual SHAP bar chart

#### [NEW] `frontend/src/api/client.js`
Axios client wired to FastAPI backend with base URL config.

---

### 5. Infrastructure

#### [NEW] `docker-compose.yml`
- PostgreSQL 15 service with persistent volume
- `backend` service (optional containerization)

#### [NEW] `backend/alembic/` 
Database migrations for all ORM models.

#### [NEW] `.env.example`
Environment variable template for DB URL, secret key, model paths.

---

## Verification Plan

### Automated Tests

**1. Train ML Models:**
```powershell
cd e:\cryptacoreAi\ml
pip install -r ../backend/requirements.txt
python synthetic_data_generator.py
python train_models.py
```
Expected: All models saved to `ml/saved_models/`. Prints accuracy metrics.

**2. Backend API Tests (pytest):**
```powershell
cd e:\cryptacoreAi\backend
pip install pytest httpx
pytest tests/ -v
```
Tests cover: review analysis, return fraud, user risk score, payment fraud, dashboard stats endpoints.

**3. Start Backend:**
```powershell
cd e:\cryptacoreAi\backend
uvicorn main:app --reload --port 8000
```
Visit: `http://localhost:8000/docs` — Swagger UI should list all endpoints.

**4. Start Frontend:**
```powershell
cd e:\cryptacoreAi\frontend
npm install
npm run dev
```
Visit: `http://localhost:5173` — Dashboard should load.

### Manual Verification (Browser)

1. **Dashboard** (`/`) — Cards show fraud counts, gauge shows risk score, donut chart visible
2. **Review Analyzer** (`/reviews`) — Paste a suspicious review → confidence score + reasons shown
3. **Flagged Users** (`/users`) — Table lists high-risk users with expandable SHAP explanations
4. **Suspicious Orders** (`/orders`) — Table shows orders with risk badges
5. **Risk Explorer** (`/explorer`) — Enter a user ID → animated score meter appears with explanation
