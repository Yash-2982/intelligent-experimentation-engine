# Intelligent Experimentation Engine (Production-Style, Free Tools)

## Problem Statement
Build a system that **automatically recommends the next best experiment configuration** to maximize a business KPI, **learns from results**, and maintains a full **audit trail**.

This repo implements an “Intelligent Experimentation Engine” that:
- creates an experiment space (decision variables + objective),
- suggests the next configuration to try,
- accepts reported results,
- ranks top configurations (leaderboard),
- supports a simulation runner to demonstrate iterative improvement.

## Real-World Use Case: SaaS Pricing & Revenue Optimization
We want to maximize **revenue_per_user** for a SaaS product.

**Decision variables**
- `price` (float)
- `discount_pct` (0–50)
- `trial_days` (0–30)
- `onboarding_variant` (A/B/C)

**Reward**
- `revenue_per_user` (float) computed by a hidden (simulated) objective function + noise.

The engine should discover better configurations over iterations using:
- **Random exploration** for the first K trials
- **Optuna TPE** suggestions after that (reproducible seed)

## Architecture Overview
**FastAPI**
- REST endpoints for experiment lifecycle + optimization loop

**SQLAlchemy + SQLite**
- `Experiment` table: stores experiment metadata + variable space + reproducibility config
- `Trial` table: stores every suggestion + reported result (audit trail)

**Optimizer**
- Random exploration (deterministic via seed + completed-trial-count)
- Optuna TPE sampler (study reconstructed from completed trials; no paid storage needed)

**Simulation**
- Script that loops: suggest -> simulate reward -> report
- Prints best config + leaderboard summary

## API Endpoints
- `POST /experiments` : create experiment space with variable ranges and objective
- `POST /suggest` : get next suggested configuration for an experiment
- `POST /report` : submit results for a trial
- `GET /experiments/{id}/leaderboard?n=10` : top N configs by reward
- `GET /health`

> Note: `POST /experiments/{id}/_simulate_reward` exists to support the included simulator.
> In a real deployment, the reward would come from your production analytics pipeline.

## Run Locally (Docker Compose)
```bash
docker compose up --build