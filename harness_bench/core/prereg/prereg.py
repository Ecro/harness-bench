"""Pre-registration. Freeze predictions BEFORE data, or wear the exploratory brand.

A prediction is only informative if it could have come out the other way, and only if that
was settled before the data arrived. Post-hoc, any observed direction acquires a reason it
was expected all along; that is what unregistered analysis produces.

Two consequences are enforced here rather than requested:

  * a prediction with no falsification condition is a description, and is rejected at
    construction;
  * a frozen file is hashed, so editing it after the fact fails to load.

A run without a prereg is not forbidden, it is BRANDED. `exploratory: true` travels in the
result and into the ledger, and no amount of downstream formatting removes it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import re


@dataclass
class Prediction:
    id: str
    statement: str
    falsified_when: str        # what result would refute it. Required: a prediction that
                               # cannot be refuted is a description.
    outcome: str | None = None      # "PASS" | "FAIL" | None (not yet evaluated)
    observed: str | None = None


@dataclass
class Prereg:
    slug: str
    question: str
    design: str
    predictions: list[Prediction] = field(default_factory=list)
    frozen_at: str | None = None
    sha256: str | None = None
    exploratory: bool = False

    def __post_init__(self) -> None:
        for p in self.predictions:
            if not p.falsified_when.strip():
                raise ValueError(
                    f"prediction {p.id} has no falsification condition; "
                    "an unfalsifiable prediction is a description, not a prediction"
                )

    # ---- freezing -------------------------------------------------------
    def freeze(self, path: Path) -> "Prereg":
        """Write the prereg and stamp it. Outcomes MUST still be empty."""
        if any(p.outcome for p in self.predictions):
            raise ValueError("cannot freeze a prereg that already carries outcomes")
        self.frozen_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        body = json.dumps(
            {"slug": self.slug, "question": self.question, "design": self.design,
             "predictions": [{"id": p.id, "statement": p.statement,
                              "falsified_when": p.falsified_when} for p in self.predictions],
             "frozen_at": self.frozen_at},
            indent=2, ensure_ascii=False, sort_keys=True)
        self.sha256 = hashlib.sha256(body.encode()).hexdigest()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + "\n")
        (path.parent / f"{path.stem}.sha256").write_text(self.sha256 + "\n")
        return self

    @classmethod
    def load(cls, path: Path) -> "Prereg":
        d = json.loads(path.read_text())
        pr = cls(d["slug"], d["question"], d["design"],
                 [Prediction(**p) for p in d["predictions"]], d.get("frozen_at"))
        expect = (path.parent / f"{path.stem}.sha256")
        body = json.dumps({k: d[k] for k in ("slug", "question", "design", "predictions",
                                             "frozen_at")},
                          indent=2, ensure_ascii=False, sort_keys=True)
        pr.sha256 = hashlib.sha256(body.encode()).hexdigest()
        if expect.exists() and expect.read_text().strip() != pr.sha256:
            raise ValueError(
                f"prereg {path} does not match its recorded hash -- it was edited after "
                "freezing. Predictions edited after seeing data are not predictions."
            )
        return pr

    @classmethod
    def exploratory_run(cls, slug: str, why: str) -> "Prereg":
        """No predictions. Everything downstream carries exploratory: true."""
        pr = cls(slug, why, "unregistered", [], exploratory=True)
        return pr

    # ---- scoring --------------------------------------------------------
    def score(self, outcomes: dict[str, tuple[str, str]]) -> "Prereg":
        """outcomes: {prediction_id: (PASS|FAIL, observed)}"""
        for p in self.predictions:
            if p.id in outcomes:
                p.outcome, p.observed = outcomes[p.id]
        return self

    @property
    def summary(self) -> dict:
        scored = [p for p in self.predictions if p.outcome]
        return {
            "slug": self.slug,
            "exploratory": self.exploratory,
            "n_predictions": len(self.predictions),
            "n_scored": len(scored),
            "n_failed": sum(1 for p in scored if p.outcome == "FAIL"),
            "failed_ids": [p.id for p in scored if p.outcome == "FAIL"],
            "sha256": self.sha256,
        }

    def to_dict(self) -> dict:
        return asdict(self)
