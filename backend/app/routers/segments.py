"""Customer segmentation API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Prediction, RFMFeature, Transaction


router = APIRouter()


class CustomerSegmentRow(BaseModel):
    """Response schema for a single customer in the segments view."""

    customer_id: str
    email: str
    signup_date: str
    tenure_days: Optional[int] = None
    total_spent: Optional[float] = None
    transaction_count: Optional[int] = None
    predicted_clv_90d: Optional[float] = None
    churn_probability: Optional[float] = None
    clv_tier: Optional[str] = None

    class Config:
        from_attributes = True


class SegmentsResponse(BaseModel):
    """Paginated segments response."""

    total: int
    data: list[CustomerSegmentRow]


def _assign_clv_tier(clv: Optional[float]) -> Optional[str]:
    """Assign a CLV tier label based on predicted value."""
    if clv is None:
        return None
    if clv >= 500:
        return "High"
    elif clv >= 200:
        return "Medium"
    else:
        return "Low"


@router.get("/segments", response_model=SegmentsResponse)
async def get_customer_segments(
    clv_tier: Optional[str] = Query(None, description="Filter by CLV tier: High, Medium, Low"),
    min_churn: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum churn probability"),
    max_churn: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum churn probability"),
    min_tenure: Optional[int] = Query(None, ge=0, description="Minimum tenure in days"),
    sort_by: str = Query("predicted_clv_90d", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> SegmentsResponse:
    """Get customer segments with filtering, sorting, and pagination."""
    # Build base query with all joined data
    today = func.current_date()
    tenure_expr = func.julianday(today) - func.julianday(Customer.signup_date)

    query = (
        db.query(
            Customer.customer_id,
            Customer.email,
            Customer.signup_date,
            tenure_expr.label("tenure_days"),
            func.sum(Transaction.amount).label("total_spent"),
            func.count(Transaction.transaction_id).label("transaction_count"),
            Prediction.predicted_clv_90d,
            Prediction.churn_probability,
        )
        .outerjoin(Transaction, Customer.customer_id == Transaction.customer_id)
        .outerjoin(Prediction, Customer.customer_id == Prediction.customer_id)
        .group_by(Customer.customer_id)
    )

    # Apply filters
    if min_churn is not None:
        query = query.having(Prediction.churn_probability >= min_churn)
    if max_churn is not None:
        query = query.having(Prediction.churn_probability <= max_churn)
    if min_tenure is not None:
        query = query.having(tenure_expr >= min_tenure)

    # Get total count before pagination
    count_query = query.subquery()
    total = db.query(func.count()).select_from(count_query).scalar() or 0

    # Apply sorting
    sort_column = {
        "predicted_clv_90d": Prediction.predicted_clv_90d,
        "churn_probability": Prediction.churn_probability,
        "total_spent": func.sum(Transaction.amount),
        "tenure_days": tenure_expr,
    }.get(sort_by, Prediction.predicted_clv_90d)

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    results = query.offset(offset).limit(limit).all()

    # Build response with CLV tiers
    rows = []
    for row in results:
        clv_val = float(row.predicted_clv_90d) if row.predicted_clv_90d else None
        tier = _assign_clv_tier(clv_val)

        # Apply CLV tier filter (post-query since it's computed)
        if clv_tier and tier != clv_tier:
            continue

        rows.append(
            CustomerSegmentRow(
                customer_id=row.customer_id,
                email=row.email,
                signup_date=str(row.signup_date),
                tenure_days=int(row.tenure_days) if row.tenure_days else None,
                total_spent=round(float(row.total_spent), 2) if row.total_spent else 0.0,
                transaction_count=row.transaction_count or 0,
                predicted_clv_90d=clv_val,
                churn_probability=float(row.churn_probability) if row.churn_probability else None,
                clv_tier=tier,
            )
        )

    return SegmentsResponse(total=total, data=rows)
