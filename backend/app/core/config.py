from __future__ import annotations
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "postgresql+psycopg://palp:palp_secret_password@localhost:5432/palp"
    REDIS_URL: str = "redis://localhost:6379/0"
    ML_SERVICE_URL: str = "http://localhost:8100"
    MODEL_VERSION: str = "rct-gat-1.0.0-baseline"

    # JWT Authentication
    JWT_SECRET: str = "super-secret-jwt-key-for-palp-dashboard-development-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google Sign-In OAuth
    GOOGLE_CLIENT_ID: str = "mock-client-id-for-development.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "mock-client-secret-for-development"
    MOCK_GOOGLE_AUTH: bool = True

    # Google Gemini
    GEMINI_API_KEY: str = ""

    # Thresholds and System Constants (spec §8, §23)
    THETA_SUSPECT: float = 0.45
    EPSILON_PROBE: float = 0.10
    ENTROPY_GUARD: float = 0.70
    MASTERY_TARGET: float = 0.60
    TAU_DAYS: float = 60.0
    COLD_START_MIN_INTERACTIONS: int = 20

    # Special Test Mode Settings (change 4)
    SPECIAL_MAIN_Q_TIME_SEC: int = 30
    SPECIAL_SUB_Q_COUNT: int = 3
    SPECIAL_SUB_Q_TIME_SEC: int = 20
    SPECIAL_DEFAULT_MAIN_COUNT: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_guards(self) -> Settings:
        if self.ENV.lower() == "production" and self.MOCK_GOOGLE_AUTH:
            raise ValueError("MOCK_GOOGLE_AUTH is strictly forbidden when ENV=production")
        return self


settings = Settings()
