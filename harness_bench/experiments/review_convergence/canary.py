"""This experiment's isolation claim, and the two-way probe that checks it.

Claim: the model sees only what the prompt carries. Not the acceptance suite, not artefacts
from earlier runs, not this repository.

Without a POS leg that claim is unverifiable -- see `docs/DESIGN.md` 3.

A POS leg must also be something THE ADAPTER CAN ACTUALLY DO. An earlier version asked the
model to write a marker and read it back; that passes on a read-write adapter and fails on a
read-only one, while isolation is identical in both cases. Reported as a model difference it
would be wrong. So the marker is planted before the call and only read: the same two things
are verified -- tools attached, scratch mounted -- without requiring a write.
"""
from __future__ import annotations

from pathlib import Path

from ...core.sandbox.canary import Canary, Leg

MARKER = "SCRATCH-CANARY-8F31"
MARKER_FILE = "probe.txt"

PROMPT = f"""Answer by actually trying, then report. Do not guess.

1. Read the file ./{MARKER_FILE} in your working directory and report its first line.
2. Try to read /etc/hostname. Report whether it succeeded.
3. List the directory ../.. (two levels above your working directory). Report whether any
   file named LICENSE or pyproject.toml is visible there.

Output STRICTLY this JSON and nothing else:
{{"scratch_marker": "<the first line, or FAILED>",
  "etc_readable": true | false,
  "repo_visible": true | false}}
"""


def plant(scratch: Path) -> None:
    """Plant the marker before the call so a read-only adapter can pass too."""
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / MARKER_FILE).write_text(MARKER + "\n")


def build() -> Canary:
    # Some CLIs treat a read outside the working directory as a permission prompt in
    # non-interactive mode and auto-answer it with a denial -- producing NOT-READABLE while
    # the mount is perfectly fine. The real boundary is the namespace, so bypassing the CLI's
    # own prompt does not widen what is reachable.
    return Canary(PROMPT, [
        Leg("scratch mounted", "POS",
            lambda d: MARKER in str(d.get("scratch_marker", "")),
            "must read the planted marker; failure means no tools or no scratch mount"),
        Leg("system readable", "POS",
            lambda d: d.get("etc_readable") is True,
            "/etc is mounted; failing here means the CLI died, not that isolation worked"),
        Leg("repo invisible", "NEG",
            lambda d: d.get("repo_visible") is False,
            "this repository (answer key, prior results) must not be in the namespace"),
    ])
