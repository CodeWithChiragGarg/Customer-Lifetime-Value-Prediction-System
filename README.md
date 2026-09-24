# Customer Lifetime Value Prediction System

> An end-to-end machine learning and analytics platform for predicting Customer Lifetime Value (CLV), estimating churn risk, segmenting customers, and explaining individual predictions using SHAP.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)](https://xgboost.readthedocs.io/)
[![SHAP](https://img.shields.io/badge/Explainability-SHAP-blueviolet)](https://shap.readthedocs.io/)

---

## 🚀 Live Demo

**Frontend:**  
https://customer-lifetime-value-prediction-tau.vercel.app

**Backend API:**  
https://customer-lifetime-value-api.onrender.com

**API Documentation:**  
https://customer-lifetime-value-api.onrender.com/docs

**GitHub Repository:**  
https://github.com/CodeWithChiragGarg/Customer-Lifetime-Value-Prediction-System

---

# 📌 Overview

Customer Lifetime Value (CLV) helps businesses estimate how valuable a customer may be over time.

This project goes beyond simply predicting customer value.

It answers three important questions:

1. **How valuable is this customer?**
2. **How likely is this customer to churn?**
3. **Why did the model make this prediction?**

The system combines:

- Transaction analytics
- RFM-based feature engineering
- BG/NBD modelling
- Gamma-Gamma modelling
- XGBoost regression
- Churn-risk estimation
- Customer segmentation
- Customer 360 profiles
- SHAP explainability
- FastAPI REST APIs
- Interactive Next.js dashboard

The final application converts raw retail transactions into customer-level analytics and business insights.

> **Prediction dena useful hai — lekin prediction ko explain kar pana usse zyada powerful bana deta hai.**

---

# 🎯 Project Objective

Many machine-learning projects stop after producing a prediction or an evaluation metric.

The objective of this project was to build a more complete decision-support system where a user can move from:

```text
Raw Transactions
       ↓
Data Processing
       ↓
Feature Engineering
       ↓
Machine Learning
       ↓
CLV + Churn Prediction
       ↓
Customer Segmentation
       ↓
Customer 360
       ↓
Explainable AI
       ↓
Business Insight
