from __future__ import annotations

import math
from typing import Any

import numpy as np


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def simulate_revenue_per_user(params: dict[str, Any], seed: int = 42) -> float:
    """
    Hidden objective function with noise.
    We pretend the true optimum is unknown to the optimizer.

    Decision variables:
      - price (float)
      - discount_pct (0-50)
      - trial_days (0-30)
      - onboarding_variant (A/B/C)
    Output:
      - revenue_per_user (float), noisy

    Notes:
    - The function is shaped so that:
      * too-high price hurts conversion
      * some discount can improve conversion, but too much reduces revenue
      * moderate trial length helps, too long reduces urgency
      * onboarding_variant has a real effect
    """
    rng = np.random.RandomState(seed + _stable_hash(params) % 10_000)

    price = float(params["price"])
    discount = float(params["discount_pct"])
    trial_days = float(params["trial_days"])
    variant = str(params["onboarding_variant"])

    # "True" sweet spots (hidden)
    price_opt = 49.0
    discount_opt = 12.0
    trial_opt = 14.0

    # Variant effect (hidden)
    variant_bonus = {"A": 0.00, "B": 0.08, "C": -0.04}.get(variant, 0.0)

    # Convert params into a conversion probability (0..1)
    # Penalize distance from optimum with smooth quadratic terms
    conv_score = (
        2.2
        - 0.0025 * (price - price_opt) ** 2
        - 0.0100 * (discount - discount_opt) ** 2
        - 0.0080 * (trial_days - trial_opt) ** 2
        + variant_bonus
    )
    conversion_prob = _sigmoid(conv_score)

    # Average paid revenue per converted user: price after discount, with some diminishing returns.
    effective_price = price * (1.0 - discount / 100.0)
    monetization = effective_price * (0.85 + 0.15 * _sigmoid((60 - price) / 10.0))

    # Expected revenue per user = conversion * monetization
    expected_rpu = conversion_prob * monetization

    # Add realistic noise
    noise = rng.normal(loc=0.0, scale=max(0.5, 0.05 * expected_rpu))
    observed = max(0.0, expected_rpu + noise)

    return float(observed)


def _stable_hash(obj: dict[str, Any]) -> int:
    """
    Produce a stable-ish integer hash from param dict without relying on Python's randomized hash().
    """
    s = f"{obj.get('price')}|{obj.get('discount_pct')}|{obj.get('trial_days')}|{obj.get('onboarding_variant')}"
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h *= 16777619
        h &= 0xFFFFFFFF
    return int(h)