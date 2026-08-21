"""SQLAlchemy ORM models matching schema.md definitions."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    DateTime,
)

from app.database import Base


class Customer(Base):
    """Customer profile."""

    __tablename__ = "customers"

    customer_id = Column(String(255), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    signup_date = Column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<Customer(customer_id='{self.customer_id}')>"


class Transaction(Base):
    """Individual purchase transaction."""

    __tablename__ = "transactions"

    transaction_id = Column(String(36), primary_key=True)
    order_id = Column(String(255), nullable=True, index=True)
    customer_id = Column(
        String(255),
        ForeignKey("customers.customer_id"),
        nullable=False,
        index=True,
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)

    def __repr__(self) -> str:
        return f"<Transaction(id='{self.transaction_id}', amount={self.amount})>"


class RFMFeature(Base):
    """Computed RFM (Recency, Frequency, Monetary) features per customer."""

    __tablename__ = "rfm_features"

    customer_id = Column(
        String(255),
        ForeignKey("customers.customer_id"),
        primary_key=True,
    )
    recency = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False)
    monetary_value = Column(Numeric(10, 2), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<RFMFeature(customer='{self.customer_id}', "
            f"R={self.recency}, F={self.frequency}, M={self.monetary_value})>"
        )


class Prediction(Base):
    """Model output — CLV prediction and churn probability."""

    __tablename__ = "predictions"

    customer_id = Column(
        String(255),
        ForeignKey("customers.customer_id"),
        primary_key=True,
    )
    predicted_clv_90d = Column(Numeric(10, 2))
    churn_probability = Column(
        Float,
        CheckConstraint(
            "churn_probability >= 0.0 AND churn_probability <= 1.0",
            name="chk_churn_probability_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(customer='{self.customer_id}', "
            f"clv_90d={self.predicted_clv_90d}, churn={self.churn_probability})>"
        )
