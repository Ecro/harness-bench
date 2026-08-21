"""Label-invariant agreement between clusterings (PLAN ADR-008).

Three independent clustering runs produce different cluster COUNTS and their labels are
permutation-invariant, so per-item label equality is undefined -- an earlier draft of the plan
gated on "<=10% assignment disagreement", which is not a computable quantity. Adjusted Rand
Index and Variation of Information both compare the induced PARTITIONS, so they are defined
regardless of labelling and of how many clusters each run produced.

No sklearn dependency: the contingency-table forms are short, and a hand-written version can
be unit-tested against known values instead of trusted.
"""

from __future__ import annotations

import math
from collections import Counter


def _comb2(n: int) -> int:
    return n * (n - 1) // 2


def contingency(a: dict[str, str], b: dict[str, str]) -> tuple[Counter, Counter, Counter, int]:
    """Cross-tabulate two labelings over their SHARED items.

    Restricting to shared items is deliberate: a clustering run that dropped or hallucinated
    an item must not silently change the denominator. Callers check the shared count.
    """
    keys = sorted(set(a) & set(b))
    joint = Counter((a[k], b[k]) for k in keys)
    ca = Counter(a[k] for k in keys)
    cb = Counter(b[k] for k in keys)
    return joint, ca, cb, len(keys)


def adjusted_rand_index(a: dict[str, str], b: dict[str, str]) -> float:
    """ARI: 1.0 = identical partitions, ~0 = chance, can be negative (worse than chance)."""
    joint, ca, cb, n = contingency(a, b)
    if n < 2:
        return float("nan")

    sum_ij = sum(_comb2(v) for v in joint.values())
    sum_a = sum(_comb2(v) for v in ca.values())
    sum_b = sum(_comb2(v) for v in cb.values())
    total = _comb2(n)
    expected = (sum_a * sum_b) / total if total else 0.0
    max_index = 0.5 * (sum_a + sum_b)
    denom = max_index - expected
    if denom == 0:
        # Both partitions are all-singletons or all-one-cluster: they agree perfectly and
        # the index is degenerate. Returning 1.0 is correct and avoids a ZeroDivisionError
        # at exactly the boundary a gate is most likely to be evaluated on.
        return 1.0
    return (sum_ij - expected) / denom


def variation_of_information(a: dict[str, str], b: dict[str, str]) -> float:
    """VI in nats. 0 = identical. Unlike ARI it is a metric, so it is reported alongside:
    ARI can look healthy while a few large clusters absorb the disagreement."""
    joint, ca, cb, n = contingency(a, b)
    if n == 0:
        return float("nan")

    vi = 0.0
    for (la, lb), nij in joint.items():
        pij = nij / n
        pa = ca[la] / n
        pb = cb[lb] / n
        vi -= pij * (math.log(pij / pa) + math.log(pij / pb))
    return vi


def medoid(labelings: list[dict[str, str]]) -> tuple[int, list[list[float]]]:
    """Index of the labeling with the highest MEAN ARI to the others, plus the ARI matrix.

    Chosen over a thresholded majority-co-assignment consensus because majority
    co-assignment is NOT transitive (x~y in runs 1,2; y~z in 1,3; x~z in 1 only), so it does
    not define a partition at all -- whichever repair the implementer reached for would be an
    unrecorded analyst degree of freedom sitting above every downstream number.

    Ties break on lowest mean VI, then lowest index, so the choice never falls to dict order.
    """
    k = len(labelings)
    ari = [[1.0] * k for _ in range(k)]
    vi = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(i + 1, k):
            ari[i][j] = ari[j][i] = adjusted_rand_index(labelings[i], labelings[j])
            vi[i][j] = vi[j][i] = variation_of_information(labelings[i], labelings[j])

    def mean_off(row: list[float], i: int) -> float:
        others = [v for j, v in enumerate(row) if j != i]
        return sum(others) / len(others) if others else float("nan")

    best = min(
        range(k),
        key=lambda i: (-mean_off(ari[i], i), mean_off(vi[i], i), i),
    )
    return best, ari


def mean_pairwise_ari(labelings: list[dict[str, str]]) -> float:
    vals = [
        adjusted_rand_index(labelings[i], labelings[j])
        for i in range(len(labelings))
        for j in range(i + 1, len(labelings))
    ]
    return sum(vals) / len(vals) if vals else float("nan")


def is_valid_partition(labeling: dict[str, str], items: list[str]) -> bool:
    """Every item in exactly one cluster, nothing invented. The property a consensus rule can
    silently violate, so it is asserted rather than assumed."""
    return set(labeling) == set(items)
