"""Customer 360 and prediction explainability API endpoints."""

from functools import lru_cache

import numpy as np
import pandas as pd
import shap
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Prediction, Transaction
from ml.xgboost_model import XGBoostCLVModel


router = APIRouter()


# =========================================================
# Response Models
# =========================================================

class Customer360Response(BaseModel):
    """Complete summary for one customer."""

    customer_id: str
    email: str

    predicted_clv_90d: float | None = None
    churn_probability: float | None = None
    clv_tier: str | None = None
    risk_level: str | None = None

    total_spent: float
    order_count: int
    average_order_value: float

    first_purchase: str | None = None
    last_purchase: str | None = None
    tenure_days: int | None = None

    recommended_action: str


class ExplanationFactor(BaseModel):
    """One feature contributing to the XGBoost prediction."""

    feature: str
    display_name: str
    value: float
    shap_value: float
    direction: str


class CustomerExplanationResponse(BaseModel):
    """SHAP explanation for one customer's XGBoost prediction."""

    customer_id: str
    model: str
    explanation_scope: str
    top_factors: list[ExplanationFactor]


# =========================================================
# Business Logic
# =========================================================

def assign_clv_tier(clv: float | None) -> str | None:
    """Convert predicted CLV into a business tier."""

    if clv is None:
        return None

    if clv >= 500:
        return "High"

    if clv >= 200:
        return "Medium"

    return "Low"


def assign_risk_level(
    churn_probability: float | None,
) -> str | None:
    """Convert churn probability into a readable risk level."""

    if churn_probability is None:
        return None

    if churn_probability >= 0.70:
        return "High Risk"

    if churn_probability >= 0.30:
        return "Medium Risk"

    return "Low Risk"


def recommend_action(
    clv_tier: str | None,
    risk_level: str | None,
) -> str:
    """Generate a simple business recommendation."""

    if clv_tier == "High" and risk_level == "High Risk":
        return "Priority retention campaign"

    if clv_tier == "High" and risk_level == "Medium Risk":
        return "Offer personalized loyalty incentive"

    if clv_tier == "High" and risk_level == "Low Risk":
        return "VIP and loyalty program opportunity"

    if risk_level == "High Risk":
        return "Run re-engagement campaign"

    if clv_tier == "Medium":
        return "Encourage repeat purchases"

    return "Standard customer engagement"


# =========================================================
# XGBoost + SHAP
# =========================================================

@lru_cache(maxsize=1)
def get_xgboost_model():
    """Load the trained XGBoost model once."""

    model = XGBoostCLVModel()
    model.load()

    return model


@lru_cache(maxsize=1)
def get_shap_explainer():
    """Create the SHAP TreeExplainer once."""

    model = get_xgboost_model()

    return shap.TreeExplainer(model.model)


FEATURE_DISPLAY_NAMES = {
    "recency": "Purchase Recency",
    "frequency": "Repeat Orders",
    "monetary_value": "Average Purchase Value",
    "T": "Customer Age",
    "log_monetary": "Purchase Value Scale",
    "log_frequency": "Purchase Frequency Scale",
    "purchase_velocity": "Purchase Velocity",
    "tenure_ratio": "Active Tenure Ratio",
    "avg_order_value": "Average Order Value",
}


def build_customer_features(
    customer_id: str,
    db: Session,
) -> pd.DataFrame:
    """
    Rebuild the features used by the trained XGBoost model.

    Product line-items are aggregated into unique purchase orders
    using order_id before customer-level features are calculated.
    """

    query = text(
        """
        SELECT
            customer_id,
            order_id,
            timestamp,
            amount
        FROM transactions
        WHERE customer_id = :customer_id
          AND order_id IS NOT NULL
        ORDER BY timestamp
        """
    )

    transactions = pd.read_sql(
        query,
        db.bind,
        params={"customer_id": customer_id},
    )

    if transactions.empty:
        raise HTTPException(
            status_code=404,
            detail="No transaction history found for customer",
        )

    transactions["timestamp"] = pd.to_datetime(
        transactions["timestamp"],
        errors="coerce",
    )

    transactions["amount"] = pd.to_numeric(
        transactions["amount"],
        errors="coerce",
    )

    transactions = transactions.dropna(
        subset=["order_id", "timestamp", "amount"]
    )

    transactions = transactions[
        transactions["amount"] > 0
    ].copy()

    orders = (
        transactions.groupby(
            ["customer_id", "order_id"],
            as_index=False,
        )
        .agg(
            timestamp=("timestamp", "min"),
            order_amount=("amount", "sum"),
        )
    )

    if orders.empty:
        raise HTTPException(
            status_code=404,
            detail="No valid purchase orders found for customer",
        )

    observation_end = (
        db.query(func.max(Transaction.timestamp))
        .scalar()
    )

    if observation_end is None:
        raise HTTPException(
            status_code=500,
            detail="Unable to determine dataset observation end",
        )

    first_purchase = orders["timestamp"].min()
    last_purchase = orders["timestamp"].max()

    order_count = int(
        orders["order_id"].nunique()
    )

    # BG/NBD-style repeat purchase frequency
    frequency = max(order_count - 1, 0)

    recency = (
        last_purchase - first_purchase
    ).days

    T = (
        observation_end - first_purchase
    ).days

    monetary_value = float(
        orders["order_amount"].mean()
    )

    if frequency <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "SHAP explanation requires a returning customer "
                "with at least two orders"
            ),
        )

    features = {
        "recency": float(recency),
        "frequency": float(frequency),
        "monetary_value": monetary_value,
        "T": float(T),
        "log_monetary": float(np.log1p(monetary_value)),
        "log_frequency": float(np.log1p(frequency)),
        "purchase_velocity": float(
            frequency / (T + 1)
        ),
        "tenure_ratio": float(
            recency / (T + 1)
        ),
        "avg_order_value": monetary_value,
    }

    model = get_xgboost_model()

    feature_columns = [
        str(column)
        for column in model.feature_columns
    ]

    return pd.DataFrame(
        [features],
        columns=feature_columns,
    )


