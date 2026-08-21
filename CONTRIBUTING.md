# 기여

## 새 모델을 얹으려면

`harness_bench/core/runner/adapters.py` 에 `Adapter` 하나. **계약 다섯 개**:

```
argv()        헤드리스 단발 호출. REPL 도 resume 도 아니다
STDIN         프롬프트는 stdin. argv 금지 — 큰 입력은 잘리거나 ARG_MAX 를 넘고,
              조용히 손상된 입력은 여기서 최악의 실패다
parse()       CLI 봉투에서 최종 텍스트 · 해석된 모델 id · 토큰을 꺼낸다
usage()       입출력 토큰. 못 얻으면 degraded 이지 0 이 아니다
tools         도구를 끌 수 있는가. 없으면 tools_blockable=False 로 **선언**한다
```

`tools_blockable=False` 는 각주가 아니다. 이 벤치의 최대 미해결이고
(`docs/LIMITS.md` §4), 그 어댑터의 행에는 낙인이 찍힌다.

그다음 **반드시** `bench canary --model <name>` 를 통과해야 한다. POS 레그가 실패하면
격리 성공이 아니라 프로브 고장이고, 그 상태로 모은 데이터는 무효다.

## 새 실험을 추가하려면

`harness_bench/experiments/<name>/` 에 다섯 개: 과제 · 프롬프트 · 오라클 · 지표 · 사전등록.

**코어를 고쳐야 한다면 먼저 물어라 — 코어가 부족한 것인지, 경계를 넘으려는 것인지.**
`core` 는 `experiments` 를 import 할 수 없고 도메인 어휘를 코드에 담을 수 없다.
테스트가 강제한다(`tests/test_core_boundary.py`).

## 규율은 협상 대상이 아니다

`docs/METHODOLOGY.md` 의 여섯 개는 전부 **실제로 일어난 사고**에서 나왔다. 빼면 더
깔끔한 숫자가 나오고, 그 숫자는 틀렸다. PR 에서 다음을 완화하는 변경은 거절된다:

- 카나리 양방향 요구 · `require_pass` 우회
- 재시도 파라미터 추가
- ARI 게이트 문턱 완화 (답을 얻고 싶어서 내리는 것 포함 — D-001 참조)
- 근거 등급 없는 처방 규칙

## 결과를 고치지 마라

원 연구와 안 맞으면 `docs/KNOWN-DISCREPANCIES.md` 에 적는다. 이상치로 판명된 행은
**삭제하지 않고** `superseded_by` 로 낙인찍는다 — 그 행이 증거다.
