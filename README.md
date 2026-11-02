# 🛡️ Crypta Core AI

**AI-powered fraud detection system for e-commerce platforms**

Detects: Fake Reviews · Return Fraud · Suspicious User Behavior · Payment Fraud

---

## Architecture

```
cryptacoreAi/
├── backend/          # FastAPI (Python) REST API
├── frontend/         # React + Vite Dashboard
├── ml/               # ML Models, Training Scripts, Inference
├── docker-compose.yml
└── README.md
```

## Quick Start

### 1. Start the Database
```bash
docker-compose up -d
```

### 2. Train ML Models
```bash
cd ml
pip install -r ../backend/requirements.txt
python synthetic_data_generator.py
python train_models.py
```

### 3. Start Backend
```bash
cd backend
cp .env.example .env
uvicorn main:app --reload --port 8000
```
> API Docs: http://localhost:8000/docs

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
> Dashboard: http://localhost:5173

---

## Features

| Feature | Model | Output |
|---|---|---|
| Fake Review Detection | DistilBERT | FAKE/GENUINE + confidence |
| Return Fraud | XGBoost | Risk score 0-100 |
| User Behavior | Isolation Forest + Random Forest | Anomaly flags |
| Payment Fraud | XGBoost ensemble | Fraud probability |
| Risk Score Engine | Composite (SHAP) | 0-100 Crypta Risk Score |

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Alembic
- **ML**: HuggingFace Transformers (DistilBERT), XGBoost, Scikit-learn, SHAP
- **Frontend**: React 18, Vite, Recharts, Framer Motion
- **Infra**: Docker, docker-compose
