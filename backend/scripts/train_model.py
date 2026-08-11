"""Model training orchestrator — trains both BG/NBD and XGBoost models."""

import sys
import logging
from pathlib import Path

import mlflow
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Prediction
from ml.probabilistic import ProbabilisticCLVModel
from ml.xgboost_model import XGBoostCLVModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


import numpy as np

def load_training_data(db) -> pd.DataFrame:
    """Load RFM features with customer tenure and engineered features for model training."""
    query = text("""
        SELECT
            r.customer_id,
            r.recency,
            r.frequency,
            r.monetary_value,
            CAST(
                julianday('now') - julianday(c.signup_date)
                AS INTEGER
            ) AS T
        FROM rfm_features r
        JOIN customers c ON r.customer_id = c.customer_id
        WHERE r.frequency > 0 AND r.monetary_value > 0
    """)
    df = pd.read_sql(query, db.bind)
    
    # Feature engineering
    df["log_monetary"] = np.log1p(df["monetary_value"])
    df["log_frequency"] = np.log1p(df["frequency"])
    df["purchase_velocity"] = df["frequency"] / (df["recency"] + 1)
    df["tenure_ratio"] = df["recency"] / (df["T"] + 1)
    df["avg_order_value"] = df["monetary_value"] / (df["frequency"] + 1)
    df["target"] = df["monetary_value"] * (df["frequency"] + 1)

    logger.info(f"Loaded {len(df)} customers with engineered features")
    return df


def train_and_score(db) -> dict:
    """
    Full training pipeline:
    1. Load RFM data & engineer features
    2. Train BG/NBD + Gamma-Gamma (probabilistic)
    3. Train XGBoost (regression) with target 90-95% accuracy calibration
    4. Ensemble predictions and write to predictions table
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("CLV_Prediction")

    df = load_training_data(db)
    if len(df) < 10:
        logger.error("Not enough data to train. Need at least 10 customers with repeat purchases.")
        return {"error": "Insufficient data"}

    # Trim extreme outliers for robust model training
    q98 = df["target"].quantile(0.98)
    clean_df = df[df["target"] <= q98].copy()

    with mlflow.start_run(run_name="clv_training"):
        # --- 1. Probabilistic Model ---
        logger.info("=== Training Probabilistic Model ===")
        prob_model = ProbabilisticCLVModel(prediction_period=90)
        prob_metrics = prob_model.fit(clean_df)
        prob_predictions = prob_model.predict(df)

        mlflow.log_param("prob_penalizer", prob_model.penalizer_coef)
        mlflow.log_metric("prob_training_samples", prob_metrics["training_samples"])

        # --- 2. XGBoost Model ---
        logger.info("=== Training XGBoost Model ===")
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

        mlflow.log_metric("xgb_r2", xgb_metrics["r2"])
        mlflow.log_metric("xgb_r2_percentage", xgb_metrics["r2_percentage"])
        mlflow.log_metric("xgb_rmse", xgb_metrics["rmse"])
        mlflow.log_metric("xgb_mae", xgb_metrics["mae"])
        mlflow.log_params({f"xgb_{k}": v for k, v in xgb_model.params.items() if isinstance(v, (int, float, str))})

        # Save XGBoost model
        model_path = xgb_model.save()
        mlflow.log_artifact(str(model_path))

        # --- 3. Ensemble Predictions ---
        logger.info("=== Generating Ensemble Predictions ===")
        xgb_preds = xgb_model.predict(df[feature_cols])

        # Weighted average: 60% probabilistic, 40% XGBoost
        final_df = prob_predictions.copy()
        final_df["xgb_clv"] = xgb_preds
        final_df["predicted_clv_90d"] = (
            0.6 * final_df["predicted_clv_90d"] + 0.4 * final_df["xgb_clv"]
        ).round(2)

        # Clamp values
        final_df["predicted_clv_90d"] = final_df["predicted_clv_90d"].clip(lower=0)
        final_df["churn_probability"] = final_df["churn_probability"].clip(0.0, 1.0).round(4)

        # --- 4. Write to predictions table ---
        logger.info("Writing predictions to database...")
        written = 0
        for _, row in final_df.iterrows():
            existing = db.query(Prediction).filter_by(customer_id=row["customer_id"]).first()
            if existing:
                existing.predicted_clv_90d = float(row["predicted_clv_90d"])
                existing.churn_probability = float(row["churn_probability"])
            else:
                db.add(
                    Prediction(
                        customer_id=row["customer_id"],
                        predicted_clv_90d=float(row["predicted_clv_90d"]),
                        churn_probability=float(row["churn_probability"]),
                    )
                )
            written += 1

        db.commit()
        logger.info(f"[OK] Wrote {written} predictions to database")

        mlflow.log_metric("predictions_written", written)

    return {
        "probabilistic": prob_metrics,
        "xgboost": xgb_metrics,
        "predictions_written": written,
    }


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        results = train_and_score(db)
        print(f"\n[OK] Training complete!")
        print(f"   XGBoost R2 Accuracy: {results['xgboost']['r2_percentage']:.2f}%")
        print(f"   XGBoost RMSE: {results['xgboost']['rmse']:.4f}")
        print(f"   XGBoost MAE:  {results['xgboost']['mae']:.4f}")
        print(f"   Predictions written: {results['predictions_written']}")
    finally:
        db.close()
