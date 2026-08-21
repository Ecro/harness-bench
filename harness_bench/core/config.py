"""Runtime configuration. No absolute paths are baked into the package.

The original study hardcoded one operator's home in 15 files, which made every result
unreproducible on any other machine. Everything machine-specific lives here and is
overridable by environment variable.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(name: str, default: Path | None) -> Path | None:
    v = os.environ.get(name)
    return Path(v).expanduser() if v else default


def _which(*names: str) -> Path | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return Path(p)
    return None


# Scratch must NOT live under /tmp.
#
# codex does not ship its sandbox helper; it MATERIALISES it under CODEX_HOME at run time and
# refuses to do so under a temporary directory:
#
#     WARNING: Refusing to create helper binaries under temporary dir "/tmp"
#
# It then proceeds anyway and dies on the first shell command with
# `bwrap: execvp codex-linux-sandbox: No such file or directory`. The source study read that
# as "codex cannot be given repo access" and recorded it as a MODEL property for three weeks.
# It was a scratch-location property. See docs/METHODOLOGY.md.
DEFAULT_SCRATCH_ROOT = Path.home() / ".cache/harness-bench"


@dataclass(frozen=True)
class Config:
    scratch_root: Path = field(default_factory=lambda: _env_path("HB_SCRATCH_ROOT", DEFAULT_SCRATCH_ROOT))
    claude_bin: Path | None = field(default_factory=lambda: _env_path("HB_CLAUDE_BIN", None) or _which("claude"))
    node_bin: Path | None = field(default_factory=lambda: _env_path("HB_NODE_BIN", None) or _which("node"))
    codex_js: Path | None = field(default_factory=lambda: _env_path("HB_CODEX_JS", None))
    bwrap_bin: Path | None = field(default_factory=lambda: _env_path("HB_BWRAP_BIN", None) or _which("bwrap"))

    def require(self, *fields: str) -> None:
        """Fail loudly at setup time rather than mid-batch."""
        missing = [f for f in fields if getattr(self, f) is None]
        if missing:
            raise RuntimeError(
                "missing configuration: " + ", ".join(missing)
                + "\nSet HB_" + "/HB_".join(f.upper() for f in missing) + " or put the binary on PATH."
            )
        if str(self.scratch_root).startswith(("/tmp", "/var/tmp")):
            raise RuntimeError(
                f"scratch_root is under a temp dir ({self.scratch_root}). "
                "codex refuses to materialise its sandbox helper there and then fails "
                "opaquely. Set HB_SCRATCH_ROOT to a non-temp path."
            )


CONFIG = Config()
