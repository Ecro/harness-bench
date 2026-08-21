"""Derive six category-reviewer prompts mechanically from review_structured.txt.

Writing six by hand makes vocabulary, emphasis and output rules drift between them, and that
drift is then read as the fan-out arm's effect. Exactly one block differs; every other byte
is identical.

Exactly two things change:
  1. the six-area list  ->  one of them
  2. the "List findings in order of importance" line is dropped (meaningless for one area)

What must NOT change, because each becomes a confound:
  * output schema, the 15-finding cap, and the permissive clause
    (dropping "If you find nothing worth reporting, return {"findings": []}" pressures a
     specialist into saying SOMETHING in its area, and then the fan-out arm's higher finding
     count is an artefact of the prompt rather than a measurement)
  * "Report a finding only if you can point at a specific line."
  * the cap is per call, so fan-out (6 calls) has six times the budget of a single call.
    That is intended, which is why the comparison baseline is not the single call but six
    identical structured calls.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "review_structured.txt"

# key -> (heading, body). Must match blocks 1-6 of review_structured.txt verbatim.
CATEGORIES = {
    "design": (
        "DESIGN -- is the internal design right?",
        """   The public contract above is FIXED and is not up for review: the constructor signature,
   the method names, and the documented behaviour must stay exactly as specified. Review the
   design BEHIND that contract -- the internal decomposition, the abstractions chosen, where
   responsibilities sit, whether the structure fits the problem, whether a fundamentally
   simpler internal design exists.""",
    ),
    "functionality": (
        "FUNCTIONALITY -- does it do what the contract says?",
        "   Edge cases, boundary conditions, error paths, state transitions, arithmetic, re-entrancy.",
    ),
    "complexity": (
        "COMPLEXITY -- is it more complex than it needs to be?",
        """   Over-engineering, speculative generality, logic a reader cannot hold in their head,
   control flow that could be flattened.""",
    ),
    "robustness": (
        "ROBUSTNESS -- how does it behave when things go wrong?",
        """   Unbounded resource use, exceptions escaping the public surface, state that can wedge
   permanently, silent failure.""",
    ),
    "naming": (
        "NAMING AND COMMENTS -- will the next person understand this?",
        """   Names that mislead, missing rationale for non-obvious decisions, comments that restate
   the code instead of explaining why.""",
    ),
    "style": (
        "CONSISTENCY AND STYLE -- is it idiomatic Python, consistent within the module?",
        "",
    ),
}

_AREAS = re.compile(
    r"Review it across these areas, in this order of importance:\n\n.*?\n\nReport a finding",
    re.S,
)


def build(key: str) -> str:
    src = SRC.read_text()
    title, body = CATEGORIES[key]
    block = f"You are reviewing ONE area only:\n\n{title}\n{body}\n\nReport a finding"
    out, n = _AREAS.subn(block.replace("\\", "\\\\"), src, count=1)
    if n != 1:
        raise SystemExit("review_structured.txt structure changed -- revisit the derivation")
    out = out.replace("List findings in order of importance, most important first.\n\n", "")
    return out


def main() -> None:
    for key in CATEGORIES:
        dst = HERE / f"review_cat_{key}.txt"
        dst.write_text(build(key))
        print(f"wrote {dst.name} ({len(dst.read_text().splitlines())} lines)")

    # Self-check that the derivation really changed only one place.
    base = SRC.read_text().splitlines()
    for key in CATEGORIES:
        gen = (HERE / f"review_cat_{key}.txt").read_text().splitlines()
        common = sum(1 for line in gen if line in base)
        print(f"  {key:14s} {common}/{len(gen)} lines identical to the source")


if __name__ == "__main__":
    main()
