"""Prediction API endpoints."""

import io
from io import StringIO
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Customer,
    Prediction,
    RFMFeature,
    Transaction,
)
from ml.probabilistic import ProbabilisticCLVModel
from ml.xgboost_model import XGBoostCLVModel


router = APIRouter()


# =========================================================
# Response Models
# =========================================================


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
    """Dashboard KPI summary."""

    average_clv: float
    total_active_customers: int
    average_churn_risk: float
    total_revenue: float


class CustomPredictionItem(BaseModel):
    """Prediction result for one uploaded customer."""

    customer_id: str
    recency: int
    frequency: int
    monetary_value: float
    tenure: int
    predicted_clv_90d: float
    churn_probability: float
    clv_tier: str


class CustomPredictionSummary(BaseModel):
    """Summary of a custom dataset prediction."""

    total_customers: int
    average_clv: float
    total_future_clv: float
    average_churn_risk: float
    high_value_count: int


class CustomPredictionResponse(BaseModel):
    """Complete custom prediction response."""

    summary: CustomPredictionSummary
    predictions: list[CustomPredictionItem]


# =========================================================
# Existing CLV Predictions
# =========================================================


@router.get(
    "/predict/clv",
    response_model=list[CLVPredictionResponse],
)
async def get_clv_predictions(
    customer_id: Optional[str] = Query(
        None,
        description="Filter by customer ID",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Max results",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset",
    ),
    db: Session = Depends(get_db),
) -> list[CLVPredictionResponse]:
    """Get stored CLV predictions."""

    query = (
        db.query(
            Prediction.customer_id,
            Prediction.predicted_clv_90d,
            Prediction.churn_probability,
            RFMFeature.recency,
            RFMFeature.frequency,
            RFMFeature.monetary_value,
        )
        .outerjoin(
            RFMFeature,
            Prediction.customer_id
            == RFMFeature.customer_id,
        )
    )

    if customer_id:
        query = query.filter(
            Prediction.customer_id == customer_id
        )

    results = (
        query.offset(offset)
        .limit(limit)
        .all()
    )

    if customer_id and not results:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No predictions found for customer "
                f"'{customer_id}'"
            ),
        )

    return [
        CLVPredictionResponse(
            customer_id=str(row.customer_id),
            predicted_clv_90d=(
                float(row.predicted_clv_90d)
                if row.predicted_clv_90d is not None
                else None
            ),
            churn_probability=(
                float(row.churn_probability)
                if row.churn_probability is not None
                else None
            ),
            recency=row.recency,
            frequency=row.frequency,
            monetary_value=(
                float(row.monetary_value)
                if row.monetary_value is not None
                else None
            ),
        )
        for row in results
    ]


# =========================================================
# Dashboard Summary
# =========================================================


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """Get dashboard KPI metrics."""

    avg_clv = (
        db.query(
            func.avg(
                Prediction.predicted_clv_90d
            )
        ).scalar()
        or 0.0
    )

    total_customers = (
        db.query(
            func.count(
                Customer.customer_id
            )
        ).scalar()
        or 0
    )

    avg_churn = (
        db.query(
            func.avg(
                Prediction.churn_probability
            )
        ).scalar()
        or 0.0
    )

    total_revenue = (
        db.query(
            func.sum(
                Transaction.amount
            )
        ).scalar()
        or 0.0
    )

    return DashboardSummaryResponse(
        average_clv=round(
            float(avg_clv),
            2,
        ),
        total_active_customers=int(
            total_customers
        ),
        average_churn_risk=round(
            float(avg_churn),
            4,
        ),
        total_revenue=round(
            float(total_revenue),
            2,
        ),
    )


# =========================================================
# Uploaded File Reader
# =========================================================


