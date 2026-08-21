"""Model training orchestrator — trains BG/NBD, Gamma-Gamma and XGBoost models."""

import sys
import logging
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Prediction
from ml.probabilistic import ProbabilisticCLVModel
from ml.xgboost_model import XGBoostCLVModel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def load_training_data(db) -> pd.DataFrame:
    """
    Build customer-level features from invoice-level purchase events.

    BG/NBD definitions:
    - frequency: number of repeat orders
    - recency: days between first and last order
    - T: days between first order and observation-period end
    - monetary_value: average order value
    """

    # ---------------------------------------------------------
    # Load line-item transactions
    # ---------------------------------------------------------

    query = text("""
        SELECT
            customer_id,
            order_id,
            timestamp,
            amount
        FROM transactions
        WHERE order_id IS NOT NULL
        ORDER BY customer_id, timestamp
    """)

    transactions = pd.read_sql(query, db.bind)

    if transactions.empty:
        logger.warning("No transactions available for training.")
        return pd.DataFrame()

    transactions["timestamp"] = pd.to_datetime(
        transactions["timestamp"],
        errors="coerce",
    )

    transactions["amount"] = pd.to_numeric(
        transactions["amount"],
        errors="coerce",
    )

    transactions = transactions.dropna(
        subset=[
            "customer_id",
            "order_id",
            "timestamp",
            "amount",
        ]
    )

    transactions = transactions[
        transactions["amount"] > 0
    ].copy()

    logger.info(
        f"Loaded {len(transactions)} valid transaction line-items"
    )

    # ---------------------------------------------------------
    # Convert line-items into actual invoice/order events
    # ---------------------------------------------------------

    orders = (
        transactions
        .groupby(
            ["customer_id", "order_id"],
            as_index=False,
        )
        .agg(
            timestamp=("timestamp", "min"),
            order_amount=("amount", "sum"),
        )
    )

    logger.info(
        f"Built {len(orders)} unique purchase orders"
    )

    # Dataset observation cutoff
    observation_end = (
        orders["timestamp"].max()
        + pd.Timedelta(days=1)
    )

    # ---------------------------------------------------------
    # Build customer-level BG/NBD features
    # ---------------------------------------------------------

    df = (
        orders
        .groupby("customer_id")
        .agg(
            first_purchase=("timestamp", "min"),
            last_purchase=("timestamp", "max"),
            order_count=("order_id", "nunique"),
            monetary_value=("order_amount", "mean"),
        )
        .reset_index()
    )

    # Number of repeat purchases after first order
    df["frequency"] = (
        df["order_count"] - 1
    ).clip(lower=0)

    # BG/NBD recency:
    # time between first and most recent purchase
    df["recency"] = (
        df["last_purchase"]
        - df["first_purchase"]
    ).dt.days

    # BG/NBD customer age:
    # time between first purchase and observation cutoff
    df["T"] = (
        observation_end
        - df["first_purchase"]
    ).dt.days

    # ---------------------------------------------------------
    # Keep valid returning customers
    # ---------------------------------------------------------

    df = df[
        (df["frequency"] > 0)
        & (df["monetary_value"] > 0)
        & (df["T"] > 0)
        & (df["recency"] >= 0)
        & (df["recency"] <= df["T"])
    ].copy()

    # ---------------------------------------------------------
    # XGBoost engineered features
    # ---------------------------------------------------------

    df["log_monetary"] = np.log1p(
        df["monetary_value"]
    )

    df["log_frequency"] = np.log1p(
        df["frequency"]
    )

    # Purchase rate over observed customer lifetime
    df["purchase_velocity"] = (
        df["frequency"]
        / (df["T"] + 1)
    )

    # Fraction of observed customer lifetime containing
    # repeat purchasing activity
    df["tenure_ratio"] = (
        df["recency"]
        / (df["T"] + 1)
    )

    # monetary_value is already average invoice/order value
    df["avg_order_value"] = df["monetary_value"]

    # ---------------------------------------------------------
    # Temporary XGBoost target
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    # This is retained only to preserve the existing XGBoost
    # pipeline while we repair the probabilistic model.
    #
    # It is NOT yet a genuine future 90-day CLV target.
    # We will replace this with temporal holdout revenue later.
    # ---------------------------------------------------------

    df["target"] = (
        df["monetary_value"]
        * (df["frequency"] + 1)
    )

    # ---------------------------------------------------------
    # Diagnostics
    # ---------------------------------------------------------

    logger.info(
        f"Loaded {len(df)} returning customers"
    )

    logger.info(
        f"Observation end: {observation_end.date()}"
    )

    logger.info(
        f"Frequency — mean: {df['frequency'].mean():.2f}, "
        f"median: {df['frequency'].median():.2f}, "
        f"max: {df['frequency'].max()}"
    )

    logger.info(
        f"Recency — mean: {df['recency'].mean():.2f}, "
        f"median: {df['recency'].median():.2f}"
    )

    logger.info(
        f"T — mean: {df['T'].mean():.2f}, "
        f"median: {df['T'].median():.2f}"
    )

    return df