# =========================================================
# Customer 360
# =========================================================

@router.get(
    "/customers/{customer_id}",
    response_model=Customer360Response,
)
async def get_customer_360(
    customer_id: str,
    db: Session = Depends(get_db),
) -> Customer360Response:
    """Return Customer 360 information for one customer."""

    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    prediction = (
        db.query(Prediction)
        .filter(Prediction.customer_id == customer_id)
        .first()
    )

    order_stats = (
        db.query(
            func.sum(Transaction.amount).label(
                "total_spent"
            ),
            func.count(
                func.distinct(Transaction.order_id)
            ).label("order_count"),
            func.min(Transaction.timestamp).label(
                "first_purchase"
            ),
            func.max(Transaction.timestamp).label(
                "last_purchase"
            ),
        )
        .filter(
            Transaction.customer_id == customer_id
        )
        .first()
    )

    total_spent = float(
        order_stats.total_spent or 0
    )

    order_count = int(
        order_stats.order_count or 0
    )

    average_order_value = (
        total_spent / order_count
        if order_count > 0
        else 0.0
    )

    dataset_end = (
        db.query(func.max(Transaction.timestamp))
        .scalar()
    )

    tenure_days = None

    if (
        customer.signup_date is not None
        and dataset_end is not None
    ):
        tenure_days = (
            dataset_end - customer.signup_date
        ).days

    predicted_clv = (
        float(prediction.predicted_clv_90d)
        if (
            prediction
            and prediction.predicted_clv_90d is not None
        )
        else None
    )

    churn_probability = (
        float(prediction.churn_probability)
        if (
            prediction
            and prediction.churn_probability is not None
        )
        else None
    )

    clv_tier = assign_clv_tier(
        predicted_clv
    )

    risk_level = assign_risk_level(
        churn_probability
    )

    action = recommend_action(
        clv_tier,
        risk_level,
    )

    return Customer360Response(
        customer_id=str(customer.customer_id),
        email=customer.email,
        predicted_clv_90d=predicted_clv,
        churn_probability=churn_probability,
        clv_tier=clv_tier,
        risk_level=risk_level,
        total_spent=round(total_spent, 2),
        order_count=order_count,
        average_order_value=round(
            average_order_value,
            2,
        ),
        first_purchase=(
            str(order_stats.first_purchase)
            if order_stats.first_purchase
            else None
        ),
        last_purchase=(
            str(order_stats.last_purchase)
            if order_stats.last_purchase
            else None
        ),
        tenure_days=tenure_days,
        recommended_action=action,
    )


# =========================================================
# SHAP Explainability
# =========================================================

@router.get(
    "/customers/{customer_id}/explanation",
    response_model=CustomerExplanationResponse,
)
async def get_customer_explanation(
    customer_id: str,
    db: Session = Depends(get_db),
) -> CustomerExplanationResponse:
    """
    Explain the XGBoost component of a customer's CLV prediction.

    Positive SHAP values push the XGBoost prediction upward.
    Negative values push it downward.

    The XGBoost target is log-transformed, so these SHAP values
    represent relative model impact rather than direct dollar amounts.
    """

    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    features = build_customer_features(
        customer_id,
        db,
    )

    explainer = get_shap_explainer()

    shap_values = explainer.shap_values(
        features
    )

    impacts = shap_values[0]

    factors = []

    for index, feature in enumerate(
        features.columns
    ):
        feature_name = str(feature)

        value = float(
            features.iloc[0, index]
        )

        impact = float(
            impacts[index]
        )

        factors.append(
            ExplanationFactor(
                feature=feature_name,
                display_name=FEATURE_DISPLAY_NAMES.get(
                    feature_name,
                    feature_name,
                ),
                value=round(value, 4),
                shap_value=round(impact, 4),
                direction=(
                    "increases"
                    if impact > 0
                    else (
                        "decreases"
                        if impact < 0
                        else "neutral"
                    )
                ),
            )
        )

    factors.sort(
        key=lambda factor: abs(
            factor.shap_value
        ),
        reverse=True,
    )

    return CustomerExplanationResponse(
        customer_id=customer_id,
        model="XGBoost",
        explanation_scope=(
            "Local SHAP explanation of the XGBoost "
            "component of the CLV prediction"
        ),
        top_factors=factors[:5],
    )