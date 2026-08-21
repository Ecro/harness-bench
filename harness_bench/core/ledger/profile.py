"""Model profile and the prescription derived from it (PLAN ADR-001c).

A score tells you which model won. A PROFILE tells you how to run the one you have.

The source study's most useful output was never a number, it was a pair of operating
recipes that fell straight out of measured traits:

    claude   terse under repo access (-51%) · churn never dries · 1.40 real finds/call
             -> needs fan-out · round cap mandatory · churn gate unusable
    codex    verbose under repo access (+37%) · dry by round 3 · 2.70 real finds/call
             -> single pass suffices · cap less critical · churn gate works

Core owns the SCHEMA and the RENDERER. The trait->knob rules are owned by the experiment,
because the mapping is domain knowledge and the next experiment will bring different knobs.

EVIDENCE GRADES ARE MANDATORY. Some of those mappings are the study's judgement, not its
measurement, and a prescription that hides the difference is worse than no prescription --
it launders an opinion into a recommendation. A rule with no grade does not render.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable

GRADES = {
    "***": "두 모델 이상에서 재현",
    "**": "단일 모델/단일 실험에서 측정",
    "*": "판단 — 측정되지 않음",
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
            out.append("EXPLORATORY — 예측을 사전 동결하지 않았다")
        if self.tools_blockable is False:
            out.append("TOOLS-UNBLOCKABLE — 이 어댑터는 도구를 끌 수 없다. "
                       "차단 가능한 모델과 같은 표에 놓는 것 자체가 교란이다")
        if self.total_cost_usd is None:
            out.append("COST-UNKNOWN — 비용을 못 얻었다 (0 이 아니라 미상)")
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
        lines += ["", "## 측정된 특성"]
        for k, t in self.traits.items():
            lines.append(f"  {k:<28} {t.value}{(' ' + t.unit) if t.unit else ''}"
                         + (f"   {t.note}" if t.note else ""))
        pres = self.prescribe(rules)
        lines += ["", "## 운용 처방"]
        if not pres:
            lines.append("  (해당 없음 — 측정된 특성이 어떤 규칙도 발화시키지 않았다)")
        for p in pres:
            lines.append(f"  [{p['grade']:<3}] {p['knob']:<24} {p['do']}")
            if p["because"]:
                lines.append(f"        ← {p['because']}")
        lines += ["", "  근거 등급: " + " · ".join(f"{g} {d}" for g, d in GRADES.items())]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)
