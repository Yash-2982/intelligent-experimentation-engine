from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import optuna
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Experiment, Trial


@dataclass(frozen=True)
class CompletedTrial:
    params: dict[str, Any]
    reward: float


class OptimizerService:
    """
    Optimizer logic:
    - First K completed trials: random exploration (reproducible).
    - After that: Optuna TPE sampler, with study reconstructed from DB history.
    """

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)

    def fetch_completed_trials(self, db: Session, experiment_id: int) -> list[CompletedTrial]:
        q = (
            select(Trial)
            .where(Trial.experiment_id == experiment_id)
            .where(Trial.status == "completed")
            .where(Trial.reward.is_not(None))
            .order_by(Trial.id.asc())
        )
        rows = db.execute(q).scalars().all()
        out: list[CompletedTrial] = []
        for t in rows:
            if t.reward is None:
                continue
            out.append(CompletedTrial(params=t.params_json, reward=float(t.reward)))
        return out

    def suggest(self, experiment: Experiment, completed_trials: list[CompletedTrial]) -> tuple[dict[str, Any], str]:
        space = experiment.space_json
        k = int(experiment.random_exploration_trials)

        if len(completed_trials) < k:
            params = self._suggest_random(space, n_completed=len(completed_trials))
            return params, "random"

        params = self._suggest_optuna_tpe(space, completed_trials=completed_trials)
        return params, "optuna_tpe"

    def _suggest_random(self, space: dict[str, Any], n_completed: int) -> dict[str, Any]:
        """
        Deterministic random suggestion based on (seed + n_completed),
        so the first K are reproducible across restarts.
        """
        rng = np.random.RandomState(self.seed + int(n_completed))

        price = float(rng.uniform(space["price_min"], space["price_max"]))
        discount = int(rng.randint(space["discount_pct_min"], space["discount_pct_max"] + 1))
        trial_days = int(rng.randint(space["trial_days_min"], space["trial_days_max"] + 1))
        variant = str(rng.choice(space["onboarding_variants"]))

        return {
            "price": round(price, 2),
            "discount_pct": discount,
            "trial_days": trial_days,
            "onboarding_variant": variant,
        }

    def _suggest_optuna_tpe(self, space: dict[str, Any], completed_trials: list[CompletedTrial]) -> dict[str, Any]:
        """
        Rebuild an Optuna study from completed trials, then ask for a new suggestion.

        This keeps Optuna storage optional/free while still using TPE.
        (For production at scale: use Optuna RDB storage + Postgres.)
        """
        sampler = optuna.samplers.TPESampler(seed=self.seed, multivariate=True, group=True)
        study = optuna.create_study(direction="maximize", sampler=sampler)

        # Feed prior observations into the study
        for ct in completed_trials:
            distributions = {
                "price": optuna.distributions.FloatDistribution(float(space["price_min"]), float(space["price_max"])),
                "discount_pct": optuna.distributions.IntDistribution(int(space["discount_pct_min"]), int(space["discount_pct_max"])),
                "trial_days": optuna.distributions.IntDistribution(int(space["trial_days_min"]), int(space["trial_days_max"])),
                "onboarding_variant": optuna.distributions.CategoricalDistribution(list(space["onboarding_variants"])),
            }

            # Basic sanity: coerce types
            p = {
                "price": float(ct.params["price"]),
                "discount_pct": int(ct.params["discount_pct"]),
                "trial_days": int(ct.params["trial_days"]),
                "onboarding_variant": str(ct.params["onboarding_variant"]),
            }

            # Guard against NaN/infs sneaking in
            val = float(ct.reward)
            if math.isnan(val) or math.isinf(val):
                continue

            trial = optuna.trial.create_trial(params=p, distributions=distributions, value=val)
            study.add_trial(trial)

        # Ask Optuna for a new candidate
        t = study.ask(
            fixed_distributions={
                "price": optuna.distributions.FloatDistribution(float(space["price_min"]), float(space["price_max"])),
                "discount_pct": optuna.distributions.IntDistribution(int(space["discount_pct_min"]), int(space["discount_pct_max"])),
                "trial_days": optuna.distributions.IntDistribution(int(space["trial_days_min"]), int(space["trial_days_max"])),
                "onboarding_variant": optuna.distributions.CategoricalDistribution(list(space["onboarding_variants"])),
            }
        )
        params = t.params

        # Clean up / normalize
        return {
            "price": round(float(params["price"]), 2),
            "discount_pct": int(params["discount_pct"]),
            "trial_days": int(params["trial_days"]),
            "onboarding_variant": str(params["onboarding_variant"]),
        }