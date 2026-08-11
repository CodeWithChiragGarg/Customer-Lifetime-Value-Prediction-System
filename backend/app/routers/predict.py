import io
from io import StringIO
from typing import Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Prediction, RFMFeature, Transaction
from ml.probabilistic import ProbabilisticCLVModel
from ml.xgboost_model import XGBoostCLVModel


router = APIRouter()


class CLVPredictionResponse(BaseModel):
    """Response schema for a single CLV prediction."""

    customer_id: str
    predicted_clv_90d: Optional[float] = None
    churn_probability: Optional[float] = None
    recency: Optional[int] = None
    frequency: Optional[int] = None
    monetary_value: Optional[float] = None

    class Config:
        from_attributes = True


class DashboardSummaryResponse(BaseModel):
    """Response schema for dashboard KPI summary."""

    average_clv: float
    total_active_customers: int
    average_churn_risk: float
    total_revenue: float


class CustomPredictionItem(BaseModel):
    customer_id: str
    recency: int
    frequency: int
    monetary_value: float
    tenure: int
    predicted_clv_90d: float
    churn_probability: float
    clv_tier: str


class CustomPredictionSummary(BaseModel):
    total_customers: int
    average_clv: float
    total_future_clv: float
    average_churn_risk: float
    high_value_count: int


class CustomPredictionResponse(BaseModel):
    summary: CustomPredictionSummary
    predictions: list[CustomPredictionItem]


