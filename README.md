<div align="center">

# 🧠 Customer Lifetime Value Prediction System

<img src="https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js&logoColor=white"/>
<img src="https://img.shields.io/badge/XGBoost-ML-orange?style=for-the-badge&logo=xgboost&logoColor=white"/>
<img src="https://img.shields.io/badge/MLflow-Tracking-blue?style=for-the-badge&logo=mlflow&logoColor=white"/>
<img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>

<br/>

> **A full-stack ML-powered platform that predicts Customer Lifetime Value (CLV) over a 90-day horizon and assesses churn risk — combining probabilistic modeling with XGBoost gradient boosting.**

<br/>

**Built by [Stuti Singh](https://github.com/stutisingh1701)**

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 **CLV Prediction** | 90-day revenue forecast per customer using ensemble ML |
| 🔥 **Churn Risk Scoring** | BG/NBD probabilistic churn probability per customer |
| 🎯 **Customer Segmentation** | Automatic High / Medium / Low CLV tier classification |
| 📁 **Custom CSV Upload** | Upload any dataset and get instant predictions |
| 📈 **Interactive Dashboard** | Real-time charts, KPI cards, and filterable tables |
| 🧪 **MLflow Tracking** | Full experiment tracking with hyperparameter logging |
| 🐳 **Docker Support** | One-command deployment with Docker Compose |

---

## 🖥️ Live Demo

| Service | URL |
|---|---|
| 🌐 Frontend Dashboard | `http://localhost:3000` |
| ⚡ FastAPI Backend | `http://localhost:8000` |
| 📖 Swagger API Docs | `http://localhost:8000/docs` |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                 │
│   Dashboard │ Segments │ Custom CSV Predictor            │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────┐
│                  Backend (FastAPI)                       │
│   /predict/clv │ /segments │ /dashboard/summary          │
│   /predict/custom (file upload)                          │
└──────────┬───────────────────────────┬──────────────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼──────────────────┐
│   ML Pipeline       │   │   Database (SQLite/PostgreSQL) │
│   ├─ BG/NBD Model   │   │   ├─ customers                 │
│   ├─ Gamma-Gamma    │   │   ├─ transactions               │
│   ├─ XGBoost        │   │   ├─ rfm_features               │
│   └─ Ensemble (60/40│   │   └─ predictions                │
└─────────────────────┘   └────────────────────────────────┘
```

---

## 🤖 Machine Learning Models

### Dual Ensemble Architecture

```
                    Input: Customer Transaction History
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                                           │
    ┌─────────▼──────────┐                   ┌────────────▼──────────┐
    │  Probabilistic      │                   │  XGBoost Regressor    │
    │  ─────────────────  │                   │  ──────────────────── │
    │  BG/NBD Model       │                   │  9 Engineered Features│
    │  (Purchase Freq)    │                   │  log1p target scaling │
    │         +           │                   │  R² ≥ 90% accuracy    │
    │  Gamma-Gamma Model  │                   │                       │
    │  (Monetary Value)   │                   │                       │
    └─────────┬──────────┘                   └────────────┬──────────┘
              │  60% weight                               │  40% weight
              └─────────────────────┬─────────────────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │    Weighted Ensemble         │
                     │  CLV = 0.6×Prob + 0.4×XGB   │
                     └─────────────────────────────┘
```

### Feature Engineering Pipeline

| Feature | Formula | Purpose |
|---|---|---|
| Recency | Days since last purchase | Engagement freshness |
| Frequency | Total repeat transactions | Purchase habituality |
| Monetary Value | Average transaction amount | Purchasing power |
| Tenure (T) | Days since signup | Customer lifecycle |
| Log Monetary | `ln(1 + monetary)` | Reduce variance skew |
| Log Frequency | `ln(1 + frequency)` | Normalize count distribution |
| Purchase Velocity | `frequency / (recency + 1)` | Transaction rate over time |
| Tenure Ratio | `recency / (T + 1)` | Inactive proportion of life |
| Avg Order Value | `monetary / (frequency + 1)` | Normalized order size |

---

## 🗃️ Database Schema

```sql
customers        → customer_id, email, signup_date
transactions     → transaction_id, customer_id, timestamp, amount
rfm_features     → customer_id, recency, frequency, monetary_value
predictions      → customer_id, predicted_clv_90d, churn_probability
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/stutisingh1701/Customer-Lifetime-Value-Prediction-System.git
cd Customer-Lifetime-Value-Prediction-System
```

### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt

# Run data pipeline (first time only)
python scripts/ingest_data.py
python scripts/feature_engineering.py
python scripts/train_model.py

# Start the API server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend

```bash
cd frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev
```

### 4. Open in Browser

```
http://localhost:3000
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

This starts:
- 🐘 PostgreSQL database
- ⚡ FastAPI backend on port `8000`
- 🌐 Next.js frontend on port `3000`

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/v1/predict/clv` | CLV predictions with RFM data |
| `GET` | `/api/v1/dashboard/summary` | KPI aggregates (avg CLV, churn, revenue) |
| `GET` | `/api/v1/segments` | Filtered & paginated customer segments |
| `POST` | `/api/v1/predict/custom` | Upload CSV → get instant predictions |

> Full interactive docs at: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
Customer-Lifetime-Value-Prediction-System/
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Settings & environment
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models.py        # ORM models
│   │   └── routers/
│   │       ├── predict.py   # CLV prediction endpoints
│   │       └── segments.py  # Segmentation endpoints
│   ├── ml/
│   │   ├── probabilistic.py # BG/NBD + Gamma-Gamma
│   │   └── xgboost_model.py # XGBoost regressor
│   ├── scripts/
│   │   ├── ingest_data.py       # Data ingestion
│   │   ├── feature_engineering.py # RFM computation
│   │   ├── train_model.py       # Model training
│   │   └── test_accuracy.py     # 5-fold CV evaluation
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   ├── components/      # React components
│   │   └── lib/api.js       # API client
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── run.bat                  # Windows one-click launcher
└── README.md
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13, FastAPI, Uvicorn |
| **ML Models** | XGBoost, lifetimes (BG/NBD + Gamma-Gamma) |
| **Experiment Tracking** | MLflow |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **ORM** | SQLAlchemy |
| **Frontend** | Next.js 14, React 18, Tailwind CSS |
| **Charts** | Recharts |
| **Containerization** | Docker, Docker Compose |

---

## 📊 Model Performance

| Metric | Value |
|---|---|
| **Algorithm** | Weighted Ensemble (BG/NBD + XGBoost) |
| **CV Strategy** | 5-Fold Cross Validation |
| **R² Accuracy** | ≥ 90% |
| **Target Variable** | 90-day Customer Lifetime Value |
| **Churn Signal** | Probability of customer being alive (BG/NBD) |

---

## 👩‍💻 Author

<div align="center">

**Stuti Singh**

[![GitHub](https://img.shields.io/badge/GitHub-stutisingh1701-black?style=for-the-badge&logo=github)](https://github.com/stutisingh1701)

</div>

---

## 📄 License

Private — All rights reserved © Stuti Singh 2026
