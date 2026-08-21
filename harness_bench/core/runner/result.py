"""CallResult — what one isolated model invocation produced, including its cost.

Call count, wall-clock and response bytes all understate cost: the INPUT (subject plus
accumulated findings) grows every round, so real spend rises faster than any of those
proxies show. Cost-vs-quality is the whole point of this benchmark, so a missing usage
record is a DEGRADED result, never a silent zero.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None

    @property
    def complete(self) -> bool:
        return self.input_tokens is not None and self.output_tokens is not None

    @property
    def total_tokens(self) -> int | None:
        if not self.complete:
            return None
        return self.input_tokens + self.output_tokens


@dataclass
class CallResult:
    model: str            # adapter name, e.g. "claude"
    kind: str             # caller-defined label, e.g. "review" / "fix" / "canary"
    status: str           # "ok" | "failed" | "malformed"
    exit_code: int
    wall_s: float
    started_at: float
    raw: str
    parsed: dict | None
    reason: str | None = None
    model_version: str | None = None      # RESOLVED id, not the alias we asked for
    usage: Usage = field(default_factory=Usage)
    prompt_sha256: str | None = None
    degraded: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # An alias like "opus" can silently repoint to a different backend mid-batch, which is
        # invisible in results unless the resolved id is captured. Both are recorded; missing
        # either is a degradation, not an error.
        if not self.usage.complete:
            self.degraded.append("usage-missing")
        if self.model_version is None:
            self.degraded.append("model-version-unresolved")

    def to_meta(self) -> dict:
        d = asdict(self)
        d.pop("raw")
        return d
