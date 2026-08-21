"""Two-way canary. The single most load-bearing piece of discipline in this benchmark.

"The model could not read the answer key" PROVES NOTHING. A broken probe returns the same
answer as perfect isolation: no tools attached, prompt not delivered, CLI died, permission
prompt auto-denied. All of them look like success.

So every isolation claim needs BOTH directions in the SAME invocation:

    POS   something that MUST be reachable, and is
    NEG   something that MUST NOT be reachable, and isn't

If POS fails, that is not isolation working. That is the probe being broken, and any result
collected under it is void.

In the source study this caught a real one: codex returned NOT-READABLE for both, which
without the POS control would have been recorded as "codex does not use repo access even
when given it" -- a MODEL property. It was a scratch-directory property. The same class of
mistake was made three times; each time only the POS leg distinguished them.

Therefore: `require_pass()` raises. A driver cannot proceed on a failed canary, and there
is no flag to override it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..runner.call import call
from ..runner.result import CallResult


class CanaryFailure(RuntimeError):
    """Raised when a canary does not pass in both directions. Not catchable by policy:
    a driver that swallows this is collecting void data."""


@dataclass
class Leg:
    name: str
    direction: str                 # "POS" | "NEG"
    check: object                  # Callable[[dict], bool]
    note: str = ""


@dataclass
class Canary:
    prompt: str
    legs: list[Leg]
    result: CallResult | None = field(default=None, init=False)
    verdicts: dict[str, bool] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if not any(l.direction == "POS" for l in self.legs):
            raise ValueError(
                "a canary with no POS leg cannot distinguish isolation from a broken probe"
            )
        if not any(l.direction == "NEG" for l in self.legs):
            raise ValueError("a canary with no NEG leg asserts nothing about isolation")

    def run(self, adapter, scratch: Path, **kw) -> "Canary":
        self.result = call(adapter, "canary", self.prompt, scratch, **kw)
        parsed = self.result.parsed or {}
        self.verdicts = {l.name: bool(l.check(parsed)) for l in self.legs}
        return self

    @property
    def passed(self) -> bool:
        return bool(self.verdicts) and all(self.verdicts.values())

    def report(self) -> str:
        rows = [f"  {l.direction} {l.name:<28} "
                f"{'PASS' if self.verdicts.get(l.name) else 'FAIL'}"
                + (f"   {l.note}" if l.note else "")
                for l in self.legs]
        return "\n".join(rows)

    def require_pass(self) -> "Canary":
        if not self.passed:
            failed = [n for n, v in self.verdicts.items() if not v]
            pos_failed = [l.name for l in self.legs
                          if l.direction == "POS" and not self.verdicts.get(l.name)]
            hint = ("\nA FAILED POS LEG IS A BROKEN PROBE, NOT ISOLATION. "
                    "Any data collected now is void." if pos_failed else "")
            raise CanaryFailure(
                f"canary failed: {', '.join(failed)}\n{self.report()}{hint}"
            )
        return self
