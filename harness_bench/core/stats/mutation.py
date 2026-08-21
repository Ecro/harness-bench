"""Mutation score of each implementation against the FROZEN acceptance suite.

The suite never changes -- it was written from SPEC-retry-policy.md before any
implementation existed and was never revised. So the mutation score here answers a
question the pass/fail oracle cannot:

    of the behaviour this code has, how much is actually pinned down by the contract?

Read it as ISO/IEC 25010 Testability. A high score means almost every way of perturbing
this code is caught. A falling score across review rounds means the reviews are adding
code whose behaviour nothing checks -- lines that could be silently wrong forever. That
is the exact failure the acceptance-pass-rate metric is blind to, because added-and-
untested code passes every test by construction.

Operators (standard, conservative -- each produces a syntactically valid module):
  * comparison swap        <  <= > >= == !=
  * arithmetic swap        +  -  *  /  //  %  **
  * boolean operator swap  and <-> or
  * numeric constant       n -> n + 1, and 0 -> 1
  * boolean constant       True <-> False
  * `not` removal

A mutant is KILLED when the frozen suite fails on it, SURVIVED when the suite still
passes. Surviving mutants include genuine equivalent mutants, which no automated method
can separate out; the score is therefore a lower bound and is only ever compared
BETWEEN implementations measured the same way, never read as an absolute.
"""

from __future__ import annotations

import ast
import concurrent.futures
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Defaults only. Both are overridable per call: core must not know what an experiment calls
# its subject or where its frozen suite lives (ADR-001b).
SUITE: Path | None = None
MODULE_NAME = "subject.py"

_CMP = [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq]
_ARITH = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]


class _Collector(ast.NodeVisitor):
    """Enumerate mutation sites as (node_id, kind, replacement) without editing."""

    def __init__(self):
        self.sites: list[tuple[int, str, object]] = []

    def visit_Compare(self, node):
        for i, op in enumerate(node.ops):
            for alt in _CMP:
                if not isinstance(op, alt):
                    self.sites.append((id(op), "cmp", alt))
        self.generic_visit(node)

    def visit_BinOp(self, node):
        for alt in _ARITH:
            if not isinstance(node.op, alt):
                self.sites.append((id(node.op), "arith", alt))
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        alt = ast.Or if isinstance(node.op, ast.And) else ast.And
        self.sites.append((id(node.op), "bool", alt))
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            self.sites.append((id(node), "drop-not", None))
        self.generic_visit(node)

    def visit_Constant(self, node):
        v = node.value
        if isinstance(v, bool):
            self.sites.append((id(node), "const", not v))
        elif isinstance(v, int):
            self.sites.append((id(node), "const", v + 1))
            if v == 0:
                self.sites.append((id(node), "const", 1))
        elif isinstance(v, float):
            self.sites.append((id(node), "const", v + 1.0))


class _Applier(ast.NodeTransformer):
    """Apply exactly ONE mutation, identified by the node's identity in a fresh parse."""

    def __init__(self, target_index: int, sites: list):
        self.target = sites[target_index]
        self.applied = False

    def _hit(self, node) -> bool:
        return id(node) == self.target[0]

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            if self._hit(op):
                node.ops[i] = self.target[2]()
                self.applied = True
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if self._hit(node.op):
            node.op = self.target[2]()
            self.applied = True
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self._hit(node.op):
            node.op = self.target[2]()
            self.applied = True
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if self.target[1] == "drop-not" and self._hit(node):
            self.applied = True
            return node.operand
        return node

    def visit_Constant(self, node):
        if self.target[1] == "const" and self._hit(node):
            self.applied = True
            return ast.copy_location(ast.Constant(value=self.target[2]), node)
        return node


def _sites_and_tree(source: str):
    tree = ast.parse(source)
    col = _Collector()
    col.visit(tree)
    return tree, col.sites


def mutants(source: str):
    """Yield (index, kind, mutated_source). Re-parses per mutant so ids stay valid."""
    _tree, sites = _sites_and_tree(source)
    for i in range(len(sites)):
        tree, s = _sites_and_tree(source)  # fresh parse -> fresh ids, same order
        app = _Applier(i, s)
        new = app.visit(tree)
        if not app.applied:
            continue  # site not reachable by the transformer (defensive)
        ast.fix_missing_locations(new)
        try:
            code = ast.unparse(new)
        except Exception:  # pragma: no cover - unparse should not fail
            continue
        yield i, s[i][1], code


def _run_suite(source: str, timeout_s: int = 60, *, suite: Path | None = None,
               module_name: str | None = None) -> bool:
    """True when the frozen suite PASSES on this source (i.e. the mutant SURVIVED).

    `module_name` is the filename the suite imports. It is a PARAMETER because core must not
    know what any experiment calls its subject -- a hardcoded name silently makes this engine
    single-purpose (ADR-001b).
    """
    suite = suite or SUITE
    if suite is None:
        raise ValueError(
            "no frozen suite given. Core does not own one -- the acceptance suite IS the "
            "experiment's oracle. Pass suite=<path> (ADR-001b)."
        )
    module_name = module_name or MODULE_NAME
    with tempfile.TemporaryDirectory(prefix="mutscore-") as td:
        d = Path(td)
        (d / module_name).write_text(source, encoding="utf-8")
        shutil.copy2(suite, d / "test_acceptance.py")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "test_acceptance.py",
                 "-x", "-q", "--tb=no", "-p", "no:cacheprovider"],
                cwd=d, capture_output=True, text=True, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return False  # hang == killed (the suite would never go green)
        return proc.returncode == 0


def score_file(path: Path, workers: int = 8, *, suite: Path | None = None,
               module_name: str | None = None) -> dict:
    source = path.read_text(encoding="utf-8")
    muts = list(mutants(source))
    if not muts:
        return {"total": 0, "killed": 0, "survived": 0, "score": None, "by_kind": {}}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        survived_flags = list(ex.map(
            lambda m: _run_suite(m[2], suite=suite, module_name=module_name), muts))

    by_kind: dict[str, dict] = {}
    killed = 0
    for (_i, kind, _src), survived in zip(muts, survived_flags):
        slot = by_kind.setdefault(kind, {"total": 0, "killed": 0})
        slot["total"] += 1
        if not survived:
            killed += 1
            slot["killed"] += 1
    return {
        "total": len(muts),
        "killed": killed,
        "survived": len(muts) - killed,
        "score": killed / len(muts),
        "by_kind": by_kind,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(score_file(Path(sys.argv[1])), indent=2, ensure_ascii=False))