def read_uploaded_file(
    contents: bytes,
) -> pd.DataFrame:
    """
    Read uploaded CSV, TSV, TXT or Excel data.

    The function tries multiple encodings and delimiters
    so that common customer datasets can be uploaded
    without manual conversion.
    """

    if (
        not contents
        or len(contents.strip()) == 0
    ):
        raise ValueError(
            "The uploaded file is empty."
        )

    clean_contents = contents.replace(
        b"\x00",
        b"",
    )

    if (
        not clean_contents
        or len(clean_contents.strip()) == 0
    ):
        raise ValueError(
            "The uploaded file contains no readable data."
        )

    encodings = [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "utf-16le",
        "utf-16be",
        "latin-1",
        "cp1252",
        "iso-8859-1",
    ]

    decoded_text = None

    for encoding in encodings:
        try:
            text_value = (
                clean_contents
                .decode(encoding)
                .replace("\x00", "")
            )

            if text_value.strip():
                decoded_text = text_value
                break

        except Exception:
            continue

    if decoded_text is None:
        decoded_text = (
            clean_contents
            .decode(
                "utf-8",
                errors="ignore",
            )
            .replace("\x00", "")
        )

    if not decoded_text.strip():
        raise ValueError(
            "The uploaded file contains no parseable text."
        )

    separators = [
        ",",
        ";",
        "\t",
        "|",
    ]

    dataframe = None

    for separator in separators:
        try:
            candidate = pd.read_csv(
                StringIO(decoded_text),
                sep=separator,
                on_bad_lines="skip",
                engine="python",
            )

            if (
                candidate.shape[1] >= 2
                and len(candidate) >= 1
            ):
                dataframe = candidate
                break

        except Exception:
            continue

    # Excel fallback
    if dataframe is None or dataframe.empty:
        try:
            dataframe = pd.read_excel(
                io.BytesIO(contents)
            )
        except Exception:
            pass

    if (
        dataframe is None
        or dataframe.empty
    ):
        raise ValueError(
            "No usable tabular data was found."
        )

    return dataframe


# =========================================================
# Column Helpers
# =========================================================


def normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize uploaded column names."""

    df = df.copy()

    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for column in df.columns
    ]

    return df


def find_first_column(
    columns: list[str],
    aliases: list[str],
) -> Optional[str]:
    """Return the first matching alias."""

    for alias in aliases:
        if alias in columns:
            return alias

    return None


# =========================================================
# Uploaded Data → Customer Features
# =========================================================


def auto_map_rfm(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert uploaded data into one row per customer.

    Supported formats:

    Transaction format:
        customer_id, timestamp, amount

    RFM format:
        customer_id, recency, frequency,
        monetary_value, tenure/T
    """

    df = normalize_columns(df)

    columns = list(df.columns)

    # -----------------------------------------------------
    # Aliases
    # -----------------------------------------------------

    id_keys = [
        "customer_id",
        "customerid",
        "cust_id",
        "id",
        "user_id",
        "userid",
        "client_id",
        "customer",
        "account_id",
        "member_id",
    ]

    time_keys = [
        "timestamp",
        "date",
        "order_date",
        "transaction_date",
        "created_at",
        "invoice_date",
        "invoicedate",
        "purchased_at",
        "purchase_date",
        "time",
    ]

    amount_keys = [
        "amount",
        "sales",
        "revenue",
        "transaction_amount",
        "order_amount",
        "total_amount",
    ]

    recency_keys = [
        "recency",
        "recency_days",
        "days_since_last_order",
        "days_since_last_purchase",
        "last_purchase_days",
        "days_ago",
        "days_since_purchase",
    ]

    frequency_keys = [
        "frequency",
        "order_count",
        "transaction_count",
        "purchase_count",
        "num_orders",
        "total_orders",
        "orders",
        "purchases",
        "count",
    ]

    monetary_keys = [
        "monetary_value",
        "monetary",
        "avg_order_value",
        "average_order_value",
        "total_spent",
        "spend",
        "value",
        "price",
    ]

    tenure_keys = [
        "t",
        "tenure",
        "tenure_days",
        "signup_days",
        "account_age",
        "customer_age",
        "days_as_customer",
    ]

    customer_column = find_first_column(
        columns,
        id_keys,
    )

    time_column = find_first_column(
        columns,
        time_keys,
    )

    amount_column = find_first_column(
        columns,
        amount_keys,
    )

    # =====================================================
    # TRANSACTION FORMAT
    #
    # Important:
    # Detect transaction format BEFORE mapping amount
    # into monetary_value.
    # =====================================================

    if (
        customer_column is not None
        and time_column is not None
        and amount_column is not None
    ):

        transactions = df[
            [
                customer_column,
                time_column,
                amount_column,
            ]
        ].copy()

        transactions = transactions.rename(
            columns={
                customer_column:
                    "customer_id",
                time_column:
                    "timestamp",
                amount_column:
                    "amount",
            }
        )

        transactions["customer_id"] = (
            transactions["customer_id"]
            .astype(str)
            .str.strip()
        )

        transactions["timestamp"] = (
            pd.to_datetime(
                transactions["timestamp"],
                errors="coerce",
            )
        )

        transactions["amount"] = (
            pd.to_numeric(
                transactions["amount"],
                errors="coerce",
            )
        )

        transactions = (
            transactions
            .dropna(
                subset=[
                    "customer_id",
                    "timestamp",
                    "amount",
                ]
            )
            .copy()
        )

        transactions = transactions[
            transactions["customer_id"]
            != ""
        ].copy()

        transactions = transactions[
            transactions["amount"] > 0
        ].copy()

        if transactions.empty:
            raise ValueError(
                "No valid positive transactions "
                "were found after cleaning."
            )

        observation_end = (
            transactions[
                "timestamp"
            ].max()
            + pd.Timedelta(days=1)
        )

        # -------------------------------------------------
        # Aggregate transactions to ONE ROW PER CUSTOMER
        # -------------------------------------------------

        customer_features = (
            transactions
            .groupby(
                "customer_id",
                as_index=False,
            )
            .agg(
                first_purchase=(
                    "timestamp",
                    "min",
                ),
                last_purchase=(
                    "timestamp",
                    "max",
                ),
                purchase_count=(
                    "timestamp",
                    "count",
                ),
                monetary_value=(
                    "amount",
                    "mean",
                ),
            )
        )

        # Recency used by the probabilistic model:
        # time between first and most recent purchase.
        customer_features["recency"] = (
            customer_features[
                "last_purchase"
            ]
            - customer_features[
                "first_purchase"
            ]
        ).dt.days

        # Repeat purchase frequency.
        customer_features["frequency"] = (
            customer_features[
                "purchase_count"
            ]
            - 1
        ).clip(lower=0)

        # Customer age at the observation date.
        customer_features["T"] = (
            observation_end
            - customer_features[
                "first_purchase"
            ]
        ).dt.days

        customer_features[
            "recency"
        ] = (
            customer_features[
                "recency"
            ]
            .clip(lower=0)
            .astype(int)
        )

        customer_features[
            "frequency"
        ] = (
            customer_features[
                "frequency"
            ]
            .clip(lower=0)
            .astype(int)
        )

        customer_features["T"] = (
            customer_features["T"]
            .clip(lower=1)
            .astype(int)
        )

        customer_features[
            "monetary_value"
        ] = (
            pd.to_numeric(
                customer_features[
                    "monetary_value"
                ],
                errors="coerce",
            )
            .fillna(50.0)
        )

        return customer_features[
            [
                "customer_id",
                "recency",
                "frequency",
                "monetary_value",
                "T",
            ]
        ]

    # =====================================================
    # RFM FORMAT
    # =====================================================

    rename_map = {}

    customer_column = find_first_column(
        columns,
        id_keys,
    )

    recency_column = find_first_column(
        columns,
        recency_keys,
    )

    frequency_column = find_first_column(
        columns,
        frequency_keys,
    )

    monetary_column = find_first_column(
        columns,
        monetary_keys,
    )

    tenure_column = find_first_column(
        columns,
        tenure_keys,
    )

    if customer_column is not None:
        rename_map[
            customer_column
        ] = "customer_id"

    if recency_column is not None:
        rename_map[
            recency_column
        ] = "recency"

    if frequency_column is not None:
        rename_map[
            frequency_column
        ] = "frequency"

    if monetary_column is not None:
        rename_map[
            monetary_column
        ] = "monetary_value"

    if tenure_column is not None:
        rename_map[
            tenure_column
        ] = "T"

    df = df.rename(
        columns=rename_map
    )

    # -----------------------------------------------------
    # Customer ID
    # -----------------------------------------------------

    if "customer_id" not in df.columns:
        df["customer_id"] = [
            f"CUST_{index + 1}"
            for index in range(len(df))
        ]

    df["customer_id"] = (
        df["customer_id"]
        .astype(str)
        .str.strip()
    )

    # -----------------------------------------------------
    # Numeric fallbacks
    # -----------------------------------------------------

    numeric_columns = (
        df.select_dtypes(
            include=[np.number]
        )
        .columns
        .tolist()
    )

    if "recency" not in df.columns:
        if numeric_columns:
            df["recency"] = (
                df[
                    numeric_columns[0]
                ]
            )
        else:
            df["recency"] = 30

    if "frequency" not in df.columns:

        candidates = [
            column
            for column
            in numeric_columns
            if column
            != "recency"
        ]

        if candidates:
            df["frequency"] = (
                df[
                    candidates[0]
                ]
            )
        else:
            df["frequency"] = 1

    if (
        "monetary_value"
        not in df.columns
    ):

        candidates = [
            column
            for column
            in numeric_columns
            if column
            not in {
                "recency",
                "frequency",
            }
        ]

        if candidates:
            df[
                "monetary_value"
            ] = df[
                candidates[0]
            ]
        else:
            df[
                "monetary_value"
            ] = 50.0

    if "T" not in df.columns:
        df["T"] = (
            pd.to_numeric(
                df["recency"],
                errors="coerce",
            )
            .fillna(30)
            + 60
        )

    return df[
        [
            "customer_id",
            "recency",
            "frequency",
            "monetary_value",
            "T",
        ]
    ]


