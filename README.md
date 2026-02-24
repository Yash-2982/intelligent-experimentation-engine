# 🚀 Intelligent Experimentation Engine

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-production-green)
![Docker](https://img.shields.io/badge/Docker-containerized-blue)
![Optuna](https://img.shields.io/badge/Optuna-TPE-orange)
![CI](https://github.com/Yash-2982/intelligent-experimentation-engine/actions/workflows/ci.yml/badge.svg)

> A production-style experimentation backend that autonomously recommends optimal configurations using Bayesian Optimization (Optuna TPE), maintains a complete audit trail, and simulates SaaS revenue optimization.

---

## 🔬 Problem Statement

Build a system that **automatically recommends the next best experiment configuration** to maximize a business KPI, **learns from results**, and maintains a full audit trail.

Modern SaaS companies continuously experiment with:
- Pricing strategies
- Discount percentages
- Free trial durations
- Onboarding variants

The key question:
> **What configuration should we try next to maximize revenue?**

This project implements a production-style experimentation engine that:
- Creates an experiment space (decision variables + objective)
- Suggests the next configuration to try
- Accepts reported results
- Ranks top configurations (leaderboard)
- Supports a simulation runner to demonstrate iterative improvement

---

## 🎯 Real-World Use Case — SaaS Pricing & Revenue Optimization

We want to maximize **revenue_per_user** for a SaaS product.

### Decision Variables

| Variable | Type | Range |
|----------|------|--------|
| `price` | float | 10–100 |
| `discount_pct` | int | 0–50 |
| `trial_days` | int | 0–30 |
| `onboarding_variant` | categorical | A / B / C |

### Reward

`revenue_per_user` (float) computed by a hidden (simulated) objective function with noise.

The engine discovers better configurations over iterations using:
- **Random exploration** for the first K trials
- **Optuna TPE (Bayesian optimization)** afterward
- Deterministic seeding for reproducibility

---

## 🏗 Architecture Overview

```
Client
  ↓
FastAPI REST API
  ↓
Optimizer Service (Random + Optuna TPE)
  ↓
SQLAlchemy ORM
  ↓
SQLite (MVP) / Postgres-ready
  ↓
Simulation Engine (Hidden Objective)
```

---

## ⚙️ Technology Stack

- Python 3.9+
- FastAPI
- SQLAlchemy
- SQLite (Postgres-compatible)
- Optuna (TPE sampler)
- Docker & Docker Compose
- Pytest
- GitHub Actions CI

---

## 📂 Project Structure

```
repo/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── services/
│   ├── simulate.py
│   └── main.py
├── tests/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

Clean separation of:
- API Layer
- Business Logic (Optimizer)
- Database Models
- Simulation Layer

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/experiments` | Create experiment space |
| `POST` | `/suggest` | Get next suggested configuration |
| `POST` | `/report` | Submit observed reward |
| `GET` | `/experiments/{id}/leaderboard?n=10` | Top configs |
| `GET` | `/health` | Service health check |

> `POST /experiments/{id}/_simulate_reward` exists only for the included simulator.  
> In production, rewards would come from real analytics pipelines.

---

## 🚀 Run Locally (Docker)

### Build and Start

```bash
docker compose up --build
```

This will:
- Build the Docker image
- Start the FastAPI service
- Create the SQLite database
- Expose the API on port 8000

### Access the Service

- **Health:** http://localhost:8000/health
- **Swagger Docs:** http://localhost:8000/docs

### Stop the Service

```bash
# CTRL + C or:
docker compose down
```

---

## 🧪 Run Without Docker (Development Mode)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: http://localhost:8000/docs

---

## 📊 Example Optimization Run

```bash
python -m app.simulate --experiment_id 1 --n_trials 100
```

Example output:

```
[001/100] reward=6.21   best=6.21
[010/100] reward=9.87   best=10.22
[050/100] reward=12.41  best=12.88
[100/100] reward=11.98  best=13.01

Best found configuration:
  price               ≈ 49
  discount_pct        ≈ 12
  trial_days          ≈ 14
  onboarding_variant  = B
```

The engine converges toward the hidden optimum.

---

## 🗄 Data Model

**Experiment**
```
id
name
objective
space_json
seed
random_exploration_trials
created_at
```

**Trial**
```
id
experiment_id
params_json
reward
status
metadata_json
created_at
```

Every suggestion and result is persisted → full auditability.

---

## 🔐 Production Features

- Deterministic seeding
- Structured JSON logging
- Input validation (Pydantic)
- Clean error handling
- Layered architecture
- Dockerized deployment
- CI-tested
- Postgres-ready design

---

## 📈 Why This Is Production-Grade

Unlike toy ML demos, this project includes:

- REST experiment lifecycle management
- Persistent optimization state
- Reproducible Bayesian optimization
- Service-layer abstraction
- CI pipeline
- Containerization
- Clean modular design

This mirrors experimentation systems used in:
- SaaS pricing optimization
- Growth experimentation
- A/B testing platforms
- Marketing optimization engines

---

## 🛠 Future Improvements

- Alembic migrations
- Postgres production configuration
- Authentication middleware
- Concurrency-safe suggestion locking
- Multi-objective optimization
- AWS deployment (EC2 / ECS)

---

## 👨‍💻 Author

**Yash Rahul Chitte**  
MS Computer Science — Stevens Institute of Technology  