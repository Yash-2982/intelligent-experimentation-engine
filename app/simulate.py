from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests

from app.core.config import settings


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulation runner for Intelligent Experimentation Engine")
    parser.add_argument("--experiment_id", type=int, required=True)
    parser.add_argument("--n_trials", type=int, default=100)
    parser.add_argument("--base_url", type=str, default=settings.API_BASE_URL)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    experiment_id = args.experiment_id
    n_trials = args.n_trials

    print(f"Running simulation: experiment_id={experiment_id}, n_trials={n_trials}, base_url={base_url}")

    best_reward = float("-inf")
    best_params: dict[str, Any] = {}

    for i in range(1, n_trials + 1):
        s = requests.post(f"{base_url}/suggest", json={"experiment_id": experiment_id}, timeout=20)
        s.raise_for_status()
        suggestion = s.json()
        trial_id = suggestion["trial_id"]
        params = suggestion["params"]

        # Evaluate simulated reward locally (hidden optimum).
        sim = requests.post(
            f"{base_url}/experiments/{experiment_id}/_simulate_reward",
            json={"params": params},
            timeout=20,
        )
        sim.raise_for_status()
        reward = sim.json()["reward"]

        r = requests.post(
            f"{base_url}/report",
            json={
                "experiment_id": experiment_id,
                "trial_id": trial_id,
                "params": params,
                "reward": reward,
                "metadata": {"iteration": i, "source": "simulate.py"},
            },
            timeout=20,
        )
        r.raise_for_status()
        reported = r.json()

        if reward > best_reward:
            best_reward = reward
            best_params = params

        if i % 10 == 0 or i == 1:
            print(f"[{i:03d}/{n_trials}] reward={reward:.4f} best={best_reward:.4f}")

    print("\nBest found configuration:")
    print(_pretty({"best_reward": best_reward, "best_params": best_params}))

    lb = requests.get(f"{base_url}/experiments/{experiment_id}/leaderboard?n=5", timeout=20)
    lb.raise_for_status()
    print("\nTop 5 leaderboard:")
    print(_pretty(lb.json()))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as e:
        print(f"Request error: {e}", file=sys.stderr)
        raise SystemExit(2)