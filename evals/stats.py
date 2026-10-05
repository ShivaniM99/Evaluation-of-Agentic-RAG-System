"""Aggregation + agreement statistics."""
import math
import random


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def percentile(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bootstrap_ci(xs, n=1000, alpha=0.05, seed=0):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return (None, None)
    rng = random.Random(seed)
    means = sorted(mean([rng.choice(xs) for _ in xs]) for _ in range(n))
    return (means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n) - 1])


def cohens_kappa(a: list, b: list) -> float | None:
    """Cohen's kappa for two raters over the same items (any hashable labels)."""
    assert len(a) == len(b)
    n = len(a)
    if n == 0:
        return None
    labels = set(a) | set(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def stdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
