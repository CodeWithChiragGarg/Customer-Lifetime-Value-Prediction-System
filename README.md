# Customer Lifetime Value Prediction System

> An end-to-end machine learning application for predicting Customer Lifetime Value (CLV), estimating churn risk, segmenting customers, and explaining individual predictions using SHAP.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)](https://xgboost.readthedocs.io/)
[![SHAP](https://img.shields.io/badge/Explainability-SHAP-blueviolet)](https://shap.readthedocs.io/)

---

## Live Demo & Repository

🌐 **Live Application:** Coming Soon

💻 **GitHub Repository:**  
https://github.com/CodeWithChiragGarg/Customer-Lifetime-Value-Prediction-System

---

## Project Overview

Customer Lifetime Value is an important metric for understanding how valuable a customer may be to a business over time.

But I wanted this project to answer more than one question.

Instead of only asking:

> **"How valuable is this customer?"**

I wanted the system to also answer:

> **"How likely is this customer to churn?"**

and more importantly:

> **"Why did the model make this prediction?"**

This project therefore combines:

- Customer transaction analytics
- RFM-based feature engineering
- Probabilistic CLV modelling
- XGBoost machine learning
- Churn-risk estimation
- Customer segmentation
- Customer 360 profiles
- SHAP-based model explainability
- REST API development
- Interactive dashboard visualization

The result is an end-to-end system that converts raw retail transactions into customer-level business insights.

> **"Sirf prediction nikalna goal nahi tha — prediction ke peeche ka reason samajhna bhi equally important tha."**

---

# Why I Built This

A lot of machine-learning projects stop after displaying a prediction or an accuracy score.

I wanted to build something closer to an actual decision-support system.

For example, knowing that a customer has high predicted CLV is useful.

But a business may also want to know:

- Is this customer at risk of leaving?
- How frequently does this customer purchase?
- How much has the customer historically spent?
- What factors are influencing the prediction?
- What action could the business take?

That thinking eventually led to the development of **Customer 360** and **SHAP-based prediction explainability**.

---

# Key Features

## 1. Customer Lifetime Value Prediction

The system estimates customer value using a combination of probabilistic modelling and machine learning.

The modelling pipeline includes:

- BG/NBD
- Gamma-Gamma
- XGBoost Regression

The system generates customer-level CLV predictions that can then be explored through the dashboard.

---

## 2. Churn Risk Estimation

Each eligible customer receives a churn probability derived from customer purchasing behaviour.

The dashboard converts these probabilities into understandable risk categories such as:

- Low Risk
- Medium Risk
- High Risk

This allows valuable customers with elevated churn risk to be identified for potential retention campaigns.

---

## 3. Customer Segmentation

Customers can be explored using:

- Predicted CLV
- CLV Tier
- Churn Risk
- Customer Tenure
- Historical Spending

Customers are grouped into simple business-friendly CLV tiers:

| CLV Tier | Predicted CLV |
|---|---:|
| High | >= $500 |
| Medium | >= $200 |
| Low | < $200 |

The segmentation table also supports filtering, sorting and pagination.

---

# Customer 360

One of the major enhancements I added to the project is a dedicated **Customer 360** view.

Instead of only seeing customers in a table, a user can click a Customer ID and drill down into an individual customer profile.

The Customer 360 page displays:

- Predicted 90-Day CLV
- Churn Risk
- CLV Tier
- Total Historical Spending
- Number of Unique Orders
- Average Order Value
- First Purchase
- Last Purchase
- Customer Tenure
- Recommended Business Action
- SHAP Prediction Explanation

Example flow:

```text
Customer Segments
       |
       v
Select Customer
       |
       v
Customer 360
       |
       +---- Predicted CLV
       +---- Churn Risk
       +---- Purchase Behaviour
       +---- Business Recommendation
       +---- SHAP Explanation
```

This turns the project from a simple prediction dashboard into a customer-level analytics system.

---

# Explainable AI with SHAP

Machine-learning predictions should not always be treated as a black box.

For this reason, I integrated **SHAP (SHapley Additive exPlanations)** with the trained XGBoost model.

For an individual customer, the application identifies the strongest factors pushing the XGBoost prediction upward or downward.

Example:

```text
Why This Prediction?

Average Purchase Value
↑ Increases Prediction

Purchase Value Scale
↑ Increases Prediction

Repeat Orders
↓ Decreases Prediction

Purchase Frequency Scale
↓ Decreases Prediction

Purchase Velocity
↓ Decreases Prediction
```

Positive SHAP values indicate that a feature pushes the XGBoost prediction upward.

Negative SHAP values indicate that a feature pushes the prediction downward.

### Important

The XGBoost target is trained using a log transformation.

Therefore, SHAP values in the dashboard represent **relative model influence**, not direct dollar contributions.

This distinction is intentionally shown in the interface to avoid presenting misleading explanations.

> **"Prediction dena useful hai, lekin prediction ko explain kar pana usse zyada powerful bana deta hai."**

---

# A Bug That Changed the Project

One of the most important parts of this project came from a result that initially looked completely wrong.

The first version of the churn model produced approximately:

```text
Average Churn Risk ≈ 99.9%
```

Instead of accepting the result, I traced the issue backwards through the pipeline.

The original Online Retail dataset contains multiple product rows belonging to the same invoice.

For example:

```text
Invoice 536365
   Product A
   Product B
   Product C
   Product D
```

These rows represent **one purchase order**, not four separate purchases.

Initially, individual product line-items were effectively influencing purchase frequency as if they were independent purchase events.

That distorted the behavioural features used by the probabilistic model.

I modified the ingestion and training pipeline to preserve:

```text
InvoiceNo → order_id
```

and aggregate product line-items into actual purchase orders.

The corrected flow became:

```text
397,884 Product Line Items
            |
            v
     Group by InvoiceNo
            |
            v
      18,532 Orders
            |
            v
 Customer-Level Features
            |
            v
       CLV Models
```

After rebuilding the features and retraining the model:

```text
Before correction:
Average Churn Risk ≈ 99.9%

After correction:
Average Churn Risk ≈ 8.6%
```

This became one of the most useful lessons from the entire project.

> **"Model galat nahi tha — model ko jo business event samjhaya gaya tha, woh galat tha."**

In other words:

**Good machine learning starts before model training. It starts with correctly understanding what the data represents.**

---

# Dataset

The project currently uses the **Online Retail** transaction dataset.

Important fields include:

```text
InvoiceNo
StockCode
Description
Quantity
InvoiceDate
UnitPrice
CustomerID
Country
```

After cleaning and filtering, the working dataset contains approximately:

```text
397,884 valid transaction line-items
18,532 unique purchase orders
4,338 customers
2,845 returning customers used for repeat-purchase modelling
```

The distinction between **transaction line-items** and **actual purchase orders** is important throughout the project.

---

# Feature Engineering

Customer behaviour is represented using RFM-style and engineered features.

Core behavioural concepts include:

### Recency

How recently the customer purchased relative to their purchase history.

### Frequency

Number of repeat purchase events.

```text
frequency = number_of_orders - 1
```

### Monetary Value

Average customer purchase value.

Additional engineered features used by the XGBoost model include:

```text
recency
frequency
monetary_value
T
log_monetary
log_frequency
purchase_velocity
tenure_ratio
avg_order_value
```

---

# Machine Learning Pipeline

The system combines probabilistic customer modelling with gradient-boosted regression.

```text
Online Retail CSV
        |
        v
Data Cleaning
        |
        v
Invoice / Order Aggregation
        |
        v
Customer-Level Features
        |
        +----------------------+
        |                      |
        v                      v
    BG/NBD                Gamma-Gamma
        |                      |
        +----------+-----------+
                   |
                   v
          Probabilistic CLV
                   |
                   |
                   +-------------------+
                                       |
Customer Features                      |
        |                              |
        v                              |
     XGBoost                           |
        |                              |
        +--------------+---------------+
                       |
                       v
               Final CLV Prediction
                       |
                       v
               Customer Dashboard
                       |
                       v
                  Customer 360
                       |
                       v
                SHAP Explanation
```

---

# BG/NBD Model

BG/NBD is used to model repeat purchasing behaviour.

It estimates how likely a customer is to continue purchasing based on concepts such as:

- Frequency
- Recency
- Customer age / observation period

The model is particularly useful for non-contractual customer relationships where a customer does not explicitly cancel a subscription.

---

# Gamma-Gamma Model

Gamma-Gamma modelling is used to estimate customer monetary behaviour.

It complements BG/NBD by modelling expected transaction value.

Together, BG/NBD and Gamma-Gamma provide a probabilistic approach to CLV estimation.

---

# XGBoost Model

XGBoost is used as the machine-learning component of the CLV pipeline.

Current model parameters include regularization, subsampling and controlled tree depth to reduce overfitting.

The model uses behavioural and engineered customer features.

During the current model evaluation, the XGBoost pipeline has produced an R² around:

```text
90.68%
```

with corresponding RMSE and MAE metrics tracked during training.

### Evaluation Note

This metric should not yet be interpreted as:

> "90.68% accuracy for true future 90-day customer revenue."

The current training target is based on engineered historical customer value.

A future improvement is to implement **temporal validation**, where features are calculated before a historical cutoff date and the actual revenue generated during the following 90 days becomes the target.

I intentionally keep this distinction clear because reporting an impressive metric is less important than reporting the **correct meaning of that metric**.

---

# Technology Stack

## Frontend

- Next.js 14
- React
- Tailwind CSS
- JavaScript

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic

## Machine Learning

- XGBoost
- BG/NBD
- Gamma-Gamma
- scikit-learn
- SHAP
- NumPy
- Pandas

## Data & Storage

- SQLite
- CSV transaction datasets

## MLOps / Experiment Tracking

- MLflow

## Development & Deployment

- Git
- GitHub
- Uvicorn
- Docker support

---

# System Architecture

```text
                        ┌──────────────────────┐
                        │   Transaction CSV    │
                        └──────────┬───────────┘
                                   │
                                   v
                        ┌──────────────────────┐
                        │   Data Ingestion     │
                        │ Cleaning + Mapping   │
                        └──────────┬───────────┘
                                   │
                                   v
                        ┌──────────────────────┐
                        │ Invoice Aggregation  │
                        │ InvoiceNo → Order ID │
                        └──────────┬───────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     │                           │
                     v                           v
          ┌────────────────────┐       ┌────────────────────┐
          │      Database      │       │ Feature Engineering│
          │ SQLite / SQLAlchemy│       │ RFM + Behavioural  │
          └────────────────────┘       └──────────┬─────────┘
                                                 │
                            ┌────────────────────┼────────────────────┐
                            │                    │                    │
                            v                    v                    v
                       ┌────────┐          ┌────────────┐       ┌─────────┐
                       │ BG/NBD │          │Gamma-Gamma │       │ XGBoost │
                       └────┬───┘          └─────┬──────┘       └────┬────┘
                            │                    │                   │
                            └──────────┬─────────┘                   │
                                       │                             │
                                       v                             │
                              Probabilistic CLV                      │
                                       │                             │
                                       └──────────────┬──────────────┘
                                                      │
                                                      v
                                            CLV Predictions
                                                      │
                                                      v
                                             FastAPI Backend
                                                      │
                                                      v
                                             Next.js Dashboard
                                                      │
                               ┌──────────────────────┼────────────────────┐
                               │                      │                    │
                               v                      v                    v
                            Dashboard            Segmentation        Customer 360
                                                                         │
                                                                         v
                                                                  SHAP Explanation
```

---

# API Endpoints

The FastAPI backend exposes REST endpoints for predictions, segmentation and customer-level analytics.

Examples:

```text
GET /api/v1/dashboard/summary

GET /api/v1/predict/clv

GET /api/v1/segments

GET /api/v1/customers/{customer_id}

GET /api/v1/customers/{customer_id}/explanation

POST /api/v1/predict/custom
```

Interactive API documentation is available locally at:

```text
http://localhost:8000/docs
```

---

# Dashboard

The main dashboard provides a quick overview of customer analytics.

Current KPIs include:

- Average CLV
- Active Customers
- Average Churn Risk
- Total Revenue

It also provides visual analysis of:

- CLV distribution
- Churn-risk distribution
- Customer segments

---

# Customer Segments

The Customer Segments page allows users to explore individual customers.

Available information includes:

```text
Customer ID
Email
Tenure
Total Spent
Predicted CLV
CLV Tier
Churn Risk
```

Customer IDs are clickable.

Selecting a customer opens the dedicated **Customer 360** view.

---

# Business Recommendations

Customer 360 converts CLV and churn information into simple business actions.

Examples:

### High CLV + Low Churn Risk

```text
VIP and loyalty program opportunity
```

### High CLV + Medium Churn Risk

```text
Offer personalized loyalty incentive
```

### High CLV + High Churn Risk

```text
Priority retention campaign
```

### High Churn Risk

```text
Run re-engagement campaign
```

This layer helps connect model output with possible business decisions.

---

# Project Structure

```text
Customer-Lifetime-Value-Prediction-System/
│
├── backend/
│   │
│   ├── app/
│   │   ├── routers/
│   │   │   ├── predict.py
│   │   │   ├── segments.py
│   │   │   └── customers.py
│   │   │
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── ml/
│   │   ├── probabilistic.py
│   │   ├── xgboost_model.py
│   │   └── models/
│   │
│   ├── scripts/
│   │   ├── ingest_data.py
│   │   ├── feature_engineering.py
│   │   └── train_model.py
│   │
│   └── requirements.txt
│
├── frontend/
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.js
│   │   │   ├── segments/
│   │   │   ├── custom-predict/
│   │   │   └── customers/
│   │   │       └── [customerId]/
│   │   │           └── page.js
│   │   │
│   │   ├── components/
│   │   │   └── CustomerTable.js
│   │   │
│   │   └── lib/
│   │       └── api.js
│   │
│   └── package.json
│
└── README.md
```

---

# Running the Project Locally

## 1. Clone Repository

```bash
git clone https://github.com/CodeWithChiragGarg/Customer-Lifetime-Value-Prediction-System.git

cd Customer-Lifetime-Value-Prediction-System
```

---

## 2. Backend Setup

```bash
cd backend

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

Start FastAPI:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

## 3. Frontend Setup

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# Current Model Results

Current project results include approximately:

| Metric | Result |
|---|---:|
| Valid Transaction Line Items | 397,880 |
| Unique Orders | 18,532 |
| Total Customers | 4,338 |
| Returning Customers Modelled | 2,845 |
| Average Churn Risk | ~8.6% |
| Median Churn Risk | ~2.1% |
| High-Risk Customers (>70%) | 38 |
| Current XGBoost R² | ~90.68% |

These values correspond to the current development dataset and modelling pipeline.

---

# What This Project Taught Me

This project was not only about getting a model to run.

Some of my biggest learnings were:

- Understanding the business meaning of a row is as important as understanding the algorithm.
- A technically valid model can still produce meaningless output when the underlying event definition is wrong.
- Model results should be questioned when they do not make business sense.
- Feature engineering can have a larger impact than simply increasing model complexity.
- Explainability makes machine-learning predictions more useful to actual decision-makers.
- Backend, frontend, database and ML components must use consistent definitions.
- A high metric is meaningless if I cannot clearly explain what was actually measured.
- Debugging the data pipeline was often more valuable than tuning another hyperparameter.

> **"ML mein sirf model banana important nahi hai — data ko question karna aur result ko challenge karna bhi important hai."**

That mindset became one of the most important parts of this project.

---

# Future Improvements

The project is actively being improved.

Planned enhancements include:

- [ ] True future 90-day CLV temporal validation
- [ ] Dedicated Model Performance dashboard
- [ ] Global SHAP feature-importance analysis
- [ ] Customer order-history timeline
- [ ] Data-quality monitoring
- [ ] Improved customer segmentation strategy
- [ ] Model comparison dashboard
- [ ] Automated model retraining pipeline
- [ ] PostgreSQL production database
- [ ] Dockerized production deployment
- [ ] Public cloud deployment
- [ ] Live application URL
- [ ] CI/CD pipeline
- [ ] Automated testing

---

# Development Philosophy

While building this project, I tried to follow one simple rule:

> **Don't trust a prediction just because the code runs.**

Whenever a result looked unusual, I tried to understand the reason before changing the model.

The 99.9% churn issue was a good example.

It would have been easy to modify thresholds until the dashboard looked reasonable.

Instead, I traced the problem back to the definition of a purchase event and corrected the underlying data pipeline.

> **"Dashboard ko believable banana goal nahi hai — model ko genuinely correct banana goal hai."**

---

# About the Project

This project was developed as an applied machine-learning and full-stack analytics project.

The objective was to understand how customer analytics can move from:

```text
Raw Data
   ↓
Machine Learning
   ↓
Prediction
```

to:

```text
Raw Transactions
       ↓
Data Understanding
       ↓
Feature Engineering
       ↓
Machine Learning
       ↓
Model Validation
       ↓
Explainability
       ↓
Customer-Level Insight
       ↓
Business Action
```

That transition is the main idea behind this project.

---

# Developer

**Chirag Garg**

GitHub:  
https://github.com/CodeWithChiragGarg

Project Repository:  
https://github.com/CodeWithChiragGarg/Customer-Lifetime-Value-Prediction-System

---

## Final Note

This project is still evolving.

The goal is not to claim that every component is production-perfect, but to continuously improve the modelling methodology, validation strategy, explainability and application design.

> **"Build karna important hai, but samajh ke build karna usse bhi important hai."**

---

⭐ If you found this project interesting, consider starring the repository.