from __future__ import annotations
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: C:\Users\abish\.gemini\antigravity\scratch\personalized-learning-dashboard
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
BACKEND_ENV_FILE = PROJECT_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "postgresql+psycopg://palp:palp_secret_password@localhost:5432/palp"
    REDIS_URL: str = "redis://localhost:6379/0"
    ML_SERVICE_URL: str = "http://localhost:8100"
    MODEL_VERSION: str = "rct-gat-1.0.0-baseline"

    # JWT Authentication
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google Sign-In OAuth
    GOOGLE_CLIENT_ID: str = "733371913106-aipdp3csna740cm0j2qcp2o9lv23d8r8.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "REPLACE_WITH_ROTATED_SECRET_IF_REQUIRED"
    MOCK_GOOGLE_AUTH: bool = False
    ALLOWED_EMAILS: str = ""  # Comma-separated list of allowed Google emails, empty = all

    # Google Gemini Chatbot
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-flash-latest"
    GEMINI_CHATBOT_ENABLED: bool = True
    GEMINI_TIMEOUT_SEC: float = 30.0
    ALLOW_BANK_FALLBACK: bool = False

    # External APIs
    YOUTUBE_API_KEY: str = ""

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
        env_file=(str(BACKEND_ENV_FILE), str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_guards(self) -> Settings:
        secret = (self.SECRET_KEY or self.JWT_SECRET or "").strip()
        if not secret:
            raise ValueError("SECRET_KEY (or JWT_SECRET) must be configured in .env and cannot be empty")
        if not self.SECRET_KEY:
            self.SECRET_KEY = secret
        if not self.JWT_SECRET:
            self.JWT_SECRET = secret
        if self.ENV.lower() == "production" and self.MOCK_GOOGLE_AUTH:
            raise ValueError("MOCK_GOOGLE_AUTH is strictly forbidden when ENV=production")
        return self


settings = Settings()
