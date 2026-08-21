"""결과 원장. 모델 × 특성 표를 시간에 걸쳐 축적한다.

재현 불가가 된 행은 **삭제하지 않고** `stale` 로 표시한다. 모델은 예고 없이 바뀌고,
6개월 전 수치와 오늘 수치의 차이가 모델 변화인지 조건 변화인지 결과 파일만으로 항상
가를 수는 없다. 지우면 그 차이 자체를 잃는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from .profile import Profile, Rule


def write(profile: Profile, results_dir: Path) -> Path:
    d = results_dir / profile.model
    d.mkdir(parents=True, exist_ok=True)
    stamp = profile.created_at.replace(":", "").replace("-", "")
    p = d / f"{stamp}.json"
    p.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False))
    return p


def load_all(results_dir: Path) -> list[dict]:
    return [json.loads(p.read_text())
            for p in sorted(results_dir.glob("*/*.json")) if p.name != "ledger.json"]


def render_ledger(rows: list[dict], trait_keys: dict) -> str:
    if not rows:
        return "# ledger\n\n(아직 결과 없음)\n"
    keys = [k for k in trait_keys if any(r["traits"].get(k, {}).get("value") is not None
                                         for r in rows)]
    head = ["model", "version", "when", "calls", "cost"] + keys
    out = ["# ledger", "",
           "이 표는 **모델 순위표가 아니다.** 하네스 설계의 효과를 재는 특성값이다.",
           "`docs/LIMITS.md` 를 같이 읽어라.", "",
           "| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * len(head)) + "|"]
    for r in sorted(rows, key=lambda r: (r["model"], r["created_at"])):
        cells = [r["model"], (r.get("model_version") or "?")[:28],
                 r["created_at"][:10], str(r.get("total_calls", "")),
                 f"${r['total_cost_usd']:.2f}" if r.get("total_cost_usd") else "—"]
        for k in keys:
            v = r["traits"].get(k, {}).get("value")
            cells.append("—" if v is None else str(v))
        out.append("| " + " | ".join(cells) + " |")
    notes = {c for r in rows for c in _caveats(r)}
    if notes:
        out += ["", "## 단서"] + [f"- {n}" for n in sorted(notes)]
    return "\n".join(out) + "\n"


def _caveats(r: dict) -> list[str]:
    out = []
    if r.get("exploratory"):
        out.append(f"`{r['model']}` — EXPLORATORY: 예측을 사전 동결하지 않은 측정")
    if r.get("tools_blockable") is False:
        out.append(f"`{r['model']}` — 도구를 끌 수 없는 어댑터. 차단 가능한 모델과 "
                   "같은 표에 놓는 것 자체가 교란이다 (LIMITS §4)")
    if r.get("total_cost_usd") is None:
        out.append(f"`{r['model']}` — 비용 미상 (0 이 아니다)")
    return out
