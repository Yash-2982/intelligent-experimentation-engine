from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.experiments import router as experiments_router
from app.api.routes.health import router as health_router
from app.core.logging import configure_logging
from app.db.session import init_db


def create_app() -> FastAPI:
    configure_logging()
    init_db()

    app = FastAPI(
        title="Intelligent Experimentation Engine",
        version="1.0.0",
        description="Suggests next best experiment configs using random exploration + Optuna TPE, with audit trail.",
    )

    app.include_router(health_router)
    app.include_router(experiments_router)

    return app


app = create_app()