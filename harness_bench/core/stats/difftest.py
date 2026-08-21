"""Differential behavioural testing: v0 vs every later round.

The acceptance suite says "the contract still holds". It cannot say "the behaviour
did not change", because a contract under-determines an implementation: every AC in
SPEC-retry-policy.md can hold while the observable behaviour on inputs the ACs never
name drifts arbitrarily.

This module measures that drift. RetryPolicy has time, sleep and randomness *injected*,
so a run is completely deterministic: fix the clock, the random stream and the call
sequence, and two implementations either produce the identical observable trace or they
do not. Any difference is a behaviour change the contract never approved -- neither
authorised nor forbidden by it. Whether such a change is an improvement is a judgement
call; that it happened is a fact, and this is the fact the oracle cannot see.

What counts as observable (the trace):
  * how many times fn was called
  * the exact sequence of values handed to sleep_fn
  * the outcome (returned value, or exception TYPE -- never its message)
  * policy.state after the call

What deliberately does NOT count:
  * how many times time_fn was consulted (a pure implementation detail; the clock only
    moves when the scenario says so, so extra reads cannot change any value)
  * exception messages (wording is style, not behaviour)

Scenarios are generated once from a seed and then replayed against every module, so
every comparison sees the identical input. rand_fn is a fresh seeded stream per module
run: an implementation that draws a different NUMBER of random values desynchronises the
stream, and that shows up as a trace difference -- correctly, because it is one.
"""

from __future__ import annotations

import importlib.util
import random
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# A call is aborted after this many fn invocations. Guards against an implementation
# whose retry loop never terminates; recorded as its own outcome rather than hanging.
MAX_FN_CALLS_PER_CALL = 200


class RetryableA(Exception):
    pass


class RetryableB(Exception):
    pass


class NotRetryable(Exception):
    pass


_SENTINEL = "ok-value"


@dataclass
class Scenario:
    """A deterministic script: one config plus a list of operations."""

    config: dict
    ops: list  # list of ("advance", dt) | ("call", kind, n) | ("state",)
    rand_seed: int


def _gen_scenario(rng: random.Random, idx: int) -> Scenario:
    base = round(rng.choice([0.0, 0.05, 0.1, 0.5, 1.0]), 3)
    cfg = {
        "max_attempts": rng.randint(1, 5),
        "base_delay": base,
        "max_delay": round(base + rng.choice([0.0, 0.2, 1.0, 4.0, 100.0]), 3),
        "failure_threshold": rng.randint(1, 4),
        "cooldown": round(rng.choice([0.0, 0.5, 2.0, 10.0]), 3),
    }
    kinds = [
        "ok",
        "always_retryable",
        "always_retryable_b",
        "fail_then_ok",
        "non_retryable",
        "reentrant_ok",
        "reentrant_fail",
    ]
    ops = []
    for _ in range(rng.randint(6, 16)):
        r = rng.random()
        if r < 0.25:
            ops.append(("advance", round(rng.choice([0.0, 0.1, 1.0, 3.0, 11.0]), 3)))
        elif r < 0.32:
            ops.append(("state",))
        else:
            kind = rng.choice(kinds)
            ops.append(("call", kind, rng.randint(1, 3)))
    return Scenario(config=cfg, ops=ops, rand_seed=1000 + idx)


def generate_scenarios(n: int, seed: int = 20260815) -> list[Scenario]:
    rng = random.Random(seed)
    return [_gen_scenario(rng, i) for i in range(n)]


def _load_module(path: Path):
    """Import a candidate retry_policy.py under a unique name (no cache collisions)."""
    name = f"_rp_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(name, None)
    return mod


class _Aborted(Exception):
    """Raised internally when a call exceeds MAX_FN_CALLS_PER_CALL."""


@dataclass
class _Harness:
    clock: float = 0.0
    sleeps: list = field(default_factory=list)
    fn_calls: int = 0
    rng: random.Random = None  # type: ignore[assignment]

    def time_fn(self):
        return self.clock

    def sleep_fn(self, d):
        # Round away last-bit noise from e.g. iterative doubling vs base*2**k. A 1e-9
        # difference is not a behaviour change anyone could observe.
        self.sleeps.append(round(float(d), 9))

    def rand_fn(self):
        return self.rng.random()