# =========================================================
# Custom Dataset Prediction
# =========================================================


@router.post(
    "/predict/custom",
    response_model=CustomPredictionResponse,
)
async def predict_custom_dataset(
    file: UploadFile = File(...),
) -> CustomPredictionResponse:
    """
    Upload a customer or transaction dataset
    and generate CLV + churn predictions.
    """

    # -----------------------------------------------------
    # Read uploaded file
    # -----------------------------------------------------

    try:
        contents = await file.read()

        raw_df = read_uploaded_file(
            contents
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Failed to parse dataset: "
                f"{str(error)}"
            ),
        )

    if (
        raw_df is None
        or raw_df.empty
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded dataset "
                "contains no usable rows."
            ),
        )

    # -----------------------------------------------------
    # Convert to one row per customer
    # -----------------------------------------------------

    try:
        df = auto_map_rfm(
            raw_df
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No customers could be created "
                "from the uploaded dataset."
            ),
        )

    # -----------------------------------------------------
    # Data Cleaning
    # -----------------------------------------------------

    df["customer_id"] = (
        df["customer_id"]
        .astype(str)
        .str.strip()
    )

    df["recency"] = (
        pd.to_numeric(
            df["recency"],
            errors="coerce",
        )
        .fillna(30)
        .clip(lower=0)
        .astype(int)
    )

    df["frequency"] = (
        pd.to_numeric(
            df["frequency"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    df["monetary_value"] = (
        pd.to_numeric(
            df["monetary_value"],
            errors="coerce",
        )
        .fillna(50.0)
    )

    df["monetary_value"] = (
        np.where(
            df["monetary_value"]
            <= 0,
            10.0,
            df["monetary_value"],
        )
    )

    df["T"] = (
        pd.to_numeric(
            df["T"],
            errors="coerce",
        )
        .fillna(
            df["recency"] + 60
        )
        .astype(int)
    )

    df["T"] = np.where(
        df["T"] <= 0,
        df["recency"] + 30,
        df["T"],
    )

    # Important consistency rule
    df["T"] = np.maximum(
        df["T"],
        df["recency"],
    )

    valid_df = df.copy()

    # -----------------------------------------------------
    # Feature Engineering
    # -----------------------------------------------------

    valid_df[
        "log_monetary"
    ] = np.log1p(
        valid_df[
            "monetary_value"
        ]
    )

    valid_df[
        "log_frequency"
    ] = np.log1p(
        valid_df[
            "frequency"
        ]
    )

    valid_df[
        "purchase_velocity"
    ] = (
        valid_df["frequency"]
        / (
            valid_df["T"]
            + 1
        )
    )

    valid_df[
        "tenure_ratio"
    ] = (
        valid_df["recency"]
        / (
            valid_df["T"]
            + 1
        )
    )

    # Monetary value already represents
    # average transaction value.
    valid_df[
        "avg_order_value"
    ] = valid_df[
        "monetary_value"
    ]

    feature_columns = [
        "recency",
        "frequency",
        "monetary_value",
        "T",
        "log_monetary",
        "log_frequency",
        "purchase_velocity",
        "tenure_ratio",
        "avg_order_value",
    ]

    # =====================================================
    # XGBoost Prediction
    # =====================================================

    try:
        xgb_model = (
            XGBoostCLVModel()
        )

        xgb_model.load()

        xgb_predictions = (
            xgb_model.predict(
                valid_df[
                    feature_columns
                ]
            )
        )

    except Exception:

        # Safe fallback if the stored model
        # cannot be loaded.
        xgb_predictions = (
            valid_df[
                "monetary_value"
            ]
            * (
                valid_df[
                    "frequency"
                ]
                + 1
            )
            * 0.8
        ).values

    # =====================================================
    # Probabilistic Prediction
    # =====================================================

    try:
        probabilistic_model = (
            ProbabilisticCLVModel()
        )

        probabilistic_model.fit(
            valid_df
        )

        probabilistic_predictions = (
            probabilistic_model.predict(
                valid_df
            )
        )

        probabilistic_clv = (
            probabilistic_predictions[
                "predicted_clv_90d"
            ].values
        )

        churn_probability = (
            probabilistic_predictions[
                "churn_probability"
            ].values
        )

    except Exception:

        probabilistic_clv = (
            valid_df[
                "monetary_value"
            ]
            * (
                valid_df[
                    "frequency"
                ]
                + 1
            )
        ).values

        # Fallback churn estimate
        inactivity = (
            valid_df["T"]
            - valid_df["recency"]
        )

        churn_probability = (
            np.clip(
                inactivity
                / (
                    valid_df["T"]
                    + 1
                ),
                0.0,
                1.0,
            )
            .values
        )

    # -----------------------------------------------------
    # Store model outputs
    # -----------------------------------------------------

    valid_df[
        "xgb_clv"
    ] = np.clip(
        xgb_predictions,
        0,
        None,
    )

    valid_df[
        "prob_clv"
    ] = np.clip(
        probabilistic_clv,
        0,
        None,
    )

    valid_df[
        "churn_probability"
    ] = np.clip(
        churn_probability,
        0.0,
        1.0,
    ).round(4)

    # =====================================================
    # Ensemble CLV
    # =====================================================

    valid_df[
        "predicted_clv_90d"
    ] = (
        0.6
        * valid_df[
            "prob_clv"
        ]
        + 0.4
        * valid_df[
            "xgb_clv"
        ]
    ).round(2)

    valid_df[
        "predicted_clv_90d"
    ] = valid_df[
        "predicted_clv_90d"
    ].clip(
        lower=0
    )

    # =====================================================
    # CLV Tiers
    # =====================================================

    percentile_75 = (
        valid_df[
            "predicted_clv_90d"
        ].quantile(0.75)
    )

    percentile_25 = (
        valid_df[
            "predicted_clv_90d"
        ].quantile(0.25)
    )

    def get_tier(
        clv: float,
    ) -> str:

        if clv >= max(
            1000,
            percentile_75,
        ):
            return "High"

        if clv >= max(
            300,
            percentile_25,
        ):
            return "Medium"

        return "Low"

    valid_df[
        "clv_tier"
    ] = valid_df[
        "predicted_clv_90d"
    ].apply(
        get_tier
    )

    # =====================================================
    # Summary
    # =====================================================

    total_customers = int(
        valid_df[
            "customer_id"
        ].nunique()
    )

    average_clv = float(
        round(
            valid_df[
                "predicted_clv_90d"
            ].mean(),
            2,
        )
    )

    total_future_clv = float(
        round(
            valid_df[
                "predicted_clv_90d"
            ].sum(),
            2,
        )
    )

    average_churn = float(
        round(
            valid_df[
                "churn_probability"
            ].mean(),
            4,
        )
    )

    high_value_count = int(
        (
            valid_df[
                "clv_tier"
            ]
            == "High"
        ).sum()
    )

    summary = (
        CustomPredictionSummary(
            total_customers=(
                total_customers
            ),
            average_clv=(
                average_clv
            ),
            total_future_clv=(
                total_future_clv
            ),
            average_churn_risk=(
                average_churn
            ),
            high_value_count=(
                high_value_count
            ),
        )
    )

    # =====================================================
    # Customer Prediction Rows
    # =====================================================

    prediction_items = []

    for _, row in valid_df.iterrows():

        prediction_items.append(
            CustomPredictionItem(
                customer_id=str(
                    row[
                        "customer_id"
                    ]
                ),
                recency=int(
                    row[
                        "recency"
                    ]
                ),
                frequency=int(
                    row[
                        "frequency"
                    ]
                ),
                monetary_value=float(
                    round(
                        row[
                            "monetary_value"
                        ],
                        2,
                    )
                ),
                tenure=int(
                    row["T"]
                ),
                predicted_clv_90d=float(
                    row[
                        "predicted_clv_90d"
                    ]
                ),
                churn_probability=float(
                    row[
                        "churn_probability"
                    ]
                ),
                clv_tier=str(
                    row[
                        "clv_tier"
                    ]
                ),
            )
        )

    return CustomPredictionResponse(
        summary=summary,
        predictions=prediction_items,
    )