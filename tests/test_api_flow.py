from __future__ import annotations


def test_end_to_end_flow(client):
    # create experiment
    resp = client.post(
        "/experiments",
        json={
            "name": "SaaS Pricing Optimization",
            "objective": "revenue_per_user",
            "seed": 123,
            "random_exploration_trials": 3,
            "space": {
                "price_min": 10.0,
                "price_max": 100.0,
                "discount_pct_min": 0,
                "discount_pct_max": 50,
                "trial_days_min": 0,
                "trial_days_max": 30,
                "onboarding_variants": ["A", "B", "C"],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    exp = resp.json()
    exp_id = exp["id"]

    # run a few suggest -> simulate -> report loops
    for _ in range(8):
        s = client.post("/suggest", json={"experiment_id": exp_id})
        assert s.status_code == 200, s.text
        suggestion = s.json()
        trial_id = suggestion["trial_id"]
        params = suggestion["params"]

        sim = client.post(f"/experiments/{exp_id}/_simulate_reward", json={"params": params})
        assert sim.status_code == 200, sim.text
        reward = sim.json()["reward"]

        r = client.post(
            "/report",
            json={
                "experiment_id": exp_id,
                "trial_id": trial_id,
                "params": params,
                "reward": reward,
                "metadata": {"test": True},
            },
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["trial_id"] == trial_id
        assert out["status"] == "completed"

    lb = client.get(f"/experiments/{exp_id}/leaderboard?n=5")
    assert lb.status_code == 200, lb.text
    top = lb.json()["top"]
    assert len(top) <= 5
    # rewards should be sorted desc
    rewards = [row["reward"] for row in top]
    assert rewards == sorted(rewards, reverse=True)