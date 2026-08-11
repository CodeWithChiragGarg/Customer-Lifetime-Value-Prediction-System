"""Probabilistic CLV models using the lifetimes library (BG/NBD + Gamma-Gamma)."""

import logging
from typing import Optional

import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter

logger = logging.getLogger(__name__)


class ProbabilisticCLVModel:
    """BG/NBD model for purchase frequency + Gamma-Gamma for monetary value."""

    def __init__(
        self,
        penalizer_coef: float = 0.01,
        prediction_period: int = 90,
    ) -> None:
        self.penalizer_coef = penalizer_coef
        self.prediction_period = prediction_period
        self.bgf: Optional[BetaGeoFitter] = None
        self.ggf: Optional[GammaGammaFitter] = None

    def fit(self, rfm_data: pd.DataFrame) -> dict:
        """
        Train BG/NBD and Gamma-Gamma models on RFM data.

        Args:
            rfm_data: DataFrame with columns:
                - frequency (int): number of repeat purchases
                - recency (int): days since last purchase
                - T (int): customer tenure in days
                - monetary_value (float): average transaction value

        Returns:
            Dictionary with model fit summary metrics.
        """
        # BG/NBD model for purchase frequency
        logger.info("Fitting BG/NBD model...")
        self.bgf = BetaGeoFitter(penalizer_coef=self.penalizer_coef)
        self.bgf.fit(
            rfm_data["frequency"],
            rfm_data["recency"],
            rfm_data["T"],
        )

        # Gamma-Gamma model for monetary value
        # Only fit on customers with at least 1 repeat purchase
        returning = rfm_data[rfm_data["frequency"] > 0]

        logger.info("Fitting Gamma-Gamma model...")
        self.ggf = GammaGammaFitter(penalizer_coef=self.penalizer_coef)
        self.ggf.fit(
            returning["frequency"],
            returning["monetary_value"],
        )

        return {
            "bgf_params": dict(self.bgf.summary),
            "ggf_params": dict(self.ggf.summary),
            "training_samples": len(rfm_data),
            "returning_customers": len(returning),
        }

    def predict(self, rfm_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate CLV predictions for each customer.

        Args:
            rfm_data: Same format as fit() input.

        Returns:
            DataFrame with customer_id, predicted_clv_90d, churn_probability.
        """
        if self.bgf is None or self.ggf is None:
            raise ValueError("Models must be fitted before prediction.")

        result = rfm_data.copy()

        # Predict number of purchases in next N days
        result["predicted_purchases"] = self.bgf.conditional_expected_number_of_purchases_up_to_time(
            self.prediction_period,
            rfm_data["frequency"],
            rfm_data["recency"],
            rfm_data["T"],
        )

        # Predict CLV using Gamma-Gamma
        result["predicted_clv_90d"] = self.ggf.customer_lifetime_value(
            self.bgf,
            rfm_data["frequency"],
            rfm_data["recency"],
            rfm_data["T"],
            rfm_data["monetary_value"],
            time=self.prediction_period / 30,  # convert days to months
            discount_rate=0.01,
        )

        # Churn probability (1 - probability of being alive)
        result["churn_probability"] = 1 - self.bgf.conditional_probability_alive(
            rfm_data["frequency"],
            rfm_data["recency"],
            rfm_data["T"],
        )

        # Clamp churn probability to [0, 1]
        result["churn_probability"] = result["churn_probability"].clip(0.0, 1.0)

        return result[["customer_id", "predicted_clv_90d", "churn_probability"]]