def train_and_score(db) -> dict:
    """
    Full model training pipeline.

    Steps:
    1. Build invoice-level customer features
    2. Train BG/NBD + Gamma-Gamma
    3. Train XGBoost
    4. Generate ensemble CLV predictions
    5. Store CLV and churn predictions in database
    """

    # ---------------------------------------------------------
    # MLflow setup
    # ---------------------------------------------------------

    mlflow.set_tracking_uri(
        settings.mlflow_tracking_uri
    )

    mlflow.set_experiment(
        "CLV_Prediction"
    )

    # ---------------------------------------------------------
    # Load training data
    # ---------------------------------------------------------

    df = load_training_data(db)

    if len(df) < 10:

        logger.error(
            "Not enough returning customers to train models."
        )

        return {
            "error": "Insufficient data"
        }

    # ---------------------------------------------------------
    # Remove extreme target outliers for model fitting
    # ---------------------------------------------------------

    q98 = df["target"].quantile(0.98)

    clean_df = df[
        df["target"] <= q98
    ].copy()

    logger.info(
        f"Training on {len(clean_df)} customers "
        f"after target outlier filtering"
    )

    # ---------------------------------------------------------
    # Start MLflow run
    # ---------------------------------------------------------

    with mlflow.start_run(
        run_name="clv_training"
    ):

        # =====================================================
        # 1. Probabilistic Model
        # =====================================================

        logger.info(
            "=== Training Probabilistic Model ==="
        )

        prob_model = ProbabilisticCLVModel(
            prediction_period=90
        )

        prob_metrics = prob_model.fit(
            clean_df
        )

        prob_predictions = prob_model.predict(
            df
        )

        mlflow.log_param(
            "prob_penalizer",
            prob_model.penalizer_coef,
        )

        mlflow.log_metric(
            "prob_training_samples",
            prob_metrics["training_samples"],
        )

        # =====================================================
        # 2. XGBoost Model
        # =====================================================

        logger.info(
            "=== Training XGBoost Model ==="
        )

        feature_cols = [
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

        xgb_model = XGBoostCLVModel()

        xgb_metrics = xgb_model.fit(
            features=clean_df[feature_cols],
            target=clean_df["target"],
            use_log_transform=True,
        )

        mlflow.log_metric(
            "xgb_r2",
            xgb_metrics["r2"],
        )

        mlflow.log_metric(
            "xgb_r2_percentage",
            xgb_metrics["r2_percentage"],
        )

        mlflow.log_metric(
            "xgb_rmse",
            xgb_metrics["rmse"],
        )

        mlflow.log_metric(
            "xgb_mae",
            xgb_metrics["mae"],
        )

        mlflow.log_params(
            {
                f"xgb_{key}": value
                for key, value
                in xgb_model.params.items()
                if isinstance(
                    value,
                    (int, float, str),
                )
            }
        )

        # Save XGBoost model
        model_path = xgb_model.save()

        mlflow.log_artifact(
            str(model_path)
        )

        # =====================================================
        # 3. Ensemble Predictions
        # =====================================================

        logger.info(
            "=== Generating Ensemble Predictions ==="
        )

        xgb_predictions = xgb_model.predict(
            df[feature_cols]
        )

        final_df = prob_predictions.copy()

        final_df["xgb_clv"] = (
            xgb_predictions
        )

        # Existing ensemble weights retained temporarily.
        # Later we will validate/tune these weights.
        final_df["predicted_clv_90d"] = (
            0.60
            * final_df["predicted_clv_90d"]
            + 0.40
            * final_df["xgb_clv"]
        )

        final_df["predicted_clv_90d"] = (
            final_df["predicted_clv_90d"]
            .clip(lower=0)
            .round(2)
        )

        final_df["churn_probability"] = (
            final_df["churn_probability"]
            .clip(0.0, 1.0)
            .round(4)
        )

        # =====================================================
        # 4. Prediction Diagnostics
        # =====================================================

        logger.info(
            "Average churn probability: "
            f"{final_df['churn_probability'].mean() * 100:.2f}%"
        )

        logger.info(
            "Median churn probability: "
            f"{final_df['churn_probability'].median() * 100:.2f}%"
        )

        logger.info(
            "High-risk customers (>70% churn): "
            f"{(final_df['churn_probability'] > 0.70).sum()}"
        )

        # =====================================================
        # 5. Write predictions to database
        # =====================================================

        logger.info(
            "Writing predictions to database..."
        )

        # Remove predictions for customers not present
        # in this training run.
        current_customer_ids = set(
            final_df["customer_id"].astype(str)
        )

        existing_predictions = (
            db.query(Prediction).all()
        )

        for existing_prediction in existing_predictions:

            if (
                str(existing_prediction.customer_id)
                not in current_customer_ids
            ):

                db.delete(
                    existing_prediction
                )

        written = 0

        for _, row in final_df.iterrows():

            customer_id = str(
                row["customer_id"]
            )

            existing = (
                db.query(Prediction)
                .filter_by(
                    customer_id=customer_id
                )
                .first()
            )

            if existing:

                existing.predicted_clv_90d = float(
                    row["predicted_clv_90d"]
                )

                existing.churn_probability = float(
                    row["churn_probability"]
                )

            else:

                db.add(
                    Prediction(
                        customer_id=customer_id,
                        predicted_clv_90d=float(
                            row["predicted_clv_90d"]
                        ),
                        churn_probability=float(
                            row["churn_probability"]
                        ),
                    )
                )

            written += 1

        db.commit()

        logger.info(
            f"[OK] Wrote {written} predictions to database"
        )

        mlflow.log_metric(
            "predictions_written",
            written,
        )

    return {
        "probabilistic": prob_metrics,
        "xgboost": xgb_metrics,
        "predictions_written": written,
        "average_churn_probability": float(
            final_df["churn_probability"].mean()
        ),
    }


if __name__ == "__main__":

    init_db()

    db = SessionLocal()

    try:

        results = train_and_score(db)

        if "error" in results:

            print(
                f"\n[ERROR] Training failed: "
                f"{results['error']}"
            )

            sys.exit(1)

        print("\n[OK] Training complete!")

        print(
            "   XGBoost R2: "
            f"{results['xgboost']['r2_percentage']:.2f}%"
        )

        print(
            "   XGBoost RMSE: "
            f"{results['xgboost']['rmse']:.4f}"
        )

        print(
            "   XGBoost MAE: "
            f"{results['xgboost']['mae']:.4f}"
        )

        print(
            "   Predictions written: "
            f"{results['predictions_written']}"
        )

        print(
            "   Average churn risk: "
            f"{results['average_churn_probability'] * 100:.2f}%"
        )

    finally:

        db.close()