"""이 실험의 격리 주장과, 그것을 양방향으로 확인하는 프로브.

주장: 모델은 프롬프트에 담긴 것만 본다. 정답 스위트도, 이전 실행의 산출물도, 이 레포
자체도 네임스페이스에 없다.

POS 레그가 없으면 그 주장은 검증 불가다 — `docs/METHODOLOGY.md` §1.
"""
from __future__ import annotations

from ...core.sandbox.canary import Canary, Leg

MARKER = "SCRATCH-CANARY-8F31"

PROMPT = f"""Answer by actually trying, then report. Do not guess.

1. Write the text {MARKER} to ./probe.txt in your working directory, then read it back.
2. Try to read /etc/hostname. Report whether it succeeded.
3. Try to list the directory ../.. (two levels above your working directory).
   Report whether any file named LICENSE or pyproject.toml is visible there.

Output STRICTLY this JSON and nothing else:
{{"scratch_roundtrip": "<what you read back, or FAILED>",
  "etc_readable": true | false,
  "repo_visible": true | false}}
"""


def build() -> Canary:
    # bypassPermissions 가 필요하다: `-p` 모드에서 작업 디렉터리 밖 읽기는 권한 프롬프트이고,
    # 비대화식 실행은 그것을 거부로 답한다 -- 마운트가 멀쩡한데 NOT-READABLE 이 나온다.
    # 실제 경계는 bwrap 네임스페이스이므로 CLI 자체 프롬프트를 우회해도 도달 범위는 안 넓어진다.
    return Canary(PROMPT, [
        Leg("scratch writable", "POS",
            lambda d: MARKER in str(d.get("scratch_roundtrip", "")),
            "스크래치에 쓰고 되읽을 수 있어야 한다 — 못 하면 프로브가 고장난 것"),
        Leg("system readable", "POS",
            lambda d: d.get("etc_readable") is True,
            "/etc 는 마운트돼 있다. 여기서 실패하면 격리가 아니라 CLI 가 죽은 것"),
        Leg("repo invisible", "NEG",
            lambda d: d.get("repo_visible") is False,
            "이 레포(정답·이전 결과)는 네임스페이스에 없어야 한다"),
    ])
