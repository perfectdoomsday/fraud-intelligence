from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Fraud Intelligence API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./fraud_intelligence.db"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw: str = "raw-transactions"
    kafka_topic_predictions: str = "fraud-predictions"
    kafka_topic_alerts: str = "fraud-alerts"
    kafka_consumer_group: str = "fraud-detection-v1"
    kafka_enabled: bool = True
    model_artifact_path: str = "artifacts/demo_fraud_model.joblib"
    jwt_secret_key: str = "CHANGE_THIS_DEVELOPMENT_SECRET_BEFORE_DEPLOYMENT"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    admin_email: str = "admin@local.test"
    admin_password: str = "ChangeMe-Local-Only-123!"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    risk_medium_threshold: int = 30
    risk_high_threshold: int = 60
    risk_critical_threshold: int = 80
    supervised_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    anomaly_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    max_bulk_transactions: int = 5000
    rate_limit_per_minute: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
