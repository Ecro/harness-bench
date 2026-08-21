"""Cognitive Complexity (Campbell, SonarSource 2018) for Python, from the AST.

Chosen over cyclomatic complexity deliberately. Cyclomatic complexity correlates with
raw line count at r ~= 0.85-0.87 -- it adds almost nothing on top of "how big is it",
which we already measure. Cognitive Complexity was designed for the other question:
how hard is this to READ. It has been validated against measured comprehension time and
subjective understandability (arXiv:2007.12520), which is exactly the ISO/IEC 25010
"Analysability" sub-characteristic we want and cannot get from size alone.

The three rules, as published:

  B1 INCREMENT   for each break in the linear flow: if / elif / else, for, while,
                 except, finally, ternary, boolean-operator sequence, comprehension-if,
                 `with` is NOT counted, recursion cycle.
  B2 NESTING     each such structure also raises the nesting level for what it contains.
  B3 PENALTY     an incrementing structure additionally costs +nesting_level.

Deliberate divergences from the paper, all in the direction of counting LESS:
  * `elif` costs +1 flat with no nesting penalty (the paper's whole point: an if/elif
    chain reads as one decision, not as nested ifs).
  * `else` / `else:` on a loop costs +1 flat, no nesting penalty.
  * A sequence of the same boolean operator costs +1 for the sequence, not per operand;
    a switch of operator inside one expression costs another +1.
  * Recursion: only direct self-recursion is detected. Mutual recursion is not.

Validated in test_cogcomplex.py against the worked examples from the paper.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


class _Visitor(ast.NodeVisitor):
    def __init__(self, func_name: str | None = None):
        self.score = 0
        self.nesting = 0
        self.func_name = func_name

    # -- helpers ---------------------------------------------------------
    def _inc(self, nesting_penalty: bool = True):
        self.score += 1 + (self.nesting if nesting_penalty else 0)

    def _nested(self, body):
        self.nesting += 1
        for stmt in body:
            self.visit(stmt)
        self.nesting -= 1

    def _flat(self, body):
        for stmt in body:
            self.visit(stmt)

    # -- structures ------------------------------------------------------
    def visit_If(self, node: ast.If):
        self._inc()
        self.visit(node.test)
        self._nested(node.body)
        orelse = node.orelse
        while orelse:
            # `elif` is parsed as a lone If inside orelse: +1 flat, and its own body
            # sits at the SAME nesting level as the chain, not one deeper.
            if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                el = orelse[0]
                self.score += 1
                self.visit(el.test)
                self._nested(el.body)
                orelse = el.orelse
            else:
                self.score += 1  # plain else, no nesting penalty
                self._nested(orelse)
                orelse = []

    def _loop(self, node):
        self._inc()
        self._nested(node.body)
        if node.orelse:
            self.score += 1
            self._nested(node.orelse)

    visit_For = _loop
    visit_AsyncFor = _loop
    visit_While = _loop

    def visit_Try(self, node: ast.Try):
        self._flat(node.body)
        for handler in node.handlers:
            self._inc()
            self._nested(handler.body)
        if node.orelse:
            self.score += 1
            self._nested(node.orelse)
        if node.finalbody:
            self.score += 1
            self._nested(node.finalbody)

    visit_TryStar = visit_Try

    def visit_With(self, node):
        # `with` does not break the linear flow -- no increment, no nesting.
        self._flat(node.body)

    visit_AsyncWith = visit_With

    def visit_IfExp(self, node: ast.IfExp):
        self._inc()
        self.visit(node.test)
        self.nesting += 1
        self.visit(node.body)
        self.visit(node.orelse)
        self.nesting -= 1

    def visit_BoolOp(self, node: ast.BoolOp):
        # One increment per RUN of the same operator, flat (no nesting penalty).
        self.score += 1
        for value in node.values:
            if isinstance(value, ast.BoolOp) and type(value.op) is not type(node.op):
                self.visit(value)  # operator switch -> its own +1
            elif isinstance(value, ast.BoolOp):
                for v in value.values:  # same operator: flatten, no extra cost
                    self.generic_visit_expr(v)
            else:
                self.generic_visit_expr(value)

    def generic_visit_expr(self, node):
        if isinstance(node, ast.BoolOp):
            self.visit_BoolOp(node)
        else:
            self.generic_visit(node)

    def _comprehension(self, node):
        for gen in node.generators:
            for _cond in gen.ifs:
                self._inc()
        self.generic_visit(node)

    visit_ListComp = _comprehension
    visit_SetComp = _comprehension
    visit_DictComp = _comprehension
    visit_GeneratorExp = _comprehension

    def visit_Call(self, node: ast.Call):
        # Direct recursion is a flow break the reader has to unwind.
        if (self.func_name and isinstance(node.func, ast.Name)
                and node.func.id == self.func_name):
            self.score += 1
        self.generic_visit(node)

    # A nested def/lambda raises nesting for its body but is not itself an increment.
    def _nested_func(self, node):
        self._nested(node.body)

    visit_FunctionDef = _nested_func
    visit_AsyncFunctionDef = _nested_func

    def visit_Lambda(self, node: ast.Lambda):
        self.nesting += 1
        self.visit(node.body)
        self.nesting -= 1


def function_complexity(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    v = _Visitor(func_name=fn.name)
    for stmt in fn.body:
        v.visit(stmt)
    return v.score


def analyse_source(source: str) -> dict:
    """Per-function scores plus the file total, for one module's source text."""
    tree = ast.parse(source)
    per_fn: dict[str, int] = {}

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                per_fn[name] = function_complexity(child)
                walk(child, prefix=f"{name}.")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix=f"{prefix}{child.name}.")
            else:
                walk(child, prefix=prefix)

    walk(tree)
    scores = list(per_fn.values())
    return {
        "per_function": per_fn,
        "total": sum(scores),
        "max": max(scores) if scores else 0,
        "n_functions": len(scores),
        "mean": (sum(scores) / len(scores)) if scores else 0.0,
    }


def analyse_file(path: Path) -> dict:
    return analyse_source(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import json

    print(json.dumps(analyse_file(Path(sys.argv[1])), indent=2, ensure_ascii=False))
