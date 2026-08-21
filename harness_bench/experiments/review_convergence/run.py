"""Measurement plan for this experiment -- what `bench run` actually does.

Cost of one tier-1 profile:

    spread    n_spread calls              repeated review of the verified v0; code never
                                          changes, so the observation IS the variance
    loop      n_loops x n_rounds x 2      review -> fix -> oracle
    derived   0 calls                     LOC, compliance, malformed and rejection rates
                                          all fall out of the artefacts above

Defaults come to ~35 calls per model. Adding a new model to the table should cost about
that; make it more expensive and nobody adds one.

No retries. A failed round stops that loop and only the observations up to it are used.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from ...core.config import CONFIG
from ...core.ledger.profile import Profile, Trait
from ...core.runner.adapters import REGISTRY
from ...core.runner.call import call, save
from . import oracle
from .tasks import TASKS

HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"


def _compose_review(spec: str, module: str) -> str:
    return (f"```\n{spec}\n```\n\n```python\n{module}\n```\n"
            + (PROMPTS / "review_structured.txt").read_text())


def _compose_fix(spec: str, module: str, findings: list) -> str:
    return (f"```\n{spec}\n```\n\n```python\n{module}\n```\n"
            + (PROMPTS / "fix_instruction.txt").read_text()
            + json.dumps(findings, indent=2, ensure_ascii=False) + "\n")


DRY_THRESHOLD = 0.7
MIN_POINTS = 4
MIN_LOOPS = 3


def _dries(churns: list[int]) -> bool | None:
    r = _ratio(churns)
    return None if r is None else r < DRY_THRESHOLD


def _dries_across(series: list[list[int]]) -> tuple[bool | None, list, str]:
    """Combine the per-loop verdicts.

    Churn series are noisy -- a single loop can go 106, 69, 82, 51, 75 -- and the observed
    ratios for one model clustered at 0.611-0.732, straddling the 0.7 threshold. A single
    loop therefore lands on either side of the boundary by chance: one loop's direction is a
    sample, not a direction.

    So below MIN_LOOPS this returns None rather than a verdict. At or above it, majority
    rules, and a split (e.g. 2:1) is stated in the note so a majority never passes itself off
    as unanimity. Read `churn_ratio` alongside the boolean.
    """
    ratios = [_ratio(c) for c in series]
    usable = [r for r in ratios if r is not None]
    if len(usable) < MIN_LOOPS:
        return None, ratios, f"{len(usable)}/{MIN_LOOPS} loops usable -- not judged"
    votes = [r < DRY_THRESHOLD for r in usable]
    yes = sum(votes)
    verdict = yes > len(votes) / 2
    split = "unanimous" if yes in (0, len(votes)) else f"split {yes}:{len(votes)-yes}"
    return verdict, ratios, f"{split} · ratios={[round(r,3) for r in usable]}"


def _ratio(churns: list[int]) -> float | None:
    if len(churns) < 4:
        return None          # calling a trend below this is reading noise
    h = len(churns) // 2
    first = sum(churns[:h]) / h
    return round(sum(churns[-h:]) / h / first, 3) if first else None


def _churn(a: str, b: str) -> int:
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), n=0))
    return sum(1 for l in d if l[:1] in "+-" and l[:3] not in ("+++", "---"))


def measure(adapter_name: str, task_slug: str = "retry_policy", *,
            n_spread: int = 5, n_rounds: int = 5, n_loops: int = 1,
            out_dir: Path | None = None, log=print) -> Profile:
    task = TASKS[task_slug]
    if not task.reference:
        raise ValueError(f"{task_slug} ships no reference; spread needs a known-good v0")
    if not oracle.verify(task, log=lambda m: log("  " + m.strip())):
        raise RuntimeError(f"oracle for {task_slug} failed verification — no number from it "
                           "is quotable (docs/TASKS.md)")

    adapter = REGISTRY[adapter_name]()
    spec, v0 = task.spec.read_text(), task.reference.read_text()
    root = (out_dir or CONFIG.scratch_root / "run") / adapter_name / task_slug
    calls: list = []

    # --- spread: the code never changes, so the observation IS the variance -
    counts = []
    for i in range(n_spread):
        r = call(adapter, "review", _compose_review(spec, v0), root / f"spread{i}")
        calls.append(r)
        save(r, root / f"spread{i}", "review")
        n = len((r.parsed or {}).get("findings", [])) if r.status == "ok" else None
        log(f"  spread {i+1}/{n_spread}: {r.status} findings={n}")
        if n is not None:
            counts.append(n)

    # --- loop (n_loops independent repetitions) --------------------------
    all_churns: list[list[int]] = []
    round_counts: list[int] = []
    dec_total = dec_rej = 0
    ac_ok = True
    final_module = v0
    for loop in range(1, n_loops + 1):
        module, churns, counts_l = v0, [], []
        for rnd in range(1, n_rounds + 1):
            d = root / f"loop{loop}" / f"round{rnd}"
            rv = call(adapter, "review", _compose_review(spec, module), d)
            calls.append(rv); save(rv, d, "review")
            if rv.status != "ok":
                log(f"  L{loop} R{rnd}: review {rv.status} - stopping loop (no retry)"); break
            findings = (rv.parsed or {}).get("findings", [])
            counts_l.append(len(findings))
            if not findings:
                log(f"  L{loop} R{rnd}: 0 findings - loop ends"); break

            fx = call(adapter, "fix", _compose_fix(spec, module, findings), d)
            calls.append(fx); save(fx, d, "fix")
            new = (fx.parsed or {}).get("code")
            if fx.status != "ok" or not new:
                log(f"  L{loop} R{rnd}: fix {fx.status} - stopping loop (no retry)"); break

            dec = (fx.parsed or {}).get("decisions", []) or []
            dec_total += len(dec)
            dec_rej += sum(1 for x in dec if x.get("action") == "rejected")
            churns.append(_churn(module, new))
            o = oracle.run(new, task.suite, task.module_name)
            ac_ok &= o.green
            log(f"  L{loop} R{rnd}: {len(findings)} findings -> churn {churns[-1]}, "
                f"{len(new.splitlines())} loc, {o.passed}/{o.total} "
                f"{'GREEN' if o.green else 'RED'}")
            module = new
        if churns:
            all_churns.append(churns)
        if len(counts_l) > len(round_counts):
            round_counts = counts_l
        final_module = module
    module = final_module

    # --- derived (no model calls) -----------------------------------------
    _verdict, _ratios, _note = _dries_across(all_churns)
    ok = [c for c in calls if c.status == "ok"]
    cost = [c.usage.cost_usd for c in ok if c.usage.cost_usd is not None]
    toks = [c.usage.total_tokens for c in ok if c.usage.total_tokens is not None]

    def T(k, v, unit="", note=""):
        return Trait(k, v, unit, note, degraded=v is None)

    traits = {
        "spread": T("spread", (max(counts) - min(counts)) if len(counts) > 1 else None,
                    note=f"n={len(counts)} {counts}"),
        "loop_decay": T("loop_decay",
                        round((round_counts[-1] - round_counts[0]) / (len(round_counts) - 1), 2)
                        if len(round_counts) > 1 else None, note=str(round_counts)),
        # Not judged from the last value alone: churn series are noisy and a last-vs-first
        # comparison flips on a single point. Mean of the first half against the mean of the
        # last half, and below MIN_POINTS no verdict at all.
        "churn_dries": T("churn_dries", _verdict, note=_note),
        "churn_ratio": T("churn_ratio",
                         round(sum(u) / len(u), 3) if (u := [r for r in _ratios if r]) else None,
                         "last/first", note=f"per loop {[round(r,3) if r else None for r in _ratios]}"),
        "rejection_rate": T("rejection_rate",
                            round(dec_rej / dec_total, 3) if dec_total else None,
                            note=f"{dec_rej}/{dec_total}"),
        "malformed_rate": T("malformed_rate",
                            round(sum(c.status == "malformed" for c in calls) / len(calls), 3)
                            if calls else None),
        "ac_held": T("ac_held", ac_ok if all_churns else None),
        "loc_direction": T("loc_direction",
                           round(len(module.splitlines()) / len(v0.splitlines()), 3)
                           if all_churns else None, "×"),
        "tools_blockable": T("tools_blockable", adapter.tools_blockable),
        # tier-2 only -- tier-1 cannot measure these. Not filled with estimates.
        "finds_per_call": T("finds_per_call", None, note="tier-2 only (needs an adjudicated defect set)"),
        "verbosity_shift": T("verbosity_shift", None, note="tier-2 only (needs a repo-access contrast)"),
    }
    return Profile(
        adapter_name, next((c.model_version for c in ok if c.model_version), None),
        f"review_convergence/{task_slug}", traits,
        exploratory=True,          # no pre-registration for this plan yet
        tools_blockable=adapter.tools_blockable,
        total_calls=len(calls),
        total_cost_usd=round(sum(cost), 4) if cost else None,
        total_tokens=sum(toks) if toks else None,
    )
