# 기여

[English](CONTRIBUTING.md)

이 저장소에 새 모델이나 새 실험을 얹는 방법과, 완화하면 안 되는 규율을 적는다.
구조의 이유는 [`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) 에 있다.

## 훅 설치

```bash
pip install pre-commit && pre-commit install
```

시크릿 스캐너와 게이트가 매 커밋마다 돈다. `.git/hooks` 는 클론에 따라오지 않으므로, 이 단계를
건너뛰면 문서가 3중이라고 말하는 시크릿 방어가 실제로는 2중이다.

## 모델 추가

`harness_bench/core/runner/adapters.py` 에 `Adapter` 하나를 더하면 된다. 어댑터는 그 모델의
CLI 를 어떻게 부르고 그 응답을 어떻게 읽는지를 아는 얇은 층이다. **의무는 다섯 개다.**

```text
argv()        헤드리스 단발 호출로 부른다 — 대화형 REPL 도, 세션 resume 도 아니다
STDIN         프롬프트는 표준 입력으로 넘긴다. 명령행 인자(argv) 금지 — 큰 입력은 잘리거나
              인자 길이 상한(ARG_MAX)을 넘고, 조용히 손상된 입력은 여기서 최악의 실패다.
              다른 모든 수치가 그것을 기준으로 측정되기 때문이다
parse()       응답 봉투에서 최종 텍스트 · 해석된 모델 id · 토큰 사용량을 꺼낸다
usage()       입출력 토큰 수. 못 얻으면 `degraded` 로 표시한다. 조용한 0 이 아니다
tools         그 CLI 에서 도구를 끌 수 있는지 선언한다 (`tools_blockable`)
```

`parse()` 가 **해석된 모델 id** 를 꺼내야 하는 이유는, 별칭(alias)이 배치 도중 다른 백엔드로
재지정될 수 있기 때문이다. 요청한 이름이 아니라 실제로 답한 모델을 기록해야 나중에 대조할 수
있다.

`tools_blockable=False` 는 각주가 아니다. 알려진 교란이며([`docs/LIMITS.ko.md`](docs/LIMITS.ko.md)
§4), 그 어댑터의 행에는 낙인이 찍힌다.

그다음 `bench canary --exp <experiment> --model <name>` 를 통과해야 한다. 카나리는 재기 전에
격리가 실제로 걸렸는지 확인하는 프로브이고, 양방향으로 본다 — 보여야 할 것이 보이는가(POS),
안 보여야 할 것이 정말 안 보이는가(NEG). **POS 레그 실패는 격리가 작동한 것이 아니라 프로브가
고장난 것**이고, 그 상태에서 모은 데이터는 무효다.

## 실험 추가

`harness_bench/experiments/<name>/` 에 다섯 개를 제공한다: 과제 · 프롬프트 · 오라클 · 지표 ·
사전등록. 코드를 이렇게 가른 것과 같은 이유로, 자기 `bench-<name>` 스킬도 함께 가져온다.

CLI 는 그 패키지를 발견해 모듈 셋으로 구동한다. `bench` 가 import 하는 이름은 이 셋뿐이고,
CLI 도 `core` 도 이 셋의 의미를 알아서는 안 된다.

```text
canary.build() / canary.plant(scratch)      양방향 격리 프로브
run.measure(model, ...) -> Profile          측정
traits.TRAIT_KEYS / traits.RULES            무엇을 재고, 그것이 무엇을 결정하는가
```

`Profile` 은 측정된 특성의 모음이고, `TRAIT_KEYS` 는 그 특성의 이름과 설명, `RULES` 는 특성을
하네스 설정으로 옮기는 규칙이다. 규칙에는 반드시 근거 등급이 붙는다 — `***` 는 두 모델
이상에서 재현된 것, `**` 는 한 번 측정된 것, `*` 는 판단이다. 등급 없는 규칙은 렌더되지 않는다.

결과에는 `"<실험>/<과제>"` 가 기록되므로, 원장(`results/ledger-<실험>.md`)과 모든 처방은 한
실험의 특성 어휘 안에 머문다.

문서는 `docs/<실험>/` 에 둔다 — 발견·방법·처방·장문 서사, 그리고 그 실험의 첫 페이지가 될
`README.md`. `docs/` 최상위에는 모음 전체에 해당하는 `DESIGN` 과 `LIMITS` 만 남는다.

`core` 를 고쳐야 한다면, 코어가 부족한 것인지 경계를 넘으려는 것인지 먼저 물어라. `core` 는
`experiments` 를 import 할 수 없고 도메인 어휘를 코드에 담을 수 없다.
`tests/test_core_boundary.py` 가 둘 다 강제한다.

## 규율은 협상 대상이 아니다

[`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) §3 에 여섯 개가 있다. 빼면 더 깔끔한 숫자가 나오고,
그 숫자는 틀렸다. 다음을 완화하는 PR 은 거절된다.

- 양방향 카나리 요구, 또는 `require_pass()` 의 우회
- retry 파라미터 — 응답이 잘 나올 때까지 다시 부르면 잘 행동한 표본만 남고, 바로 그 변동폭이
  측정 대상이다
- ARI 문턱 완화 — 실행이 `UNQUOTABLE` 로 돌아왔다는 이유로 내리는 것을 포함한다.
  `UNQUOTABLE` 은 게이트를 통과하지 못해 숫자를 내주지 않는다는 반환값이고,
  *"측정할 수 없었다"* 는 그 자체로 발표 가능한 결과다
- 근거 등급 없는 처방 규칙

## 결과를 맞추려고 고치지 마라

어떤 측정이 이전 것과 어긋나면 **둘 다 기록한다.** 이상치로 판명된 행은 `superseded_by` 로
표시하고 삭제하지 않는다 — **분포가 곧 발견이다.**
