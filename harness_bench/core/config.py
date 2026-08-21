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


# Scratch must NOT live under a temporary directory.
#
# Some CLIs materialise sandbox helper binaries under their home directory at run time and
# refuse to do so beneath /tmp:
#
#     WARNING: Refusing to create helper binaries under temporary dir "/tmp"
#
# The CLI then proceeds anyway and fails opaquely on its first shell command
# (`execvp <helper>: No such file or directory`). From the outside this is indistinguishable
# from "the model does not use the capability" -- a configuration property misreadable as a
# model property. Refused up front instead. See docs/DESIGN.md 3, "environment before
# attribution".
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
