"""Customer segmentation API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Prediction, Transaction


router = APIRouter()


# ---------------------------------------------------------
# Response Models
# ---------------------------------------------------------

class CustomerSegmentRow(BaseModel):
    """Single customer row displayed in the segmentation table."""

    customer_id: str
    email: str
    signup_date: str

    tenure_days: Optional[int] = None
    total_spent: Optional[float] = None
    order_count: Optional[int] = None

    predicted_clv_90d: Optional[float] = None
    churn_probability: Optional[float] = None
    clv_tier: Optional[str] = None

    class Config:
        from_attributes = True


class SegmentsResponse(BaseModel):
    """Paginated customer segmentation response."""

    total: int
    data: list[CustomerSegmentRow]


# ---------------------------------------------------------
# CLV Tier Logic
# ---------------------------------------------------------

def _assign_clv_tier(
    clv: Optional[float],
) -> Optional[str]:
    """
    Assign customer tier using predicted 90-day CLV.

    Current business thresholds:
    High   >= 500
    Medium >= 200
    Low    < 200
    """

    if clv is None:
        return None

    if clv >= 500:
        return "High"

    if clv >= 200:
        return "Medium"

    return "Low"


# ---------------------------------------------------------
# Customer Segments Endpoint
# ---------------------------------------------------------

@router.get(
    "/segments",
    response_model=SegmentsResponse,
)
async def get_customer_segments(
    clv_tier: Optional[str] = Query(
        None,
        description="Filter by CLV tier: High, Medium, Low",
    ),
    min_churn: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum churn probability",
    ),
    max_churn: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Maximum churn probability",
    ),
    min_tenure: Optional[int] = Query(
        None,
        ge=0,
        description="Minimum customer tenure in days",
    ),
    sort_by: str = Query(
        "predicted_clv_90d",
        description="Field used for sorting",
    ),
    sort_order: str = Query(
        "desc",
        description="Sort order: asc or desc",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of results",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset",
    ),
    db: Session = Depends(get_db),
) -> SegmentsResponse:

    """
    Return customer segmentation data with filtering,
    sorting and pagination.

    Purchase counts are based on unique orders/invoices,
    not individual product line-items.
    """

    # ---------------------------------------------------------
    # Determine dataset observation end
    # ---------------------------------------------------------

    dataset_end = (
        db.query(
            func.max(Transaction.timestamp)
        )
        .scalar()
    )

    if dataset_end is None:

        return SegmentsResponse(
            total=0,
            data=[],
        )

    # ---------------------------------------------------------
    # Customer tenure
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    # This is a historical dataset.
    #
    # Therefore tenure must be calculated against the final
    # date in the dataset rather than today's calendar date.
    # ---------------------------------------------------------

    tenure_expr = (
        func.julianday(dataset_end)
        - func.julianday(Customer.signup_date)
    )

    # ---------------------------------------------------------
    # Main customer query
    # ---------------------------------------------------------

    query = (
        db.query(
            Customer.customer_id,
            Customer.email,
            Customer.signup_date,

            tenure_expr.label(
                "tenure_days"
            ),

            func.sum(
                Transaction.amount
            ).label(
                "total_spent"
            ),

            func.count(
                func.distinct(
                    Transaction.order_id
                )
            ).label(
                "order_count"
            ),

            Prediction.predicted_clv_90d,
            Prediction.churn_probability,
        )

        .outerjoin(
            Transaction,
            Customer.customer_id
            == Transaction.customer_id,
        )

        .outerjoin(
            Prediction,
            Customer.customer_id
            == Prediction.customer_id,
        )

        .group_by(
            Customer.customer_id
        )
    )

    # ---------------------------------------------------------
    # Filters
    # ---------------------------------------------------------

    if min_churn is not None:

        query = query.having(
            Prediction.churn_probability
            >= min_churn
        )

    if max_churn is not None:

        query = query.having(
            Prediction.churn_probability
            <= max_churn
        )

    if min_tenure is not None:

        query = query.having(
            tenure_expr >= min_tenure
        )

    # ---------------------------------------------------------
    # Sorting
    # ---------------------------------------------------------

    sort_columns = {
        "predicted_clv_90d":
            Prediction.predicted_clv_90d,

        "churn_probability":
            Prediction.churn_probability,

        "total_spent":
            func.sum(Transaction.amount),

        "order_count":
            func.count(
                func.distinct(
                    Transaction.order_id
                )
            ),

        "tenure_days":
            tenure_expr,
    }

    sort_column = sort_columns.get(
        sort_by,
        Prediction.predicted_clv_90d,
    )

    if sort_order.lower() == "asc":

        query = query.order_by(
            sort_column.asc()
        )

    else:

        query = query.order_by(
            sort_column.desc()
        )

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    results = query.all()

    # ---------------------------------------------------------
    # Build response and apply CLV tier
    # ---------------------------------------------------------

    rows: list[CustomerSegmentRow] = []

    for row in results:

        predicted_clv = (
            float(row.predicted_clv_90d)
            if row.predicted_clv_90d is not None
            else None
        )

        churn_probability = (
            float(row.churn_probability)
            if row.churn_probability is not None
            else None
        )

        tier = _assign_clv_tier(
            predicted_clv
        )

        # Tier is calculated in Python,
        # so apply this filter here.
        if (
            clv_tier is not None
            and tier != clv_tier
        ):
            continue

        rows.append(
            CustomerSegmentRow(
                customer_id=str(
                    row.customer_id
                ),

                email=row.email,

                signup_date=str(
                    row.signup_date
                ),

                tenure_days=(
                    int(row.tenure_days)
                    if row.tenure_days is not None
                    else None
                ),

                total_spent=round(
                    float(row.total_spent or 0),
                    2,
                ),

                order_count=int(
                    row.order_count or 0
                ),

                predicted_clv_90d=predicted_clv,

                churn_probability=churn_probability,

                clv_tier=tier,
            )
        )

    # ---------------------------------------------------------
    # Pagination after tier filtering
    # ---------------------------------------------------------

    total = len(rows)

    paginated_rows = rows[
        offset: offset + limit
    ]

    return SegmentsResponse(
        total=total,
        data=paginated_rows,
    )