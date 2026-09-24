"""One-time production database bootstrap."""

import logging
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import Customer, Transaction, RFMFeature, Prediction

from scripts.ingest_data import ingest_csv
from scripts.feature_engineering import compute_rfm_features
from scripts.train_model import train_and_score


logger = logging.getLogger(__name__)


def database_is_populated(db) -> bool:
    """Return True when the production database already contains data."""

    customers = db.query(Customer).count()
    transactions = db.query(Transaction).count()
    predictions = db.query(Prediction).count()

    return (
        customers > 0
        and transactions > 0
        and predictions > 0
    )


def bootstrap_database() -> None:
    """
    Populate the production database once.

    Pipeline:
    CSV → Customers/Transactions → RFM → ML predictions
    """

    init_db()

    db = SessionLocal()

    try:
        # -----------------------------------------------------
        # Skip if database is already populated
        # -----------------------------------------------------

        if database_is_populated(db):
            logger.info(
                "Production database already populated. "
                "Skipping bootstrap."
            )
            return

        logger.info(
            "Production database is empty. "
            "Starting initial data bootstrap..."
        )

        # -----------------------------------------------------
        # Locate original dataset
        # -----------------------------------------------------

        csv_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "Online_Retail.csv"
        )

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {csv_path}"
            )

        logger.info(
            f"Using dataset: {csv_path}"
        )

        # -----------------------------------------------------
        # 1. Ingest CSV
        # -----------------------------------------------------

        logger.info(
            "=== STEP 1: Data ingestion ==="
        )

        ingestion_stats = ingest_csv(
            str(csv_path),
            db,
        )

        logger.info(
            f"Ingestion complete: {ingestion_stats}"
        )

        # -----------------------------------------------------
        # 2. Feature engineering
        # -----------------------------------------------------

        logger.info(
            "=== STEP 2: Feature engineering ==="
        )

        rfm_stats = compute_rfm_features(db)

        logger.info(
            f"RFM computation complete: {rfm_stats}"
        )

        # -----------------------------------------------------
        # 3. Model training + predictions
        # -----------------------------------------------------

        logger.info(
            "=== STEP 3: Model training ==="
        )

        training_stats = train_and_score(db)

        if "error" in training_stats:
            raise RuntimeError(
                f"Model training failed: "
                f"{training_stats['error']}"
            )

        logger.info(
            f"Training complete: {training_stats}"
        )

        logger.info(
            "=========================================="
        )
        logger.info(
            "Production database bootstrap COMPLETE"
        )
        logger.info(
            "Dashboard data is now available."
        )
        logger.info(
            "=========================================="
        )

    except Exception:
        db.rollback()
        logger.exception(
            "Production database bootstrap FAILED."
        )
        raise

    finally:
        db.close()