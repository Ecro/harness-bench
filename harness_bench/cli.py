"""bench — 카나리, 측정, 원장, 처방."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.config import CONFIG
from .core.ledger import store
from .core.ledger.profile import Profile, Trait
from .core.runner.adapters import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _experiment(name: str):
    if name != "review_convergence":
        sys.exit(f"unknown experiment: {name}")
    from .experiments import review_convergence as exp
    from .experiments.review_convergence import run, traits
    return exp, run, traits


def cmd_canary(a) -> int:
    from .experiments.review_convergence.canary import build, plant
    scratch = CONFIG.scratch_root / "canary" / a.model
    plant(scratch)
    c = build().run(a.model, scratch,
                    extra_argv=["--permission-mode", "bypassPermissions"]
                    if a.model == "claude" else [])
    print(c.report())
    if not c.passed:
        print("\n판정: ★중단★  — POS 실패는 격리 성공이 아니라 프로브 고장이다")
        return 1
    print("\n판정: 진행 가능")
    return 0


def cmd_run(a) -> int:
    _, run, _ = _experiment(a.exp)
    p = run.measure(a.model, a.task, n_spread=a.spread, n_rounds=a.rounds)
    out = store.write(p, RESULTS)
    print(f"\n→ {out.relative_to(ROOT)}")
    return 0


def cmd_compare(a) -> int:
    _, _, traits = _experiment(a.exp)
    rows = store.load_all(RESULTS)
    md = store.render_ledger(rows, traits.TRAIT_KEYS)
    (RESULTS / "ledger.md").write_text(md)
    print(md)
    return 0


def cmd_prescribe(a) -> int:
    _, _, traits = _experiment(a.exp)
    rows = [r for r in store.load_all(RESULTS) if r["model"] == a.model]
    if not rows:
        sys.exit(f"no results for {a.model} — run `bench run --model {a.model}` first")
    r = rows[-1]
    p = Profile(r["model"], r.get("model_version"), r["experiment"],
                {k: Trait(**v) for k, v in r["traits"].items()},
                exploratory=r.get("exploratory", False),
                tools_blockable=r.get("tools_blockable"),
                total_calls=r.get("total_calls", 0),
                total_cost_usd=r.get("total_cost_usd"))
    print(p.render(traits.RULES))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("bench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, extra in (
        ("canary", cmd_canary, []),
        ("run", cmd_run, [("--task", "retry_policy"), ("--spread", 5), ("--rounds", 5)]),
        ("compare", cmd_compare, []),
        ("prescribe", cmd_prescribe, []),
    ):
        p = sub.add_parser(name)
        if name != "compare":
            p.add_argument("--model", required=True, choices=sorted(REGISTRY))
        p.add_argument("--exp", default="review_convergence")
        for flag, default in extra:
            p.add_argument(flag, type=type(default), default=default)
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