def run_scenario(module_path: Path, sc: Scenario) -> list:
    """Execute one scenario against one module. Returns the observable trace."""
    mod = _load_module(module_path)
    h = _Harness(rng=random.Random(sc.rand_seed))
    trace: list = []

    policy = mod.RetryPolicy(
        max_attempts=sc.config["max_attempts"],
        base_delay=sc.config["base_delay"],
        max_delay=sc.config["max_delay"],
        retryable=(RetryableA, RetryableB),
        failure_threshold=sc.config["failure_threshold"],
        cooldown=sc.config["cooldown"],
        time_fn=h.time_fn,
        sleep_fn=h.sleep_fn,
        rand_fn=h.rand_fn,
    )

    def make_fn(kind, n):
        counter = {"i": 0}

        def fn(*_a, **_k):
            h.fn_calls += 1
            if h.fn_calls > MAX_FN_CALLS_PER_CALL:
                raise _Aborted()
            counter["i"] += 1
            if kind == "ok":
                return _SENTINEL
            if kind == "always_retryable":
                raise RetryableA("boom")
            if kind == "always_retryable_b":
                raise RetryableB("boom")
            if kind == "non_retryable":
                raise NotRetryable("boom")
            if kind == "fail_then_ok":
                if counter["i"] <= n:
                    raise RetryableA("boom")
                return _SENTINEL
            if kind in ("reentrant_ok", "reentrant_fail"):
                # AC-16 territory: a nested call while a trial is in flight.
                try:
                    inner = policy.call(lambda: _SENTINEL)
                    inner_out = ("ret", inner)
                except _Aborted:
                    raise
                except BaseException as exc:  # noqa: BLE001 - type is the datum
                    inner_out = ("exc", type(exc).__name__)
                if kind == "reentrant_fail":
                    raise RetryableA(f"inner={inner_out}")
                return ("nested", inner_out)
            raise AssertionError(kind)

        return fn

    for op in sc.ops:
        if op[0] == "advance":
            h.clock = round(h.clock + op[1], 9)
            trace.append(("advance", h.clock))
            continue
        if op[0] == "state":
            trace.append(("state", _safe_state(policy)))
            continue

        _kind, kind, n = op
        h.sleeps = []
        h.fn_calls = 0
        try:
            res = policy.call(make_fn(kind, n))
            outcome = ("ret", repr(res))
        except _Aborted:
            outcome = ("aborted", f">{MAX_FN_CALLS_PER_CALL} fn calls")
        except BaseException as exc:  # noqa: BLE001 - type name is the datum
            outcome = ("exc", type(exc).__name__)
        trace.append(("call", kind, n, h.fn_calls, tuple(h.sleeps), outcome,
                      _safe_state(policy)))

    return trace


def _safe_state(policy):
    try:
        return str(policy.state)
    except BaseException as exc:  # noqa: BLE001
        return f"<state raised {type(exc).__name__}>"


_CALL_FIELDS = ("op", "kind", "n", "fn_calls", "sleeps", "outcome", "state_after")


def _signature(a_step, b_step) -> str:
    """Name WHAT differs, not just that something does.

    A raw scenario count conflates one semantic decision replayed across many generated
    configs with many independent changes. The signature collapses the former: two
    scenarios that differ in the same field of the same operation share a signature.
    """
    if a_step is None or b_step is None:
        return "trace-length"
    if a_step[0] != b_step[0]:
        return f"op-kind:{a_step[0]}->{b_step[0]}"
    if a_step[0] == "state":
        return f"state-property:{a_step[1]}->{b_step[1]}"
    if a_step[0] == "advance":
        return "clock"
    if a_step[0] == "harness-error" or b_step[0] == "harness-error":
        return "harness-error"
    fields = [_CALL_FIELDS[i] for i in range(min(len(a_step), len(b_step)))
              if a_step[i] != b_step[i]]
    detail = ""
    if "state_after" in fields:
        detail = f"({a_step[6]}->{b_step[6]})"
    elif "outcome" in fields:
        detail = f"({a_step[5][0]}:{a_step[5][1]}->{b_step[5][0]}:{b_step[5][1]})"
    return f"call[{a_step[1]}]:{'+'.join(fields)}{detail}"


def compare(baseline_path: Path, candidate_path: Path, scenarios: list[Scenario]) -> dict:
    """Compare candidate against baseline over every scenario.

    Returns per-scenario equality, the distinct divergence signatures (see _signature --
    this is the number that answers "how many separate behaviour changes"), and the first
    differing step of each mismatch so a divergence can be read rather than merely counted.
    """
    diffs = []
    signatures: dict[str, int] = {}
    n_equal = 0
    for i, sc in enumerate(scenarios):
        try:
            a = run_scenario(baseline_path, sc)
        except BaseException as exc:  # noqa: BLE001
            a = [("harness-error", type(exc).__name__, str(exc)[:200])]
        try:
            b = run_scenario(candidate_path, sc)
        except BaseException as exc:  # noqa: BLE001
            b = [("harness-error", type(exc).__name__, str(exc)[:200])]

        if a == b:
            n_equal += 1
            continue
        step = next((j for j in range(max(len(a), len(b)))
                     if j >= len(a) or j >= len(b) or a[j] != b[j]), 0)
        sig = _signature(a[step] if step < len(a) else None,
                         b[step] if step < len(b) else None)
        signatures[sig] = signatures.get(sig, 0) + 1
        diffs.append({
            "scenario": i,
            "config": sc.config,
            "step": step,
            "signature": sig,
            "baseline": repr(a[step]) if step < len(a) else "<trace ended>",
            "candidate": repr(b[step]) if step < len(b) else "<trace ended>",
        })
    total = len(scenarios)
    return {
        "total": total,
        "equal": n_equal,
        "diverged": total - n_equal,
        "divergence_rate": (total - n_equal) / total if total else 0.0,
        "signatures": dict(sorted(signatures.items(), key=lambda kv: -kv[1])),
        "n_signatures": len(signatures),
        "examples": diffs[:5],
    }


if __name__ == "__main__":
    import json

    scs = generate_scenarios(int(sys.argv[3]) if len(sys.argv) > 3 else 200)
    print(json.dumps(compare(Path(sys.argv[1]), Path(sys.argv[2]), scs),
                     indent=2, ensure_ascii=False))
