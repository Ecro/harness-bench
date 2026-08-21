"""Result ledger: a model-by-trait table accumulated over time.

Rows that can no longer be reproduced are marked `stale`, never deleted. Models change
without notice, and the difference between a figure from six months ago and today cannot
always be attributed to model change versus condition change from the result file alone.
Deleting the row deletes the difference itself.
"""
from __future__ import annotations

import json
from pathlib import Path

from .profile import Profile, Rule


def write(profile: Profile, results_dir: Path) -> Path:
    d = results_dir / profile.model
    d.mkdir(parents=True, exist_ok=True)
    stamp = profile.created_at.replace(":", "").replace("-", "")
    p = d / f"{stamp}.json"
    p.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False))
    return p


def load_all(results_dir: Path) -> list[dict]:
    return [json.loads(p.read_text())
            for p in sorted(results_dir.glob("*/*.json")) if p.name != "ledger.json"]


def render_ledger(rows: list[dict], trait_keys: dict) -> str:
    if not rows:
        return "# ledger\n\n(no results yet)\n"
    keys = [k for k in trait_keys if any(r["traits"].get(k, {}).get("value") is not None
                                         for r in rows)]
    head = ["model", "version", "when", "calls", "cost"] + keys
    out = ["# ledger", "",
           "**This is not a model leaderboard.** These are trait values measuring the "
           "effect of harness design.", "Read it with `docs/LIMITS.md`.", "",
           "| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * len(head)) + "|"]
    for r in sorted(rows, key=lambda r: (r["model"], r["created_at"])):
        mark = " ~~(superseded)~~" if r.get("superseded_by") else ""
        cells = [r["model"] + mark, (r.get("model_version") or "?")[:28],
                 r["created_at"][:10], str(r.get("total_calls", "")),
                 f"${r['total_cost_usd']:.2f}" if r.get("total_cost_usd") else "—"]
        for k in keys:
            v = r["traits"].get(k, {}).get("value")
            cells.append("—" if v is None else str(v))
        out.append("| " + " | ".join(cells) + " |")
    notes = {c for r in rows for c in _caveats(r)}
    if notes:
        out += ["", "## Caveats"] + [f"- {n}" for n in sorted(notes)]
    return "\n".join(out) + "\n"


def _caveats(r: dict) -> list[str]:
    out = []
    if r.get("superseded_by"):
        out.append(f"`{r['model']}` -- superseded by {r['superseded_by']}. "
                   f"Kept, not deleted: {r.get('note', '')}")
    if r.get("exploratory"):
        out.append(f"`{r['model']}` -- EXPLORATORY: predictions not frozen before the run")
    if r.get("tools_blockable") is False:
        out.append(f"`{r['model']}` -- tools cannot be disabled for this adapter; sharing a "
                   "table with one that can is itself a confound (LIMITS 4)")
    if r.get("total_cost_usd") is None:
        out.append(f"`{r['model']}` -- cost unknown (not zero)")
    return out
