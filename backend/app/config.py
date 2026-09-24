"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite:///./clv_prediction.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"

    cors_origins: str = (
        "http://localhost:3000,"
        "https://customer-lifetime-value-prediction-liart.vercel.app"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
        ]


settings = Settings()
