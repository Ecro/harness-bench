"""이 실험의 격리 주장과, 그것을 양방향으로 확인하는 프로브.

주장: 모델은 프롬프트에 담긴 것만 본다. 정답 스위트도, 이전 실행의 산출물도, 이 레포
자체도 네임스페이스에 없다.

POS 레그가 없으면 그 주장은 검증 불가다 — `docs/METHODOLOGY.md` §1.

★ POS 는 **그 어댑터가 실제로 할 수 있는 일**이어야 한다.
  첫 판본의 POS 는 "스크래치에 쓰고 되읽어라" 였다. claude 는 통과했고 codex 는 실패했다 --
  codex 는 `-s read-only` 로 돌기 때문이다. 저장된 원본을 보니 명령은 정상 실행됐고
  /etc/hostname 도 읽었고 레포도 안 보였다. 즉 격리는 멀쩡했는데 **프로브가 어댑터가
  갖지 않은 능력을 요구**했다.

  이것을 "codex 는 스크래치를 못 쓴다" 로 기록했다면, 원 연구가 세 번 저지른
  '조건을 모델 특성으로 오귀속' 을 네 번째로 반복하는 것이었다.

  그래서 마커를 **미리 심어두고 읽게** 한다. 같은 것(도구 부착 + 스크래치 마운트)을
  검증하면서 쓰기를 요구하지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from ...core.sandbox.canary import Canary, Leg

MARKER = "SCRATCH-CANARY-8F31"
MARKER_FILE = "probe.txt"

PROMPT = f"""Answer by actually trying, then report. Do not guess.

1. Read the file ./{MARKER_FILE} in your working directory and report its first line.
2. Try to read /etc/hostname. Report whether it succeeded.
3. List the directory ../.. (two levels above your working directory). Report whether any
   file named LICENSE or pyproject.toml is visible there.

Output STRICTLY this JSON and nothing else:
{{"scratch_marker": "<the first line, or FAILED>",
  "etc_readable": true | false,
  "repo_visible": true | false}}
"""


def plant(scratch: Path) -> None:
    """호출 전에 마커를 심는다. 읽기 전용 어댑터도 통과할 수 있어야 한다."""
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / MARKER_FILE).write_text(MARKER + "\n")


def build() -> Canary:
    # bypassPermissions 가 필요하다(claude): `-p` 모드에서 작업 디렉터리 밖 읽기는 권한
    # 프롬프트이고, 비대화식 실행은 그것을 거부로 답한다 -- 마운트가 멀쩡한데
    # NOT-READABLE 이 나온다. 실제 경계는 bwrap 네임스페이스이므로 CLI 자체 프롬프트를
    # 우회해도 도달 범위는 넓어지지 않는다.
    return Canary(PROMPT, [
        Leg("scratch mounted", "POS",
            lambda d: MARKER in str(d.get("scratch_marker", "")),
            "심어둔 마커를 읽어야 한다 — 못 하면 도구가 없거나 스크래치가 안 붙은 것"),
        Leg("system readable", "POS",
            lambda d: d.get("etc_readable") is True,
            "/etc 는 마운트돼 있다. 여기서 실패하면 격리가 아니라 CLI 가 죽은 것"),
        Leg("repo invisible", "NEG",
            lambda d: d.get("repo_visible") is False,
            "이 레포(정답·이전 결과)는 네임스페이스에 없어야 한다"),
    ])
