"""Interval estimates for small-sample reporting (decision 17).

Proportions (hit@k, abstention, validity, label shares) get a 95% Wilson
interval. Means of per-question scores (recall@k, MRR) are not proportions, so
they get a fixed-seed percentile bootstrap interval instead.
"""

import math

import numpy as np

Z_95 = 1.959963984540054
BOOTSTRAP_SEED = 2026
BOOTSTRAP_RESAMPLES = 10_000


def wilson(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_mean(values: list[float], seed: int = BOOTSTRAP_SEED,
                   resamples: int = BOOTSTRAP_RESAMPLES) -> tuple[float, float]:
    if not values:
        return (0.0, 1.0)
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = data[rng.integers(0, len(data), size=(resamples, len(data)))].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return (float(low), float(high))


def proportion(successes: int, n: int) -> dict:
    low, high = wilson(successes, n)
    return {"count": successes, "n": n, "rate": successes / n if n else None,
            "ci95": [low, high], "interval": "wilson"}


def mean_with_ci(values: list[float]) -> dict:
    low, high = bootstrap_mean(values)
    return {"n": len(values), "mean": sum(values) / len(values) if values else None,
            "ci95": [low, high], "interval": f"bootstrap_percentile_seed{BOOTSTRAP_SEED}_{BOOTSTRAP_RESAMPLES}"}
