from __future__ import annotations

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """
    App settings (env-driven). Defaults keep everything free/local.
    """

    DATABASE_URL: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./app.db"),
        description="SQLAlchemy DB URL. Compatible with Postgres (e.g., postgresql+psycopg://...)",
    )
    API_BASE_URL: str = Field(
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        description="Used by simulate.py for API calls",
    )
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    OPTUNA_TPE_STARTUP_TRIALS: int = Field(default=int(os.getenv("OPTUNA_TPE_STARTUP_TRIALS", "10")))


settings = Settings()