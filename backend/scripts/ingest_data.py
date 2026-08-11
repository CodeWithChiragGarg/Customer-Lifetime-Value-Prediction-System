"""Data ingestion script — loads CSV transaction data into the database."""

import sys
import uuid
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Customer, Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def ingest_csv(csv_path: str, db: Session) -> dict:
    """
    Ingest a CSV file into the customers and transactions tables.

    Expected CSV columns (flexible — will attempt to map):
        - customer_id (or CustomerID, Customer ID)
        - email (optional — will generate if missing)
        - signup_date (or first transaction date as fallback)
        - transaction_id (optional — will generate UUID if missing)
        - timestamp (or InvoiceDate, date, transaction_date)
        - amount (or TotalAmount, Revenue, UnitPrice * Quantity)

    Args:
        csv_path: Path to the CSV file.
        db: SQLAlchemy database session.

    Returns:
        Dictionary with ingestion statistics.
    """
    logger.info(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8", encoding_errors="replace")
    logger.info(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

    # Normalize column names (lowercase, strip whitespace)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # --- Map customer_id ---
    cid_candidates = ["customer_id", "customerid", "customer", "cust_id"]
    cid_col = _find_column(df, cid_candidates)
    if cid_col is None:
        raise ValueError(f"Cannot find customer ID column. Available: {list(df.columns)}")
    df["customer_id"] = df[cid_col].astype(str).str.strip()

    # Drop rows with missing customer_id
    df = df.dropna(subset=["customer_id"])
    df = df[df["customer_id"] != "nan"]

    # --- Map timestamp ---
    ts_candidates = ["timestamp", "invoicedate", "invoice_date", "date", "transaction_date", "order_date"]
    ts_col = _find_column(df, ts_candidates)
    if ts_col is None:
        raise ValueError(f"Cannot find timestamp column. Available: {list(df.columns)}")
    df["timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # --- Map amount ---
    amt_candidates = ["amount", "totalamount", "total_amount", "revenue", "total", "price"]
    amt_col = _find_column(df, amt_candidates)
    if amt_col is None:
        # Try computing from UnitPrice * Quantity
        if "unitprice" in df.columns and "quantity" in df.columns:
            df["amount"] = df["unitprice"] * df["quantity"]
            logger.info("Computed amount from unitprice * quantity")
        else:
            raise ValueError(f"Cannot find amount column. Available: {list(df.columns)}")
    else:
        df["amount"] = pd.to_numeric(df[amt_col], errors="coerce")

    # Remove negative/zero amounts
    df = df[df["amount"] > 0]

    # --- Generate unique transaction_id per row ---
    # InvoiceNo is per-invoice (not per line item), so always generate UUIDs
    df["transaction_id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    logger.info("Generated UUIDs for transaction_id")

    # --- Map email ---
    email_candidates = ["email", "customer_email", "e-mail"]
    email_col = _find_column(df, email_candidates)
    if email_col is not None:
        df["email"] = df[email_col].astype(str).str.strip()
    else:
        df["email"] = df["customer_id"].apply(lambda x: f"{x}@placeholder.com")
        logger.info("Generated placeholder emails")

    # --- Upsert customers ---
    customer_df = (
        df.groupby("customer_id")
        .agg(
            email=("email", "first"),
            signup_date=("timestamp", "min"),
        )
        .reset_index()
    )

    customers_added = 0
    for _, row in customer_df.iterrows():
        existing = db.query(Customer).filter_by(customer_id=row["customer_id"]).first()
        if not existing:
            db.add(
                Customer(
                    customer_id=row["customer_id"],
                    email=row["email"],
                    signup_date=row["signup_date"],
                )
            )
            customers_added += 1

    db.commit()
    logger.info(f"Upserted {customers_added} new customers (total: {len(customer_df)})")

    # --- Bulk insert transactions ---
    logger.info("Bulk inserting transactions...")
    tx_df = df[["transaction_id", "customer_id", "timestamp", "amount"]].copy()
    tx_df["amount"] = tx_df["amount"].round(2)
    tx_df.to_sql("transactions", db.bind, if_exists="append", index=False)
    transactions_added = len(tx_df)
    logger.info(f"Inserted {transactions_added} transactions")

    return {
        "total_rows_in_csv": len(df),
        "customers_added": customers_added,
        "transactions_added": transactions_added,
    }


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column name from a list of candidates."""
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_data.py <path_to_csv>")
        print("Example: python ingest_data.py data/transactions.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File not found — {csv_file}")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        stats = ingest_csv(csv_file, db)
        print(f"\n[OK] Ingestion complete: {stats}")
    finally:
        db.close()