@router.get("/predict/clv", response_model=list[CLVPredictionResponse])
async def get_clv_predictions(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> list[CLVPredictionResponse]:
    """Get CLV predictions, optionally filtered by customer ID."""
    query = (
        db.query(
            Prediction.customer_id,
            Prediction.predicted_clv_90d,
            Prediction.churn_probability,
            RFMFeature.recency,
            RFMFeature.frequency,
            RFMFeature.monetary_value,
        )
        .outerjoin(RFMFeature, Prediction.customer_id == RFMFeature.customer_id)
    )

    if customer_id:
        query = query.filter(Prediction.customer_id == customer_id)

    results = query.offset(offset).limit(limit).all()

    if customer_id and not results:
        raise HTTPException(
            status_code=404,
            detail=f"No predictions found for customer '{customer_id}'",
        )

    return [
        CLVPredictionResponse(
            customer_id=row.customer_id,
            predicted_clv_90d=float(row.predicted_clv_90d) if row.predicted_clv_90d else None,
            churn_probability=float(row.churn_probability) if row.churn_probability else None,
            recency=row.recency,
            frequency=row.frequency,
            monetary_value=float(row.monetary_value) if row.monetary_value else None,
        )
        for row in results
    ]


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """Get aggregated KPI metrics for the dashboard."""
    avg_clv = db.query(func.avg(Prediction.predicted_clv_90d)).scalar() or 0.0
    total_customers = db.query(func.count(Customer.customer_id)).scalar() or 0
    avg_churn = db.query(func.avg(Prediction.churn_probability)).scalar() or 0.0
    total_revenue = db.query(func.sum(Transaction.amount)).scalar() or 0.0

    return DashboardSummaryResponse(
        average_clv=round(float(avg_clv), 2),
        total_active_customers=total_customers,
        average_churn_risk=round(float(avg_churn), 4),
        total_revenue=round(float(total_revenue), 2),
    )


def read_uploaded_file(contents: bytes) -> pd.DataFrame:
    """Read CSV, TSV, TXT, or Excel file bytes with auto-encoding, null-byte cleaning, and delimiter detection."""
    if not contents or len(contents.strip()) == 0:
        raise ValueError("The uploaded file is empty (0 bytes). Please select a CSV file containing customer data, or click '⚡ Load Sample CSV Dataset'.")

    # Remove null bytes which cause C/Python CSV parsing failures
    clean_contents = contents.replace(b"\x00", b"")
    if not clean_contents or len(clean_contents.strip()) == 0:
        raise ValueError("The uploaded file contains no readable text. Please select a valid CSV file.")

    encodings = ["utf-8-sig", "utf-8", "utf-16", "utf-16le", "utf-16be", "latin-1", "cp1252", "iso-8859-1"]
    decoded_text = None
    for enc in encodings:
        try:
            temp_text = clean_contents.decode(enc).replace("\x00", "")
            if temp_text and len(temp_text.strip()) > 0:
                decoded_text = temp_text
                break
        except Exception:
            continue

    if decoded_text is None:
        decoded_text = clean_contents.decode("utf-8", errors="ignore").replace("\x00", "")

    if not decoded_text or len(decoded_text.strip()) == 0:
        raise ValueError("The uploaded file contains no parseable text.")

    # Try delimiter parsing
    separators = [",", ";", "\t", "|"]
    df = None
    for sep in separators:
        try:
            temp = pd.read_csv(StringIO(decoded_text), sep=sep, on_bad_lines="skip", engine="python")
            if temp.shape[1] >= 1 and len(temp) >= 1:
                df = temp
                break
        except Exception:
            continue

    if df is None:
        try:
            df = pd.read_csv(StringIO(decoded_text), on_bad_lines="skip", engine="python")
        except Exception:
            pass

    # Try Excel parsing fallback
    if df is None or df.empty:
        try:
            df = pd.read_excel(io.BytesIO(contents))
        except Exception:
            pass

    if df is None or df.empty:
        raise ValueError("No tabular data or columns found in file. Please ensure your CSV contains customer rows.")

    return df


def auto_map_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """Map any arbitrary CSV column names to customer_id, recency, frequency, monetary_value, T."""
    cols_orig = list(df.columns)
    norm_map = {c: str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in cols_orig}
    df = df.rename(columns=norm_map)

    # Synonyms mapping
    id_keys = ["customer_id", "customerid", "cust_id", "id", "user_id", "userid", "client_id", "customer", "account_id", "member_id"]
    recency_keys = ["recency", "recency_days", "days_since_last_order", "days_since_last_purchase", "last_purchase_days", "days_ago", "days_since_purchase"]
    freq_keys = ["frequency", "order_count", "transaction_count", "purchase_count", "num_orders", "total_orders", "orders", "purchases", "count"]
    monetary_keys = ["monetary_value", "monetary", "avg_order_value", "total_spent", "revenue", "amount", "spend", "sales", "value", "price", "total_amount"]
    tenure_keys = ["t", "tenure", "tenure_days", "signup_days", "account_age", "customer_age", "days_as_customer"]
    time_keys = ["timestamp", "date", "order_date", "transaction_date", "created_at", "invoice_date", "purchased_at", "time"]

    mapped = {}
    cols = list(df.columns)
    for c in cols:
        if c in id_keys and "customer_id" not in mapped:
            mapped[c] = "customer_id"
        elif c in recency_keys and "recency" not in mapped:
            mapped[c] = "recency"
        elif c in freq_keys and "frequency" not in mapped:
            mapped[c] = "frequency"
        elif c in monetary_keys and "monetary_value" not in mapped:
            mapped[c] = "monetary_value"
        elif c in tenure_keys and "T" not in mapped:
            mapped[c] = "T"
        elif c in time_keys and "timestamp" not in mapped:
            mapped[c] = "timestamp"

    df = df.rename(columns=mapped)

    # Check if transaction format
    if "amount" in df.columns and ("timestamp" in df.columns or "date" in df.columns):
        t_col = "timestamp" if "timestamp" in df.columns else "date"
        df[t_col] = pd.to_datetime(df[t_col], errors="coerce")
        if "customer_id" not in df.columns:
            df["customer_id"] = "CUST_" + df.index.astype(str)

        ref = df[t_col].max() + pd.Timedelta(days=1)
        rfm = (
            df.groupby("customer_id")
            .agg(
                recency=(t_col, lambda x: max(0, int((ref - x.max()).days)) if pd.notnull(x.max()) else 30),
                frequency=(t_col, lambda x: max(0, len(x) - 1)),
                monetary_value=("amount", "mean"),
                T=(t_col, lambda x: max(1, int((ref - x.min()).days)) if pd.notnull(x.min()) else 180),
            )
            .reset_index()
        )
        return rfm

    # Ensure customer_id
    if "customer_id" not in df.columns:
        df["customer_id"] = ["CUST_" + str(i+1) for i in range(len(df))]

    # Ensure numeric fields fallback intelligently from any available numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if "recency" not in df.columns:
        if numeric_cols:
            df["recency"] = df[numeric_cols[0]]
        else:
            df["recency"] = 30

    if "frequency" not in df.columns:
        if len(numeric_cols) > 1:
            df["frequency"] = df[numeric_cols[1]]
        else:
            df["frequency"] = 1

    if "monetary_value" not in df.columns:
        if len(numeric_cols) > 2:
            df["monetary_value"] = df[numeric_cols[2]]
        elif numeric_cols:
            df["monetary_value"] = df[numeric_cols[0]]
        else:
            df["monetary_value"] = 50.0

    if "T" not in df.columns:
        df["T"] = df["recency"] + 60

    return df


@router.post("/predict/custom", response_model=CustomPredictionResponse)
async def predict_custom_dataset(file: UploadFile = File(...)) -> CustomPredictionResponse:
    """Upload ANY dataset (CSV/TSV/TXT) to compute CLV predictions & churn probability."""
    try:
        contents = await file.read()
        raw_df = read_uploaded_file(contents)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse dataset file: {str(e)}")

    if raw_df is None or raw_df.empty:
        raise HTTPException(status_code=400, detail="The uploaded dataset file contains no customer rows.")

    # Auto map RFM columns
    df = auto_map_rfm(raw_df)

    # Clean data & enforce numeric safety
    df["customer_id"] = df["customer_id"].astype(str)
    df["recency"] = pd.to_numeric(df["recency"], errors="coerce").fillna(30).clip(lower=0).astype(int)
    df["frequency"] = pd.to_numeric(df["frequency"], errors="coerce").fillna(1).clip(lower=0).astype(int)
    df["monetary_value"] = pd.to_numeric(df["monetary_value"], errors="coerce").fillna(50.0)
    df["monetary_value"] = np.where(df["monetary_value"] <= 0, 10.0, df["monetary_value"])
    df["T"] = pd.to_numeric(df["T"], errors="coerce").fillna(df["recency"] + 60).astype(int)
    df["T"] = np.where(df["T"] <= 0, df["recency"] + 30, df["T"])

    valid_df = df.copy()

    # Feature engineering
    valid_df["log_monetary"] = np.log1p(valid_df["monetary_value"])
    valid_df["log_frequency"] = np.log1p(valid_df["frequency"])
    valid_df["purchase_velocity"] = valid_df["frequency"] / (valid_df["recency"] + 1)
    valid_df["tenure_ratio"] = valid_df["recency"] / (valid_df["T"] + 1)
    valid_df["avg_order_value"] = valid_df["monetary_value"] / (valid_df["frequency"] + 1)

    feature_cols = [
        "recency", "frequency", "monetary_value", "T",
        "log_monetary", "log_frequency", "purchase_velocity",
        "tenure_ratio", "avg_order_value"
    ]

    # Model inference (Fail-safe XGBoost)
    xgb_preds = None
    try:
        xgb_model = XGBoostCLVModel()
        xgb_model.load()
        xgb_preds = xgb_model.predict(valid_df[feature_cols])
    except Exception:
        try:
            valid_df["target"] = valid_df["monetary_value"] * (valid_df["frequency"] + 1)
            xgb_model = XGBoostCLVModel()
            xgb_model.fit(valid_df[feature_cols], valid_df["target"])
            xgb_preds = xgb_model.predict(valid_df[feature_cols])
        except Exception:
            xgb_preds = (valid_df["monetary_value"] * (valid_df["frequency"] + 1) * 0.8).values

    # Model inference (Fail-safe Probabilistic BG/NBD)
    prob_clv = None
    churn_prob = None
    try:
        prob_model = ProbabilisticCLVModel()
        prob_model.fit(valid_df)
        prob_preds_df = prob_model.predict(valid_df)
        prob_clv = prob_preds_df["predicted_clv_90d"].values
        churn_prob = prob_preds_df["churn_probability"].values
    except Exception:
        prob_clv = (valid_df["monetary_value"] * (valid_df["frequency"] + 1)).values
        churn_prob = np.clip(valid_df["recency"] / (valid_df["T"] + 1), 0.0, 1.0).values

    valid_df["xgb_clv"] = xgb_preds
    valid_df["prob_clv"] = prob_clv
    valid_df["churn_probability"] = np.clip(churn_prob, 0.0, 1.0).round(4)

    # Ensembled prediction
    valid_df["predicted_clv_90d"] = (
        0.6 * valid_df["prob_clv"] + 0.4 * valid_df["xgb_clv"]
    ).round(2)
    valid_df["predicted_clv_90d"] = valid_df["predicted_clv_90d"].clip(lower=0)

    # CLV Tiers
    p75 = valid_df["predicted_clv_90d"].quantile(0.75)
    p25 = valid_df["predicted_clv_90d"].quantile(0.25)

    def get_tier(clv):
        if clv >= max(1000, p75):
            return "High"
        elif clv >= max(300, p25):
            return "Medium"
        return "Low"

    valid_df["clv_tier"] = valid_df["predicted_clv_90d"].apply(get_tier)

    # Summary Stats
    total_cust = len(valid_df)
    avg_clv = float(round(valid_df["predicted_clv_90d"].mean(), 2))
    total_future = float(round(valid_df["predicted_clv_90d"].sum(), 2))
    avg_churn = float(round(valid_df["churn_probability"].mean(), 4))
    high_count = int((valid_df["clv_tier"] == "High").sum())

    summary = CustomPredictionSummary(
        total_customers=total_cust,
        average_clv=avg_clv,
        total_future_clv=total_future,
        average_churn_risk=avg_churn,
        high_value_count=high_count,
    )

    items = [
        CustomPredictionItem(
            customer_id=str(row["customer_id"]),
            recency=int(row["recency"]),
            frequency=int(row["frequency"]),
            monetary_value=float(round(row["monetary_value"], 2)),
            tenure=int(row["T"]),
            predicted_clv_90d=float(row["predicted_clv_90d"]),
            churn_probability=float(row["churn_probability"]),
            clv_tier=str(row["clv_tier"]),
        )
        for _, row in valid_df.iterrows()
    ]

    return CustomPredictionResponse(summary=summary, predictions=items)
