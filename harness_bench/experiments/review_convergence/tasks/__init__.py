"""Tier-1 tasks: pure stdlib, pytest oracle, no toolchain.

A task is (SPEC, frozen acceptance suite, module name). The suite IS the oracle, and the
contract IS the truth — which is why this experiment needs no human adjudication and can
therefore be re-run against a new model with nobody in the loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Task:
    slug: str
    module_name: str          # what the frozen suite imports
    n_ac: int
    has_reference: bool
    note: str = ""

    @property
    def dir(self) -> Path:
        return HERE / self.slug

    @property
    def spec(self) -> Path:
        return self.dir / "SPEC.md"

    @property
    def suite(self) -> Path:
        return self.dir / "test_acceptance.py"

    @property
    def reference(self) -> Path | None:
        p = self.dir / "reference.py"
        return p if p.exists() else None


TASKS = {
    "retry_policy": Task(
        "retry_policy", "retry_policy.py", n_ac=19, has_reference=True,
        note="dense contract; exponential backoff + full jitter + circuit breaker"),
    "ttl_cache": Task(
        "ttl_cache", "ttl_cache.py", n_ac=8, has_reference=False,
        note="SPARSE contract, deliberately. No reference: the point is what models choose "
             "where the contract is silent."),
}
