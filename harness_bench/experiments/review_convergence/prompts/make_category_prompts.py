"""6개 카테고리 전문 리뷰어 프롬프트를 review_structured.txt 에서 기계적으로 파생시킨다.

손으로 6개를 쓰면 어휘·강조·출력 규칙이 미묘하게 달라지고, 그 차이가 그대로 팬아웃 팔의
효과로 오해된다. bare↔structured 를 단일 변수로 만들 때와 같은 규율이다: 범위 블록 하나만
다르고 나머지 바이트는 동일해야 한다.

바뀌는 것은 정확히 둘이다.
  1. 여섯 영역 목록  ->  그 중 하나만
  2. "List findings in order of importance" 한 줄 삭제 (영역이 하나면 순서가 의미 없음)

바꾸지 않는 것 — 전부 교란변수가 되기 때문:
  * 출력 스키마, 최대 15건 상한, 빈 배열 허용 문구
    (특히 "If you find nothing worth reporting, return {"findings": []}" 를 지운다면
     전문 리뷰어에게 "네 영역에서 뭐라도 말해라"라는 압력을 주는 것이고, 그러면 팬아웃 팔의
     지적 수 증가는 측정이 아니라 프롬프트가 만든 것이 된다.)
  * "Report a finding only if you can point at a specific line."
  * 상한 15는 호출당 값이라 팬아웃(6콜)이 단일(1콜)보다 6배의 예산을 갖는다. 이것은
    의도된 것이며, 그래서 비교의 기준선은 단일 콜이 아니라 "동일 structured 6콜"(C팔)이다.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "review_structured.txt"

# key -> (제목줄, 본문). review_structured.txt 의 1~6번 블록과 글자 그대로 같아야 한다.
CATEGORIES = {
    "design": (
        "DESIGN -- is the internal design right?",
        """   The public contract above is FIXED and is not up for review: the constructor signature,
   the method names, and the documented behaviour must stay exactly as specified. Review the
   design BEHIND that contract -- the internal decomposition, the abstractions chosen, where
   responsibilities sit, whether the structure fits the problem, whether a fundamentally
   simpler internal design exists.""",
    ),
    "functionality": (
        "FUNCTIONALITY -- does it do what the contract says?",
        "   Edge cases, boundary conditions, error paths, state transitions, arithmetic, re-entrancy.",
    ),
    "complexity": (
        "COMPLEXITY -- is it more complex than it needs to be?",
        """   Over-engineering, speculative generality, logic a reader cannot hold in their head,
   control flow that could be flattened.""",
    ),
    "robustness": (
        "ROBUSTNESS -- how does it behave when things go wrong?",
        """   Unbounded resource use, exceptions escaping the public surface, state that can wedge
   permanently, silent failure.""",
    ),
    "naming": (
        "NAMING AND COMMENTS -- will the next person understand this?",
        """   Names that mislead, missing rationale for non-obvious decisions, comments that restate
   the code instead of explaining why.""",
    ),
    "style": (
        "CONSISTENCY AND STYLE -- is it idiomatic Python, consistent within the module?",
        "",
    ),
}

_AREAS = re.compile(
    r"Review it across these areas, in this order of importance:\n\n.*?\n\nReport a finding",
    re.S,
)


def build(key: str) -> str:
    src = SRC.read_text()
    title, body = CATEGORIES[key]
    block = f"You are reviewing ONE area only:\n\n{title}\n{body}\n\nReport a finding"
    out, n = _AREAS.subn(block.replace("\\", "\\\\"), src, count=1)
    if n != 1:
        raise SystemExit("review_structured.txt 구조가 바뀌었다 — 파생 규칙을 다시 봐라")
    out = out.replace("List findings in order of importance, most important first.\n\n", "")
    return out


def main() -> None:
    for key in CATEGORIES:
        dst = HERE / f"review_cat_{key}.txt"
        dst.write_text(build(key))
        print(f"wrote {dst.name} ({len(dst.read_text().splitlines())} lines)")

    # 파생이 실제로 한 곳만 바꿨는지 스스로 확인한다.
    base = SRC.read_text().splitlines()
    for key in CATEGORIES:
        gen = (HERE / f"review_cat_{key}.txt").read_text().splitlines()
        common = sum(1 for line in gen if line in base)
        print(f"  {key:14s} {common}/{len(gen)} 줄이 원본에 그대로 존재")


if __name__ == "__main__":
    main()
