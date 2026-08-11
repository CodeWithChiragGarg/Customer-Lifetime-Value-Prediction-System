"""Feature engineering script — computes RFM metrics from transactions."""

import sys
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import RFMFeature

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def compute_rfm_features(db: Session) -> dict:
    """
    Compute Recency, Frequency, and Monetary features from the transactions table.

    - Recency: Days since last purchase
    - Frequency: Total number of repeat purchases (total transactions - 1)
    - Monetary Value: Average transaction amount

    Returns:
        Dictionary with computation statistics.
    """
    logger.info("Querying transactions for RFM computation...")

    # Load transactions via SQL for efficiency
    query = text("""
        SELECT customer_id, timestamp, amount
        FROM transactions
        ORDER BY customer_id, timestamp
    """)
    df = pd.read_sql(query, db.bind)

    if df.empty:
        logger.warning("No transactions found. Run ingest_data.py first.")
        return {"customers_processed": 0}

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Reference date = max date in dataset + 1 day
    reference_date = df["timestamp"].max() + pd.Timedelta(days=1)
    logger.info(f"Reference date: {reference_date.date()}")

    # Compute RFM aggregates per customer
    rfm = (
        df.groupby("customer_id")
        .agg(
            recency=("timestamp", lambda x: (reference_date - x.max()).days),
            frequency=("timestamp", "count"),
            monetary_value=("amount", "mean"),
        )
        .reset_index()
    )

    # Frequency = repeat purchases (total - 1), minimum 0
    rfm["frequency"] = (rfm["frequency"] - 1).clip(lower=0)

    # Round monetary value
    rfm["monetary_value"] = rfm["monetary_value"].round(2)

    logger.info(f"Computed RFM for {len(rfm)} customers")
    logger.info(f"  Recency  — mean: {rfm['recency'].mean():.1f}, median: {rfm['recency'].median():.1f}")
    logger.info(f"  Frequency — mean: {rfm['frequency'].mean():.1f}, median: {rfm['frequency'].median():.1f}")
    logger.info(f"  Monetary  — mean: {rfm['monetary_value'].mean():.2f}, median: {rfm['monetary_value'].median():.2f}")

    # Upsert into rfm_features table
    updated = 0
    inserted = 0
    for _, row in rfm.iterrows():
        existing = db.query(RFMFeature).filter_by(customer_id=row["customer_id"]).first()
        if existing:
            existing.recency = int(row["recency"])
            existing.frequency = int(row["frequency"])
            existing.monetary_value = float(row["monetary_value"])
            updated += 1
        else:
            db.add(
                RFMFeature(
                    customer_id=row["customer_id"],
                    recency=int(row["recency"]),
                    frequency=int(row["frequency"]),
                    monetary_value=float(row["monetary_value"]),
                )
            )
            inserted += 1

    db.commit()
    logger.info(f"RFM features — inserted: {inserted}, updated: {updated}")

    return {
        "customers_processed": len(rfm),
        "inserted": inserted,
        "updated": updated,
    }


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        stats = compute_rfm_features(db)
        print(f"\n[OK] Feature engineering complete: {stats}")
    finally:
        db.close()
