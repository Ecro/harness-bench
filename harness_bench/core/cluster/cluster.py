"""Provenance-blind clustering with an ARI stability gate.

N independent reviews describe the same defect in N different sentences. Nothing downstream --
pairwise Jaccard, per-defect detection frequency, recurrence -- means anything until those are
grouped. Core owns the MECHANISM; the grouping brief belongs to the experiment, because what
counts as "the same underlying thing" is domain knowledge.

Two properties the mechanism enforces:

* PROVENANCE-BLIND. The clusterer sees an opaque position, a location and the item text --
  never which model, run or arm produced it. Otherwise cluster boundaries could be drawn,
  however unconsciously, in a way that flatters one arm, and every comparison downstream
  inherits it.
* SHUFFLED PER RUN, SEEDED. Identical input order would correlate the runs through
  presentation rather than through the underlying grouping, and the ARI gate would then
  measure prompt determinism instead of clustering stability -- passing for the wrong reason.

THE GATE. Below `ari_threshold` the result is not a number, it is `UNQUOTABLE`. The source
study had a real case: codex's control arm clustered at ARI 0.781, and its unique-defect count
was therefore never cited anywhere. A gate that returns a number "with a caveat" gets cited
without the caveat.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from ..config import CONFIG
from ..runner.call import call
from .partition import is_valid_partition, mean_pairwise_ari, medoid

UNQUOTABLE = "UNQUOTABLE"
DEFAULT_ARI_THRESHOLD = 0.90


@dataclass
class ClusterResult:
    ok: bool
    reason: str | None
    mean_ari: float | None
    gate_pass: bool
    n_groups: int | None
    labeling: dict[str, str] | None
    labelings: list[dict[str, str]] = field(default_factory=list)

    def quotable(self, what: str = "n_groups"):
        """Downstream analyses call this instead of reading the field directly, so a failed
        gate cannot leak into a table as a bare number."""
        if not (self.ok and self.gate_pass):
            return UNQUOTABLE
        return getattr(self, what)


# ITEM CONTRACT — the only thing core knows about the things being clustered.
#
#   {"uid": str,            opaque, stable, experiment-owned
#    "text": str,           what the clusterer reads
#    "location": str|None}  optional locator shown alongside (line, path, symbol...)
#
# Deliberately NOT the review schema. Core used to parse `findings[].violated_invariant`,
# which meant the clustering mechanism could not be reused by any experiment that did not
# produce review findings. Building items is the experiment's job.


def render(items: list[dict], order: list[int]) -> str:
    """Provenance-blind rendering. `order` maps presentation position -> item index."""
    out = []
    for pos, i in enumerate(order):
        it = items[i]
        loc = f" ({it['location']})" if it.get("location") else ""
        out.append(f"[{pos}]{loc}\n    {it['text']}")
    return "\n\n".join(out)


def one_clustering(items, seed, scratch, instruction, adapter="claude", **kw):
    """Return {uid: group_label} or None if the response was unusable.

    `adapter` is a parameter so the CLUSTERER itself can be cross-validated: three runs of one
    model agreeing proves consistency, not correctness -- they can share a systematic bias and
    agree perfectly while being wrong. Agreement across two models cannot come from a shared
    prompt-following habit, so it is much stronger evidence about the instrument.

    `instruction` is REQUIRED and owned by the experiment. What counts as "the same underlying
    thing" is domain knowledge; a default here would silently impose one domain's notion on
    every other.
    """
    order = list(range(len(items)))
    random.Random(seed).shuffle(order)

    r = call(adapter, "cluster", render(items, order) + "\n" + instruction, scratch, **kw)
    if r.status != "ok" or not r.parsed:
        return None

    labeling: dict[str, str] = {}
    for gi, g in enumerate(r.parsed.get("groups") or []):
        for pos in g.get("members", []):
            if not isinstance(pos, int) or not (0 <= pos < len(order)):
                continue
            uid = items[order[pos]]["uid"]
            # First assignment wins; a duplicated id is a clusterer error, and silently
            # letting the last one win would hide it. Validity is asserted below.
            labeling.setdefault(uid, f"g{gi}:{g.get('label','')[:40]}")
    return labeling


def cluster_set(items, tag, instruction, *, n_runs: int = 3, adapter: str = "claude",
                ari_threshold: float = DEFAULT_ARI_THRESHOLD, scratch_root: Path | None = None,
                log=print, **kw) -> ClusterResult:
    root = scratch_root or (CONFIG.scratch_root / "cluster")
    labelings, uids = [], [it["uid"] for it in items]
    for k in range(n_runs):
        lab = one_clustering(items, 1000 + k, root / f"{tag}-{k}", instruction, adapter, **kw)
        if lab is None:
            log(f"  clustering run {k}: FAILED (recorded, not retried)")
            continue
        valid = is_valid_partition(lab, uids)
        log(f"  clustering run {k}: {len(set(lab.values()))} groups, "
            f"valid={valid} ({len(lab)}/{len(uids)} items)")
        labelings.append(lab)

    if len(labelings) < 2:
        return ClusterResult(False, "fewer than 2 usable clusterings", None, False, None, None,
                             labelings)

    ari = mean_pairwise_ari(labelings)
    best, _ = medoid(labelings)
    gate = ari >= ari_threshold
    if not gate:
        log(f"  ARI {ari:.3f} < {ari_threshold} -- results are {UNQUOTABLE}")
    return ClusterResult(True, None, ari, gate, len(set(labelings[best].values())),
                         labelings[best], labelings)
