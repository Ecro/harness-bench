"""Run a frozen acceptance suite against a candidate module, and VERIFY THE ORACLE ITSELF.

The source study's first experiment collapsed because it adopted an oracle without ever
asking what that oracle guaranteed. Tests went red, "red" was translated to "a bug was
introduced", and the headline result -- four independent runs breaking the same four tests --
turned out to be four tests pinning a state production cannot reach. The code was fine.

So this module ships `verify()` alongside `run()`, and no experiment should quote a number
until verify() has passed:

    reference passes            all ACs green on the known-good implementation
    single AC removal detected  deleting one guarantee is pinpointed, not diffuse
    import failure floors       an unimportable module scores 0, not "everything passed"
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_AC = re.compile(r"\bAC-(\d+)\b")


@dataclass
class OracleResult:
    passed: int
    total: int
    failed_ac: list[str]
    returncode: int
    stdout: str

    @property
    def green(self) -> bool:
        return self.returncode == 0


def run(source: str, suite: Path, module_name: str, timeout_s: int = 180) -> OracleResult:
    with tempfile.TemporaryDirectory(prefix="hb-oracle-") as td:
        d = Path(td)
        (d / module_name).write_text(source, encoding="utf-8")
        shutil.copy2(suite, d / "test_acceptance.py")
        try:
            p = subprocess.run(
                [sys.executable, "-m", "pytest", "test_acceptance.py", "-q", "--tb=line",
                 "-p", "no:cacheprovider"],
                cwd=d, capture_output=True, text=True, timeout=timeout_s)
            out, rc = p.stdout + p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            return OracleResult(0, 0, ["TIMEOUT"], -1, "TIMEOUT")

    m = re.search(r"(\d+) passed", out)
    passed = int(m.group(1)) if m else 0
    f = re.search(r"(\d+) failed", out)
    total = passed + (int(f.group(1)) if f else 0)
    failed = sorted({f"AC-{n}" for line in out.splitlines() if "FAILED" in line or "Error" in line
                     for n in _AC.findall(line)})
    return OracleResult(passed, total, failed, rc, out)


def verify(task, log=print) -> bool:
    """Three checks. All must pass before any number from this oracle is quotable."""
    ok = True
    src = task.reference.read_text() if task.reference else None

    if src is not None:
        r = run(src, task.suite, task.module_name)
        log(f"  reference passes          {r.passed}/{r.total}  {'PASS' if r.green else 'FAIL'}")
        ok &= r.green
    else:
        log("  reference passes          SKIP (task ships no reference by design)")

    r0 = run("raise ImportError('deliberately unimportable')", task.suite, task.module_name)
    floors = r0.passed == 0
    log(f"  import failure floors     {r0.passed} passed  {'PASS' if floors else 'FAIL'}")
    ok &= floors

    if src is not None:
        # Delete the LAST guard clause and check the suite notices. A suite that stays green
        # after a guarantee is removed is not measuring that guarantee.
        lines = src.splitlines()
        cut = next((i for i in range(len(lines) - 1, -1, -1)
                    if lines[i].strip().startswith("raise ")), None)
        if cut is None:
            log("  single-removal detected   SKIP (no guard clause found)")
        else:
            mutated = "\n".join(lines[:cut] + ["        pass"] + lines[cut + 1:])
            rm = run(mutated, task.suite, task.module_name)
            caught = not rm.green
            log(f"  single-removal detected   {rm.passed}/{rm.total} "
                f"{'PASS' if caught else 'FAIL — 스위트가 못 잡는다'}")
            ok &= caught
    return bool(ok)
