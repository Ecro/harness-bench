#!/usr/bin/env bash
# 시크릿 스캐너 — pre-commit 훅과 CI 가 **같은 파일**을 쓴다.
#
# 왜 스크립트로 뺐는가: 패턴을 훅과 CI 에 각각 적으면 둘이 갈라진다. 그리고 실제로
# 갈라지기 전에 다른 문제가 먼저 터졌다 — CI yml 안에 적힌 패턴 리터럴을 훅이
# "토큰" 으로 잡아 커밋을 거부했다. 정직한 오탐이다.
#
# ★ 이 파일은 자기 자신을 내용 스캔에서 제외한다. 스캐너가 자기 패턴으로 자기를
#   스캔하면 항상 걸린다. 제외 대상은 이 파일 하나뿐이고, 이름으로 고정돼 있다.
set -uo pipefail

MODE="${1:-staged}"          # staged | history
SELF="tools/secret_scan.sh"

PATH_RE='credential|auth\.json|\.env$|\.pem$|id_rsa'
# 패턴을 조각으로 만든다 -- 이 파일 밖 어디에도 토큰 모양 리터럴이 남지 않도록.
TOK_RE="$(printf 's''k-[A-Za-z0-9_-]{20,}|"a''ccess_token"|"r''efresh_token"|BEGIN [A-Z ]*PRIVATE KEY|g''hp_[A-Za-z0-9]{30,}')"

fail() { echo "REFUSED: $1" >&2; shift; [ $# -gt 0 ] && printf '  %s\n' "$@" >&2; exit 1; }

# 스캐너가 고장나도 "찾은 게 없다" 는 똑같이 나온다 (docs/METHODOLOGY.md §1).
# 심어둔 가짜 토큰을 못 잡으면 아래 통과는 의미가 없다.
probe="$(mktemp)"; printf 's''k-abcdefghijklmnopqrstuvwxyz01234\n' > "$probe"
grep -qE "$TOK_RE" "$probe" || { rm -f "$probe"; fail "scanner self-test FAILED — 심어둔 토큰을 못 잡았다"; }
rm -f "$probe"

if [ "$MODE" = "history" ]; then
  bad="$(git rev-list --all --objects | awk '{print $2}' | grep -iE "$PATH_RE" || true)"
  [ -z "$bad" ] || fail "이력에 시크릿 모양 경로" $bad
  bad="$(git log --all -p --no-color -- . ":(exclude)$SELF" | grep -nE "$TOK_RE" | head -5 || true)"
  [ -z "$bad" ] || fail "이력에 토큰 모양 내용" $bad
else
  staged="$(git diff --cached --name-only)"
  bad="$(printf '%s\n' "$staged" | grep -iE "$PATH_RE" || true)"
  [ -z "$bad" ] || fail "시크릿 모양 파일이 스테이징됨" $bad
  bad="$(git diff --cached -U0 -- . ":(exclude)$SELF" | grep -nE "$TOK_RE" | head -5 || true)"
  [ -z "$bad" ] || fail "diff 안에 토큰 모양 문자열" $bad
fi
echo "secret scan ($MODE): PASS  [self-test PASS]"
