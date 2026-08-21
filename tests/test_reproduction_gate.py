"""ADR-008 — 이식이 조건을 조용히 바꾸지 않았는지 검증한다.

포팅에서 가장 위험한 실패는 크래시가 아니라 **조용한 드리프트**다. 코드는 돌고, 숫자는
그럴듯하고, 아무도 이전 값과 대조하지 않는다. 그래서 원 연구의 **저장된 산출물**을 새
코드로 다시 계산해 같은 값이 나오는지 본다.

**LLM 을 한 번도 부르지 않는다.** 응답은 이미 값을 치렀고 픽스처로 들어와 있다.
재현 게이트가 모델을 다시 부른다면 그건 재현이 아니라 새 실험이다.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parents[1] / "harness_bench/experiments/review_convergence/fixtures"


def test_freespace_denominator_reproduces():
    """자유 공간 분모: 120 지점 중 계약이 104(87%)를 고정, 자유 영역은 1개.

    이 숫자가 초고의 4부 전체를 지탱한다 -- "AI 가 움직인 자리와 계약이 비워둔 자리가
    1:1 로 일치한다" 는 문장의 분모다.
    """
    v0 = json.loads((FIX / "freespace_results.json").read_text())["v0"]
    assert v0["mutants"] == 120
    assert v0["survivors"] == 16
    assert v0["mutants"] - v0["survivors"] == 104
    assert v0["observably_equivalent"] == 9
    assert v0["free_points"] == 3 and v0["free_regions"] == 1
    assert v0["suite_hole_points"] == 4 and v0["suite_hole_regions"] == 1
    # 9 관측불가 + 4 스위트구멍 + 3 진짜자유 = 16 생존. 합이 안 맞으면 분류가 깨진 것이다.
    assert v0["observably_equivalent"] + v0["suite_hole_points"] + v0["free_points"] == 16


def _pools_from_cluster():
    """저장된 3자 풀에서 (arm -> run -> 찾은 진짜결함 집합) 을 만든다."""
    blob = json.loads((FIX / "cluster_e7_codex.json").read_text())
    lab = blob["result"]["labeling"]
    runs: dict[str, dict[str, set]] = {}
    for uid, g in lab.items():
        tag, rest = uid.split("-", 1)
        run = rest.split("#")[0]
        runs.setdefault(tag, {}).setdefault(run, set()).add(g)
    # D 라벨은 대조군 출현 빈도 내림차순으로 복원한다. 원 연구가 판정에 쓴 순서와 같아야 한다.
    ctrl = runs["ctrl"]
    counts: dict[str, int] = {}
    for r, gs in ctrl.items():
        for g in gs:
            counts[g] = counts.get(g, 0) + 1
    ranked = sorted(counts, key=lambda g: (-counts[g], str(g)))
    freqs = [counts[g] for g in ranked]
    assert freqs == [9, 8, 7, 7, 7, 6, 5, 3, 3, 2, 1, 1, 1, 1], freqs
    false_idx = {2, 3, 4, 7}
    truth = {g for i, g in enumerate(ranked, 1) if i not in false_idx}
    pools = {}
    for tag in ("e7", "cdx"):
        pools[tag] = {r: (gs & truth) for r, gs in runs[tag].items()}
    return pools, ranked, false_idx, runs


def test_budget_curve_reproduces():
    """예산표 k=1..6. 초고의 "혼합 3콜 = 단일 6콜" 이 여기서 나온다."""
    from harness_bench.core.stats.coverage import budget_curve
    pools, *_ = _pools_from_cluster()
    rows = {r["k"]: r for r in budget_curve(pools, [1, 2, 3, 4, 6])}
    exp = {  # (claude, codex, mixed)
        1: (1.40, 2.70, 2.70), 2: (2.09, 3.07, 3.18),
        3: (2.54, 3.27, 3.57), 4: (2.90, 3.40, 3.90), 6: (3.43, 3.60, 4.43),
    }
    for k, (cl, cd, mx) in exp.items():
        assert rows[k]["e7"] == pytest.approx(cl, abs=0.005), (k, "claude", rows[k]["e7"])
        assert rows[k]["cdx"] == pytest.approx(cd, abs=0.005), (k, "codex", rows[k]["cdx"])
        assert rows[k]["mixed"] == pytest.approx(mx, abs=0.005), (k, "mixed", rows[k]["mixed"])
    # 헤드라인: 혼합 3콜이 단일(claude) 6콜을 이긴다
    assert rows[3]["mixed"] > rows[6]["e7"]


def test_false_positive_suppression_reproduces():
    """오탐 4건을 두 모델이 똑같이 버렸다 -- 이 연구 최대의 교차모델 재현."""
    _, ranked, false_idx, runs = _pools_from_cluster()
    for tag in ("e7", "cdx"):
        seen = set().union(*runs[tag].values())
        reproduced = [i for i, g in enumerate(ranked, 1) if i in false_idx and g in seen]
        assert reproduced == [], (tag, reproduced)


def test_ari_gate_value_reproduces():
    blob = json.loads((FIX / "cluster_e7_codex.json").read_text())["result"]
    assert blob["mean_ari"] == pytest.approx(0.978, abs=0.001)
    assert blob["n_groups"] == 19
