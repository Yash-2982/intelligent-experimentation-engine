from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, confloat, conint
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Experiment, Trial
from app.services.optimizer import OptimizerService
from app.services.simulation import simulate_revenue_per_user

log = logging.getLogger("app")

router = APIRouter(tags=["experiments"])


# -----------------------------
# Pydantic schemas
# -----------------------------
class VariableSpace(BaseModel):
    """
    Decision-variable space for the SaaS pricing optimization use case.
    Compatible with Optuna suggestions (float/int/categorical).
    """

    price_min: confloat(gt=0) = Field(..., description="Minimum price (float)")
    price_max: confloat(gt=0) = Field(..., description="Maximum price (float)")
    discount_pct_min: conint(ge=0, le=50) = Field(..., description="Minimum discount %")
    discount_pct_max: conint(ge=0, le=50) = Field(..., description="Maximum discount %")
    trial_days_min: conint(ge=0, le=30) = Field(..., description="Minimum trial days")
    trial_days_max: conint(ge=0, le=30) = Field(..., description="Maximum trial days")
    onboarding_variants: list[str] = Field(..., min_length=1, description="Allowed variants, e.g. ['A','B','C']")

    def validate_ranges(self) -> None:
        if self.price_min >= self.price_max:
            raise ValueError("price_min must be < price_max")
        if self.discount_pct_min > self.discount_pct_max:
            raise ValueError("discount_pct_min must be <= discount_pct_max")
        if self.trial_days_min > self.trial_days_max:
            raise ValueError("trial_days_min must be <= trial_days_max")


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    objective: str = Field(..., description="Business KPI to maximize, e.g. 'revenue_per_user'")
    space: VariableSpace
    seed: conint(ge=0, le=2_000_000_000) = Field(42, description="Seed for reproducibility")
    random_exploration_trials: conint(ge=0, le=10_000) = Field(10, description="K random exploration trials")


class ExperimentOut(BaseModel):
    id: int
    name: str
    objective: str
    created_at: datetime
    space: dict[str, Any]
    seed: int
    random_exploration_trials: int


class SuggestIn(BaseModel):
    experiment_id: int


class SuggestOut(BaseModel):
    experiment_id: int
    trial_id: int
    params: dict[str, Any]
    strategy: str


class ReportIn(BaseModel):
    experiment_id: int
    trial_id: int | None = None
    params: dict[str, Any]
    reward: float
    metadata: dict[str, Any] | None = None


class ReportOut(BaseModel):
    trial_id: int
    status: str
    reward: float


class LeaderboardEntry(BaseModel):
    trial_id: int
    reward: float
    params: dict[str, Any]
    created_at: datetime


class LeaderboardOut(BaseModel):
    experiment_id: int
    top: list[LeaderboardEntry]


class SimulateRewardIn(BaseModel):
    params: dict[str, Any]


class SimulateRewardOut(BaseModel):
    reward: float


# -----------------------------
# Helpers
# -----------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_experiment_or_404(db: Session, experiment_id: int) -> Experiment:
    exp = db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


def _validate_params_against_space(space: dict[str, Any], params: dict[str, Any]) -> None:
    """
    Validate that params respect the experiment's variable space.
    This prevents accidental/off-range reports and protects the audit trail.
    """
    required = ["price", "discount_pct", "trial_days", "onboarding_variant"]
    for k in required:
        if k not in params:
            raise HTTPException(status_code=422, detail=f"Missing parameter '{k}'")

    price = params["price"]
    discount = params["discount_pct"]
    trial_days = params["trial_days"]
    variant = params["onboarding_variant"]

    if not isinstance(price, (int, float)):
        raise HTTPException(status_code=422, detail="price must be a number")
    if not isinstance(discount, int):
        raise HTTPException(status_code=422, detail="discount_pct must be an int")
    if not isinstance(trial_days, int):
        raise HTTPException(status_code=422, detail="trial_days must be an int")
    if not isinstance(variant, str):
        raise HTTPException(status_code=422, detail="onboarding_variant must be a string")

    if not (space["price_min"] <= float(price) <= space["price_max"]):
        raise HTTPException(status_code=422, detail="price out of range")
    if not (space["discount_pct_min"] <= int(discount) <= space["discount_pct_max"]):
        raise HTTPException(status_code=422, detail="discount_pct out of range")
    if not (space["trial_days_min"] <= int(trial_days) <= space["trial_days_max"]):
        raise HTTPException(status_code=422, detail="trial_days out of range")
    if variant not in space["onboarding_variants"]:
        raise HTTPException(status_code=422, detail="onboarding_variant not in allowed variants")


