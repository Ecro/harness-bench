"""Model profile and the prescription derived from it (PLAN ADR-001c).

A score tells you which model won. A PROFILE tells you how to run the one you have.

The most useful output is not a number but an operating recipe that falls out of measured
traits -- one model that grows code every round and never converges needs a hard round cap
and cannot use a churn stop rule, while one that shrinks code and settles early can run
longer.

Core owns the SCHEMA and the RENDERER. The trait->knob rules are owned by the experiment,
because the mapping is domain knowledge and the next experiment will bring different knobs.

EVIDENCE GRADES ARE MANDATORY. Some mappings are judgement rather than measurement, and a
prescription that hides the difference is worse than no prescription -- it launders an
opinion into a recommendation. A rule with no grade does not render.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable

GRADES = {
    "***": "reproduced across models",
    "**": "measured once",
    "*": "judgement, not measured",
}


@dataclass
class Trait:
    key: str
    value: float | int | str | None
    unit: str = ""
    note: str = ""
    degraded: bool = False          # measurement itself was incomplete


@dataclass
class Rule:
    """A trait condition -> a harness knob setting."""
    knob: str
    when: Callable[[dict], bool]
    then: str
    grade: str
    because: str = ""

    def __post_init__(self) -> None:
        if self.grade not in GRADES:
            raise ValueError(
                f"rule for knob {self.knob!r} has grade {self.grade!r}; "
                f"must be one of {sorted(GRADES)}. An ungraded rule launders judgement "
                "into a recommendation and will not render."
            )


@dataclass
class Profile:
    model: str
    model_version: str | None
    experiment: str
    traits: dict[str, Trait] = field(default_factory=dict)
    exploratory: bool = False
    prereg_sha256: str | None = None
    tools_blockable: bool | None = None
    bench_version: str | None = None
    bench_commit: str | None = None
    task_digest: str | None = None
    total_calls: int = 0
    total_cost_usd: float | None = None
    total_tokens: int | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def values(self) -> dict:
        return {k: t.value for k, t in self.traits.items()}

    @property
    def caveats(self) -> list[str]:
        out = []
        if self.exploratory:
            out.append("EXPLORATORY -- predictions were not frozen before the run")
        if self.tools_blockable is False:
            out.append("TOOLS-UNBLOCKABLE -- this adapter cannot disable tools; placing it "
                       "in the same table as one that can is itself a confound")
        if self.total_cost_usd is None:
            out.append("COST-UNKNOWN -- usage was not reported (unknown, not zero)")
        if self.bench_commit and self.bench_commit.endswith("-dirty"):
            out.append("DIRTY-TREE -- measured against uncommitted changes; not reproducible "
                       "from any published commit")
        if self.task_digest is None:
            out.append("TASK-DIGEST-MISSING -- cannot prove the tasks were unchanged")
        out += [f"DEGRADED:{k}" for k, t in self.traits.items() if t.degraded]
        return out

    def prescribe(self, rules: list[Rule]) -> list[dict]:
        v = self.values
        out = []
        for r in rules:
            try:
                fires = r.when(v)
            except (KeyError, TypeError):
                continue                      # trait not measured -> no advice, not a guess
            if fires:
                out.append({"knob": r.knob, "do": r.then, "grade": r.grade,
                            "because": r.because})
        return out

    def render(self, rules: list[Rule]) -> str:
        lines = [f"# {self.model}" + (f"  ({self.model_version})" if self.model_version else ""),
                 f"  experiment: {self.experiment}   calls: {self.total_calls}"
                 + (f"   cost: ${self.total_cost_usd:.2f}" if self.total_cost_usd else "")]
        if self.caveats:
            lines += [""] + [f"  ⚠ {c}" for c in self.caveats]
        lines += ["", "## Measured traits"]
        for k, t in self.traits.items():
            lines.append(f"  {k:<28} {t.value}{(' ' + t.unit) if t.unit else ''}"
                         + (f"   {t.note}" if t.note else ""))
        pres = self.prescribe(rules)
        lines += ["", "## Operating prescription"]
        if not pres:
            lines.append("  (none -- no measured trait fired a rule)")
        for p in pres:
            lines.append(f"  [{p['grade']:<3}] {p['knob']:<24} {p['do']}")
            if p["because"]:
                lines.append(f"        ← {p['because']}")
        lines += ["", "  grades: " + " | ".join(f"{g} {d}" for g, d in GRADES.items())]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)
