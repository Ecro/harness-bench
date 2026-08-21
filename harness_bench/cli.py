"""bench -- canary, measure, ledger, prescribe.

The CLI is experiment-agnostic. It discovers experiments under `harness_bench.experiments`
and drives whichever one `--exp` names; every command routes through that experiment's own
modules. An experiment is drivable by this CLI when it ships:

    canary.build() / canary.plant(scratch)     the two-way isolation probe
    run.measure(model, task, ...) -> Profile   the measurement
    traits.TRAIT_KEYS / traits.RULES           what it measures, and what that decides

Nothing here may know what any of those mean.
"""
from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

from . import experiments as _experiments_pkg
from .core.config import CONFIG
from .core.ledger import store
from .core.ledger.profile import Profile, Trait
from .core.runner.adapters import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

EXPERIMENTS = sorted(m.name for m in pkgutil.iter_modules(_experiments_pkg.__path__)
                     if m.ispkg)


def _load(exp: str, module: str):
    if exp not in EXPERIMENTS:
        sys.exit(f"unknown experiment: {exp} (have: {', '.join(EXPERIMENTS) or 'none'})")
    try:
        return importlib.import_module(f".experiments.{exp}.{module}", __package__)
    except ModuleNotFoundError as e:
        sys.exit(f"experiment {exp} ships no {module} module — it cannot be driven by "
                 f"`bench` until it does ({e})")


def cmd_canary(a) -> int:
    canary = _load(a.exp, "canary")
    scratch = CONFIG.scratch_root / "canary" / a.exp / a.model
    canary.plant(scratch)
    c = canary.build().run(a.model, scratch)
    print(c.report())
    if not c.passed:
        print("\nVERDICT: STOP -- a failed POS leg is a broken probe, not isolation."
              "\n        Data collected in this state is void.")
        return 1
    print("\nVERDICT: clear to proceed")
    return 0


def cmd_run(a) -> int:
    run = _load(a.exp, "run")
    kw = {} if a.task is None else {"task_slug": a.task}
    p = run.measure(a.model, n_spread=a.spread, n_rounds=a.rounds, n_loops=a.loops, **kw)
    out = store.write(p, RESULTS)
    print(f"\n→ {out.relative_to(ROOT)}")
    return 0


def _rows(exp: str, model: str | None = None) -> list[dict]:
    # A profile records "<experiment>/<task>"; select on the experiment half.
    rows = [r for r in store.load_all(RESULTS)
            if str(r.get("experiment", "")).split("/")[0] == exp]
    return [r for r in rows if model is None or r["model"] == model]


def cmd_compare(a) -> int:
    traits = _load(a.exp, "traits")
    md = store.render_ledger(_rows(a.exp), traits.TRAIT_KEYS)
    # One ledger per experiment: trait columns are an experiment's own vocabulary, and rows
    # from two experiments in one table would share a header that fits neither.
    (RESULTS / f"ledger-{a.exp}.md").write_text(md)
    print(md)
    return 0


def cmd_prescribe(a) -> int:
    traits = _load(a.exp, "traits")
    rows = _rows(a.exp, a.model)
    if not rows:
        sys.exit(f"no {a.exp} results for {a.model} — run "
                 f"`bench run --exp {a.exp} --model {a.model}` first")
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
        ("run", cmd_run, [("--task", str, None), ("--spread", int, 5), ("--rounds", int, 5),
                          ("--loops", int, 1)]),
        ("compare", cmd_compare, []),
        ("prescribe", cmd_prescribe, []),
    ):
        p = sub.add_parser(name)
        if name != "compare":
            p.add_argument("--model", required=True, choices=sorted(REGISTRY))
        # A default is only offered while the suite holds one experiment. The second one
        # makes --exp mandatory rather than silently inheriting the first's meaning.
        p.add_argument("--exp", choices=EXPERIMENTS, required=len(EXPERIMENTS) != 1,
                       default=EXPERIMENTS[0] if len(EXPERIMENTS) == 1 else None)
        for flag, typ, default in extra:
            p.add_argument(flag, type=typ, default=default)
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
