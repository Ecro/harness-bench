"""Provenance stamped into every result: what code, what tasks, what version.

Comparing two results months apart is only meaningful if you can tell whether the difference
came from the model or from the benchmark. Prompt hashes were already recorded; the code
version and the task contents were not, which left the second half of that question open.

Task digests matter most. The acceptance suite is the oracle, and a suite that changed
between two runs invalidates the comparison silently -- the numbers still look comparable.
"""
from __future__ import annotations

import hashlib
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _package_version() -> str:
    try:
        return version("harness-bench")
    except PackageNotFoundError:
        return "unknown"


def _git_commit() -> str | None:
    """The working tree's commit, with a dirty marker. None outside a checkout."""
    root = Path(__file__).resolve().parents[2]
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if sha.returncode != 0:
            return None
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=5)
        return sha.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def digest_files(paths: list[Path]) -> str:
    """One digest over several files, order-independent and content-only.

    Sorted by name so the value does not depend on directory iteration order, and computed
    over bytes so it is unaffected by mtime or checkout order.
    """
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: x.name):
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def stamp(task_files: list[Path] | None = None) -> dict:
    return {
        "bench_version": _package_version(),
        "bench_commit": _git_commit(),
        "task_digest": digest_files(task_files) if task_files else None,
    }
