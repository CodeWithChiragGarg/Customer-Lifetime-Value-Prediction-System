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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)


def ingest_csv(csv_path: str, db: Session) -> dict:
    """
    Ingest CSV transaction data into the database.

    Supported fields:
    - customer_id / CustomerID
    - InvoiceNo / order_id
    - timestamp / InvoiceDate
    - amount OR UnitPrice * Quantity
    - email (optional)

    InvoiceNo is preserved as order_id so that multiple product
    line-items belonging to the same purchase can later be treated
    as one purchase event by the CLV models.
    """

    logger.info(f"Reading CSV: {csv_path}")

    df = pd.read_csv(
        csv_path,
        encoding="utf-8",
        encoding_errors="replace",
    )

    logger.info(
        f"Loaded {len(df)} rows, columns: {list(df.columns)}"
    )

    # ---------------------------------------------------------
    # Normalize column names
    # ---------------------------------------------------------

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # ---------------------------------------------------------
    # Customer ID
    # ---------------------------------------------------------

    cid_candidates = [
        "customer_id",
        "customerid",
        "customer",
        "cust_id",
    ]

    cid_col = _find_column(df, cid_candidates)

    if cid_col is None:
        raise ValueError(
            f"Cannot find customer ID column. "
            f"Available columns: {list(df.columns)}"
        )

    # Remove missing customer IDs
    df = df.dropna(subset=[cid_col])

    df["customer_id"] = (
        df[cid_col]
        .astype(str)
        .str.strip()
    )

    df = df[
        (df["customer_id"] != "")
        & (df["customer_id"].str.lower() != "nan")
    ]

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------

    ts_candidates = [
        "timestamp",
        "invoicedate",
        "invoice_date",
        "date",
        "transaction_date",
        "order_date",
    ]

    ts_col = _find_column(df, ts_candidates)

    if ts_col is None:
        raise ValueError(
            f"Cannot find timestamp column. "
            f"Available columns: {list(df.columns)}"
        )

    df["timestamp"] = pd.to_datetime(
        df[ts_col],
        errors="coerce",
    )

    df = df.dropna(subset=["timestamp"])

    # ---------------------------------------------------------
    # Transaction Amount
    # ---------------------------------------------------------

    amt_candidates = [
        "amount",
        "totalamount",
        "total_amount",
        "revenue",
        "total",
        "price",
    ]

    amt_col = _find_column(df, amt_candidates)

    if amt_col is not None:

        df["amount"] = pd.to_numeric(
            df[amt_col],
            errors="coerce",
        )

    elif "unitprice" in df.columns and "quantity" in df.columns:

        df["unitprice"] = pd.to_numeric(
            df["unitprice"],
            errors="coerce",
        )

        df["quantity"] = pd.to_numeric(
            df["quantity"],
            errors="coerce",
        )

        df["amount"] = (
            df["unitprice"] * df["quantity"]
        )

        logger.info(
            "Computed amount from unitprice * quantity"
        )

    else:

        raise ValueError(
            f"Cannot determine transaction amount. "
            f"Available columns: {list(df.columns)}"
        )

    # Remove invalid, zero and negative purchases
    df = df.dropna(subset=["amount"])
    df = df[df["amount"] > 0]

    # ---------------------------------------------------------
    # Order / Invoice ID
    # ---------------------------------------------------------

    order_candidates = [
        "invoiceno",
        "invoice_no",
        "order_id",
        "orderid",
    ]

    order_col = _find_column(
        df,
        order_candidates,
    )

    if order_col is not None:

        df["order_id"] = (
            df[order_col]
            .astype(str)
            .str.strip()
        )

        logger.info(
            f"Mapped {order_col} to order_id"
        )

    else:

        # Generic fallback for datasets that don't contain
        # invoice/order identifiers.
        df["order_id"] = [
            str(uuid.uuid4())
            for _ in range(len(df))
        ]

        logger.warning(
            "No invoice/order ID found; "
            "generated fallback order IDs"
        )

    # ---------------------------------------------------------
    # Unique row-level transaction ID
    # ---------------------------------------------------------

    # transaction_id identifies each database row.
    # order_id identifies the actual purchase/order.

    df["transaction_id"] = [
        str(uuid.uuid4())
        for _ in range(len(df))
    ]

    logger.info(
        "Generated UUIDs for transaction_id"
    )

    # ---------------------------------------------------------
    # Email
    # ---------------------------------------------------------

    email_candidates = [
        "email",
        "customer_email",
        "e-mail",
    ]

    email_col = _find_column(
        df,
        email_candidates,
    )

    if email_col is not None:

        df["email"] = (
            df[email_col]
            .astype(str)
            .str.strip()
        )

    else:

        df["email"] = (
            df["customer_id"]
            + "@placeholder.com"
        )

        logger.info(
            "Generated placeholder emails"
        )

    # ---------------------------------------------------------
    # Customer table
    # ---------------------------------------------------------

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

        existing = (
            db.query(Customer)
            .filter_by(
                customer_id=row["customer_id"]
            )
            .first()
        )

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

    logger.info(
        f"Upserted {customers_added} new customers "
        f"(total: {len(customer_df)})"
    )

    # ---------------------------------------------------------
    # Transaction table
    # ---------------------------------------------------------

    logger.info(
        "Inserting transactions in batches..."
    )

    transaction_columns = [
        "transaction_id",
        "order_id",
        "customer_id",
        "timestamp",
        "amount",
    ]

    batch_size = 5000
    transactions_added = len(df)

    for start in range(
        0,
        len(df),
        batch_size,
    ):

        batch = df.iloc[
            start:start + batch_size
        ][transaction_columns].copy()

        batch["amount"] = (
            batch["amount"].round(2)
        )

        batch.to_sql(
            "transactions",
            db.bind,
            if_exists="append",
            index=False,
        )

        inserted_until = min(
            start + batch_size,
            len(df),
        )

        logger.info(
            f"Inserted {inserted_until}/"
            f"{len(df)} transactions"
        )

        # Release the batch from memory
        del batch

    logger.info(
        f"Inserted {transactions_added} transactions"
    )

    return {
        "total_rows_in_csv": len(df),
        "customers_added": customers_added,
        "transactions_added": transactions_added,
    }


def _find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """Find the first matching column from a list of candidates."""

    for candidate in candidates:

        if candidate in df.columns:
            return candidate

    return None


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage: python ingest_data.py <path_to_csv>"
        )

        print(
            "Example: python ingest_data.py "
            "data/Online_Retail.csv"
        )

        sys.exit(1)

    csv_file = sys.argv[1]

    if not Path(csv_file).exists():

        print(
            f"Error: File not found — {csv_file}"
        )

        sys.exit(1)

    init_db()

    db = SessionLocal()

    try:

        stats = ingest_csv(
            csv_file,
            db,
        )

        print(
            f"\n[OK] Ingestion complete: {stats}"
        )

    except Exception:

        db.rollback()
        logger.exception(
            "Data ingestion failed."
        )
        raise

    finally:

        db.close()