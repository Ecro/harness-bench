# 기여

[English](CONTRIBUTING.md)


## 훅 설치

```bash
pip install pre-commit && pre-commit install
```

시크릿 스캐너와 게이트가 매 커밋마다 돈다. `.git/hooks` 는 클론에 따라가지 않으므로,
이 단계를 건너뛰면 문서가 3중이라고 말하는 시크릿 방어가 실제로는 2중이다.

## 모델 추가

`harness_bench/core/runner/adapters.py` 에 `Adapter` 하나. **의무 다섯 개:**

```
argv()        헤드리스 단발 호출 — REPL 도 resume 도 아니다
STDIN         프롬프트는 stdin 으로. argv 금지 — 큰 입력은 잘리거나 ARG_MAX 를 넘고,
              조용히 손상된 입력은 여기서 최악의 실패다. 다른 모든 수치가 그것을
              기준으로 측정되기 때문이다
parse()       봉투에서 최종 텍스트 · 해석된 모델 id · 토큰 사용량을 꺼낸다
usage()       입출력 토큰 — 못 얻으면 `degraded` 이지 조용한 0 이 아니다
tools         도구를 끌 수 있는지 선언한다 (`tools_blockable`)
```

`tools_blockable=False` 는 각주가 아니다. 알려진 교란이며([`docs/LIMITS.ko.md`](docs/LIMITS.ko.md)
§4) 그 어댑터의 행에는 낙인이 찍힌다.

그다음 `bench canary --exp <experiment> --model <name>` 를 통과해야 한다. POS 레그 실패는
격리가 작동한 것이 아니라 **프로브가 고장난 것**이고, 그 상태에서 모은 데이터는 무효다.

## 실험 추가

`harness_bench/experiments/<name>/` 에 다섯 개를 제공한다: 과제 · 프롬프트 · 오라클 · 지표 ·
사전등록. 코드를 이렇게 가른 것과 같은 이유로, 자기 `bench-<name>` 스킬도 함께 가져온다.

CLI 가 그 패키지를 발견해 모듈 셋으로 구동한다. `bench` 가 import 하는 이름은 이 셋뿐이고,
CLI 도 `core` 도 이 셋의 의미를 알아서는 안 된다:

```
canary.build() / canary.plant(scratch)      양방향 격리 프로브
run.measure(model, ...) -> Profile          측정
traits.TRAIT_KEYS / traits.RULES            무엇을 재고, 그것이 무엇을 결정하는가
```

결과에는 `"<실험>/<과제>"` 가 기록되므로, 원장(`results/ledger-<실험>.md`)과 모든 처방은
한 실험의 특성 어휘 안에 머문다.

`core` 를 고쳐야 한다면, 코어가 부족한 것인지 경계를 넘으려는 것인지 먼저 물어라. `core` 는
`experiments` 를 import 할 수 없고 도메인 어휘를 코드에 담을 수 없다.
`tests/test_core_boundary.py` 가 둘 다 강제한다.

## 규율은 협상 대상이 아니다

[`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) §3 에 여섯 개가 있다. 빼면 더 깔끔한 숫자가 나오고,
그 숫자는 틀렸다. 다음을 완화하는 PR 은 거절된다.

- 양방향 카나리 요구, 또는 `require_pass()` 의 우회
- retry 파라미터
- ARI 문턱 완화 — 실행이 `UNQUOTABLE` 로 돌아왔다는 이유로 내리는 것 포함
- 근거 등급 없는 처방 규칙

## 결과를 맞추려고 고치지 마라

어떤 측정이 이전 것과 어긋나면 **둘 다 기록한다.** 이상치로 판명된 행은 `superseded_by` 로
표시하고 삭제하지 않는다 — **분포가 곧 발견이다.**
