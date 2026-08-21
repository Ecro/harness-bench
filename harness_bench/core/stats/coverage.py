"""Expected coverage at a call budget — exhaustive, no LLM calls.

When you hold N independent runs, "how much would k calls have found?" is not an estimate.
It is the mean over all C(N,k) subsets, and it is free: the runs are already paid for.

This is what turned "two models are better than one" from a judgement into a number in the
source study. Each model found 4 of 10 real defects at 10 calls, but their union was 5 --
and at small budgets a MIXED pool beat either model alone at every k >= 2:

    k=3  claude 2 + codex 1 -> 3.57      claude alone at k=6 -> 3.43

Three mixed calls beat six same-model calls. Nothing new was run to learn that.
"""
from __future__ import annotations

from itertools import combinations


def expected_union(pools: dict[str, dict[str, set]], take: dict[str, int]) -> float:
    """Mean |union of the chosen runs' hit-sets| over every combination.

    pools: {arm: {run_id: set_of_things_found}}
    take:  {arm: how many runs to draw from that arm}
    """
    arms = [a for a, n in take.items() if n > 0]
    if not arms:
        return 0.0
    per_arm = [list(combinations(sorted(pools[a]), take[a])) for a in arms]
    total = n = 0
    def walk(i: int, acc: set):
        nonlocal total, n
        if i == len(arms):
            total += len(acc); n += 1
            return
        for combo in per_arm[i]:
            walk(i + 1, acc | set().union(*(pools[arms[i]][r] for r in combo)) if combo else acc)
    walk(0, set())
    return total / n if n else 0.0


def budget_curve(pools: dict[str, dict[str, set]], ks: range | list[int],
                 mix: bool = True) -> list[dict]:
    """One row per budget k:每 arm alone, plus the best mixed split if `mix`."""
    rows = []
    for k in ks:
        row: dict = {"k": k}
        for arm, runs in pools.items():
            row[arm] = expected_union(pools, {arm: k}) if k <= len(runs) else None
        if mix and len(pools) == 2:
            a, b = list(pools)
            best, best_split = -1.0, None
            for j in range(k + 1):
                if j > len(pools[a]) or (k - j) > len(pools[b]):
                    continue
                v = expected_union(pools, {a: j, b: k - j})
                if v > best:
                    best, best_split = v, (j, k - j)
            row["mixed"], row["split"] = best, best_split
        rows.append(row)
    return rows
