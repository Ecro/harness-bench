"""ADR-001b 경계 강제.

이 레포는 리뷰 실험만 담지 않는다. 두 번째 실험이 들어올 때 리뷰 전용 가정이 코어에
박혀 있으면 그때가 가장 바쁜 시점이고, 리팩터링하면 첫 실험의 재현성이 깨진다(ADR-008).

경계 규칙: **코어는 "어떻게 재는가" 를 알고 "무엇을 재는가" 는 모른다.**
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "harness_bench" / "core"

# 코드에 나타나면 안 되는 것 — 리뷰/특정 대상 고유 어휘.
# 주석·독스트링에서 왜 그런지 설명하는 것은 허용한다(그게 이 레포의 값어치다).
FORBIDDEN_IDENT = re.compile(
    r"\b(findings|violated_invariant|trigger_condition|production_consequence|"
    r"swing_capture|spoton|retry_policy|ttl_cache|fanout|precision|recall)\b", re.I)


def _py_files():
    return sorted(CORE.rglob("*.py"))


def test_core_does_not_import_experiments():
    for f in _py_files():
        tree = ast.parse(f.read_text(), str(f))
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.Import):
                mod = " ".join(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            if mod and "experiment" in mod:
                raise AssertionError(f"{f} imports experiments: {mod}")


def test_core_code_has_no_domain_vocabulary():
    """식별자·문자열 리터럴만 검사한다. 주석/독스트링은 면제 — 코어가 왜 그런
    모양인지 설명하려면 원 실험을 언급할 수밖에 없고, 그 설명이 규율의 전달 수단이다."""
    offenders = []
    for f in _py_files():
        tree = ast.parse(f.read_text(), str(f))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                d = ast.get_docstring(node, clean=False)
                if d:
                    docstrings.add(d)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and FORBIDDEN_IDENT.search(node.id):
                offenders.append(f"{f.name}:{node.lineno} name {node.id}")
            elif isinstance(node, ast.Attribute) and FORBIDDEN_IDENT.search(node.attr):
                offenders.append(f"{f.name}:{node.lineno} attr .{node.attr}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in docstrings:
                    continue
                if FORBIDDEN_IDENT.search(node.value):
                    offenders.append(f"{f.name}:{node.lineno} literal {node.value[:60]!r}")
    assert not offenders, "코어에 도메인 어휘가 코드로 존재:\n  " + "\n  ".join(offenders)


def test_no_absolute_home_paths():
    bad = [f"{f.name}:{i}" for f in _py_files()
           for i, line in enumerate(f.read_text().splitlines(), 1)
           if "/home/" in line and "Path.home()" not in line]
    assert not bad, "절대 홈 경로가 박혀 있음: " + ", ".join(bad)


def test_runner_has_no_retry_parameter():
    """ADR-006: 재시도 금지는 문서가 아니라 부재로 강제한다."""
    import inspect
    from harness_bench.core.runner.call import call
    params = list(inspect.signature(call).parameters)
    assert not any("retry" in p or "attempt" in p for p in params), params


def test_canary_requires_both_directions():
    from harness_bench.core.sandbox.canary import Canary, Leg
    import pytest
    for legs in ([Leg("a", "POS", lambda d: True)], [Leg("b", "NEG", lambda d: True)]):
        try:
            Canary("p", legs)
        except ValueError:
            continue
        raise AssertionError(f"단방향 카나리가 생성됨: {legs}")


def test_cluster_gate_blocks_quotation():
    from harness_bench.core.cluster.cluster import ClusterResult, UNQUOTABLE
    assert ClusterResult(True, None, 0.781, False, 12, {}).quotable() == UNQUOTABLE
    assert ClusterResult(True, None, 0.978, True, 19, {}).quotable() == 19