# -----------------------------
# Routes
# -----------------------------
@router.post("/experiments", response_model=ExperimentOut)
def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)) -> ExperimentOut:
    try:
        payload.space.validate_ranges()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    exp = Experiment(
        name=payload.name,
        objective=payload.objective,
        created_at=_utcnow(),
        space_json=payload.space.model_dump(),
        seed=int(payload.seed),
        random_exploration_trials=int(payload.random_exploration_trials),
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    log.info("experiment_created", extra={"experiment_id": exp.id, "objective": exp.objective})
    return ExperimentOut(
        id=exp.id,
        name=exp.name,
        objective=exp.objective,
        created_at=exp.created_at,
        space=exp.space_json,
        seed=exp.seed,
        random_exploration_trials=exp.random_exploration_trials,
    )


@router.post("/suggest", response_model=SuggestOut)
def suggest_next(payload: SuggestIn, db: Session = Depends(get_db)) -> SuggestOut:
    exp = _get_experiment_or_404(db, payload.experiment_id)

    service = OptimizerService(seed=exp.seed)
    params, strategy = service.suggest(
        experiment=exp,
        completed_trials=service.fetch_completed_trials(db, exp.id),
    )

    # Create an audit trail entry for the suggestion (pending until reported)
    t = Trial(
        experiment_id=exp.id,
        params_json=params,
        reward=None,
        status="suggested",
        created_at=_utcnow(),
        metadata_json={"strategy": strategy},
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    log.info(
        "trial_suggested",
        extra={"experiment_id": exp.id, "trial_id": t.id, "strategy": strategy},
    )

    return SuggestOut(experiment_id=exp.id, trial_id=t.id, params=params, strategy=strategy)


@router.post("/report", response_model=ReportOut)
def report_result(payload: ReportIn, db: Session = Depends(get_db)) -> ReportOut:
    exp = _get_experiment_or_404(db, payload.experiment_id)

    _validate_params_against_space(exp.space_json, payload.params)

    if payload.trial_id is not None:
        trial = db.get(Trial, payload.trial_id)
        if not trial or trial.experiment_id != exp.id:
            raise HTTPException(status_code=404, detail="Trial not found for this experiment")

        # Prevent double reporting.
        if trial.status == "completed":
            raise HTTPException(status_code=409, detail="Trial already completed")

        trial.params_json = payload.params
        trial.reward = float(payload.reward)
        trial.status = "completed"
        trial.metadata_json = payload.metadata
        db.add(trial)
        db.commit()
        db.refresh(trial)

        log.info(
            "trial_reported",
            extra={"experiment_id": exp.id, "trial_id": trial.id, "reward": trial.reward},
        )
        return ReportOut(trial_id=trial.id, status=trial.status, reward=float(trial.reward))

    # If no trial_id, create a completed trial record (still validated).
    trial = Trial(
        experiment_id=exp.id,
        params_json=payload.params,
        reward=float(payload.reward),
        status="completed",
        created_at=_utcnow(),
        metadata_json=payload.metadata,
    )
    db.add(trial)
    db.commit()
    db.refresh(trial)

    log.info(
        "trial_reported_no_id",
        extra={"experiment_id": exp.id, "trial_id": trial.id, "reward": trial.reward},
    )
    return ReportOut(trial_id=trial.id, status=trial.status, reward=float(trial.reward))


@router.get("/experiments/{experiment_id}/leaderboard", response_model=LeaderboardOut)
def leaderboard(
    experiment_id: int = Path(..., ge=1),
    n: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> LeaderboardOut:
    _ = _get_experiment_or_404(db, experiment_id)

    q = (
        select(Trial)
        .where(Trial.experiment_id == experiment_id)
        .where(Trial.status == "completed")
        .where(Trial.reward.is_not(None))
        .order_by(desc(Trial.reward))
        .limit(n)
    )
    rows = db.execute(q).scalars().all()
    top = [
        LeaderboardEntry(
            trial_id=t.id,
            reward=float(t.reward),
            params=t.params_json,
            created_at=t.created_at,
        )
        for t in rows
    ]
    return LeaderboardOut(experiment_id=experiment_id, top=top)


# ---- Optional helper endpoint for simulation (kept private-ish by name) ----
@router.post("/experiments/{experiment_id}/_simulate_reward", response_model=SimulateRewardOut)
def simulate_reward_endpoint(
    payload: SimulateRewardIn,
    experiment_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> SimulateRewardOut:
    exp = _get_experiment_or_404(db, experiment_id)
    _validate_params_against_space(exp.space_json, payload.params)
    reward = simulate_revenue_per_user(payload.params, seed=exp.seed)
    return SimulateRewardOut(reward=float(reward))