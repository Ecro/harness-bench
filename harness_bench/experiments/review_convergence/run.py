"""이 실험의 측정 계획 — bench run 이 실제로 하는 일.

tier-1 프로파일 한 벌의 비용:

    변동폭   n_spread 콜        같은 v0 를 반복 리뷰. 코드가 안 바뀌므로 순수 관측
    루프     n_rounds × 2 콜    리뷰 → 수정 → 오라클. 궤적·churn·거절률·준수
    나머지   0 콜               LOC/AC/malformed 는 위 산출물에서 파생

기본값(5, 5)이면 **15콜**이다. 새 모델 하나를 표에 얹는 값이 그 정도여야 한다 —
더 비싸면 아무도 새 모델을 안 얹는다.

★ 재시도는 없다. 실패한 라운드는 거기서 멈추고 그때까지의 관측만 쓴다.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from ...core.config import CONFIG
from ...core.ledger.profile import Profile, Trait
from ...core.runner.adapters import REGISTRY
from ...core.runner.call import call, save
from . import oracle
from .tasks import TASKS

HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"


def _compose_review(spec: str, module: str) -> str:
    return (f"```\n{spec}\n```\n\n```python\n{module}\n```\n"
            + (PROMPTS / "review_structured.txt").read_text())


def _compose_fix(spec: str, module: str, findings: list) -> str:
    return (f"```\n{spec}\n```\n\n```python\n{module}\n```\n"
            + (PROMPTS / "fix_instruction.txt").read_text()
            + json.dumps(findings, indent=2, ensure_ascii=False) + "\n")


def _churn(a: str, b: str) -> int:
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), n=0))
    return sum(1 for l in d if l[:1] in "+-" and l[:3] not in ("+++", "---"))


def measure(adapter_name: str, task_slug: str = "retry_policy", *,
            n_spread: int = 5, n_rounds: int = 5, out_dir: Path | None = None,
            log=print) -> Profile:
    task = TASKS[task_slug]
    if not task.reference:
        raise ValueError(f"{task_slug} ships no reference; spread needs a known-good v0")
    if not oracle.verify(task, log=lambda m: log("  " + m.strip())):
        raise RuntimeError(f"oracle for {task_slug} failed verification — no number from it "
                           "is quotable (docs/TASKS.md)")

    adapter = REGISTRY[adapter_name]()
    spec, v0 = task.spec.read_text(), task.reference.read_text()
    root = (out_dir or CONFIG.scratch_root / "run") / adapter_name / task_slug
    calls: list = []

    # --- 변동폭: 코드가 안 바뀌므로 관측이 곧 변동폭이다 --------------------
    counts = []
    for i in range(n_spread):
        r = call(adapter, "review", _compose_review(spec, v0), root / f"spread{i}")
        calls.append(r)
        save(r, root / f"spread{i}", "review")
        n = len((r.parsed or {}).get("findings", [])) if r.status == "ok" else None
        log(f"  spread {i+1}/{n_spread}: {r.status} findings={n}")
        if n is not None:
            counts.append(n)

    # --- 루프 -------------------------------------------------------------
    module, churns, round_counts, dec_total, dec_rej, ac_ok = v0, [], [], 0, 0, True
    for rnd in range(1, n_rounds + 1):
        d = root / f"round{rnd}"
        rv = call(adapter, "review", _compose_review(spec, module), d)
        calls.append(rv); save(rv, d, "review")
        if rv.status != "ok":
            log(f"  round {rnd}: review {rv.status} — 중단 (재시도 없음)"); break
        findings = (rv.parsed or {}).get("findings", [])
        round_counts.append(len(findings))
        if not findings:
            log(f"  round {rnd}: 지적 0 — 종료"); break

        fx = call(adapter, "fix", _compose_fix(spec, module, findings), d)
        calls.append(fx); save(fx, d, "fix")
        new = (fx.parsed or {}).get("code")
        if fx.status != "ok" or not new:
            log(f"  round {rnd}: fix {fx.status} — 중단 (재시도 없음)"); break

        dec = (fx.parsed or {}).get("decisions", []) or []
        dec_total += len(dec)
        dec_rej += sum(1 for x in dec if x.get("action") == "rejected")
        churns.append(_churn(module, new))
        o = oracle.run(new, task.suite, task.module_name)
        ac_ok &= o.green
        log(f"  round {rnd}: {len(findings)}건 → churn {churns[-1]}, "
            f"{len(new.splitlines())}줄, {o.passed}/{o.total} {'GREEN' if o.green else 'RED'}")
        module = new

    # --- 파생 (LLM 콜 0) ---------------------------------------------------
    ok = [c for c in calls if c.status == "ok"]
    cost = [c.usage.cost_usd for c in ok if c.usage.cost_usd is not None]
    toks = [c.usage.total_tokens for c in ok if c.usage.total_tokens is not None]

    def T(k, v, unit="", note=""):
        return Trait(k, v, unit, note, degraded=v is None)

    traits = {
        "spread": T("spread", (max(counts) - min(counts)) if len(counts) > 1 else None,
                    note=f"n={len(counts)} {counts}"),
        "loop_decay": T("loop_decay",
                        round((round_counts[-1] - round_counts[0]) / (len(round_counts) - 1), 2)
                        if len(round_counts) > 1 else None, note=str(round_counts)),
        "churn_dries": T("churn_dries",
                         (churns[-1] < churns[0] / 2) if len(churns) > 1 else None,
                         note=str(churns)),
        "rejection_rate": T("rejection_rate",
                            round(dec_rej / dec_total, 3) if dec_total else None,
                            note=f"{dec_rej}/{dec_total}"),
        "malformed_rate": T("malformed_rate",
                            round(sum(c.status == "malformed" for c in calls) / len(calls), 3)
                            if calls else None),
        "ac_held": T("ac_held", ac_ok if churns else None),
        "loc_direction": T("loc_direction",
                           round(len(module.splitlines()) / len(v0.splitlines()), 3)
                           if churns else None, "×"),
        "tools_blockable": T("tools_blockable", adapter.tools_blockable),
        # tier-2 전용 — tier-1 이 원리적으로 못 잰다. 추정으로 채우지 않는다.
        "finds_per_call": T("finds_per_call", None, note="tier-2 전용 (판정된 결함 집합 필요)"),
        "verbosity_shift": T("verbosity_shift", None, note="tier-2 전용 (리포 접근 대비 필요)"),
    }
    return Profile(
        adapter_name, next((c.model_version for c in ok if c.model_version), None),
        f"review_convergence/{task_slug}", traits,
        exploratory=True,          # 이 측정 계획에는 아직 사전등록이 없다
        tools_blockable=adapter.tools_blockable,
        total_calls=len(calls),
        total_cost_usd=round(sum(cost), 4) if cost else None,
        total_tokens=sum(toks) if toks else None,
    )
