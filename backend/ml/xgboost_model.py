"""XGBoost-based CLV regression model."""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Default path for saving model artifacts
MODEL_DIR = Path(__file__).parent / "models"


class XGBoostCLVModel:
    """XGBoost regression model for multi-feature CLV prediction."""

    def __init__(self, params: Optional[dict] = None) -> None:
        self.params = params or {
            "objective": "reg:squarederror",
            "max_depth": 5,
            "learning_rate": 0.06,
            "n_estimators": 180,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "reg_alpha": 5.5,
            "reg_lambda": 4.5,
            "random_state": 42,
        }
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_columns: list[str] = []
        self.log_transform_target: bool = True

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        test_size: float = 0.2,
        use_log_transform: bool = True,
    ) -> dict:
        """
        Train the XGBoost CLV model.

        Args:
            features: DataFrame with RFM + engineered features.
            target: Series with actual CLV values.
            test_size: Fraction of data to hold out for validation.
            use_log_transform: Whether to log1p transform target for training.

        Returns:
            Dictionary with training metrics (R2, RMSE, MAE).
        """
        self.feature_columns = list(features.columns)
        self.log_transform_target = use_log_transform

        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=test_size, random_state=42
        )

        logger.info(
            f"Training XGBoost: {len(X_train)} train, {len(X_test)} test samples"
        )

        y_train_fit = np.log1p(y_train) if self.log_transform_target else y_train
        y_test_eval = np.log1p(y_test) if self.log_transform_target else y_test

        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(
            X_train,
            y_train_fit,
            eval_set=[(X_test, y_test_eval)],
            verbose=False,
        )

        # Evaluate on original scale
        raw_pred = self.model.predict(X_test)
        y_pred = np.expm1(raw_pred) if self.log_transform_target else raw_pred
        y_pred = np.clip(y_pred, a_min=0, a_max=None)

        r2 = float(r2_score(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))

        logger.info(f"XGBoost metrics — R2: {r2*100:.2f}%, RMSE: {rmse:.4f}, MAE: {mae:.4f}")

        return {
            "r2": r2,
            "r2_percentage": r2 * 100,
            "rmse": rmse,
            "mae": mae,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "feature_importance": dict(
                zip(
                    self.feature_columns,
                    self.model.feature_importances_.tolist(),
                )
            ),
        }

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Generate CLV predictions.

        Args:
            features: DataFrame with same columns as training data.

        Returns:
            Array of predicted CLV values.
        """
        if self.model is None:
            raise ValueError("Model must be fitted before prediction.")
        cols = self.feature_columns if self.feature_columns else list(features.columns)
        raw_pred = self.model.predict(features[cols])
        preds = np.expm1(raw_pred) if self.log_transform_target else raw_pred
        return np.clip(preds, a_min=0, a_max=None)

    def save(self, path: Optional[Path] = None) -> Path:
        """Save model to disk."""
        if self.model is None:
            raise ValueError("No model to save.")
        save_path = path or MODEL_DIR / "xgboost_clv.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(save_path))
        logger.info(f"Model saved to {save_path}")
        return save_path

    def load(self, path: Optional[Path] = None) -> None:
        """Load model from disk."""
        load_path = path or MODEL_DIR / "xgboost_clv.json"
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(load_path))
        if hasattr(self.model, "feature_names_in_") and self.model.feature_names_in_ is not None:
            self.feature_columns = list(self.model.feature_names_in_)
        elif self.model.get_booster().feature_names:
            self.feature_columns = list(self.model.get_booster().feature_names)
        else:
            self.feature_columns = [
                "recency", "frequency", "monetary_value", "T",
                "log_monetary", "log_frequency", "purchase_velocity",
                "tenure_ratio", "avg_order_value"
            ]
        logger.info(f"Model loaded from {load_path} with features: {self.feature_columns}")
