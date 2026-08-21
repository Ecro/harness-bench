# harness-bench

**LLM 하네스 설계를 모델에 걸쳐, 시간에 걸쳐 재현 가능하게 측정한다.**

[English](README.md)

harness-bench 는 **하네스** — 모델을 감싸는 루프, 프롬프트, 도구 접근 권한, 정지 조건 —
를 바꿨을 때 결과가 실제로 얼마나 달라지는지를 재는 측정 장치다. 과제와 인수 테스트는
어떤 구현보다 먼저 동결되고, 예측은 반증 조건과 함께 사전등록되며, 격리는 실행 전에
양방향 카나리로 확인된다. 계측기가 숫자를 뒷받침하지 못하면 각주 달린 숫자가 아니라
`UNQUOTABLE` 또는 `None` 이 나온다.

새 모델이 나오면 한 번 돌려 기존 모델과 같은 표에 얹고 — 점수가 아니라 **그 모델의 운용
처방**을 받는다. 실행 하나가 raw(모든 호출과 응답) · profile(측정된 특성) ·
prescription(그 특성을 하네스 설정으로 옮긴 것) 셋을 남기고, 처방은 줄마다 근거 등급을
달고 나온다.

```
             측정                                  →  결정
 claude   코드 1.258× 증가 · churn 0.688            →  루프 상한 · churn 정지기준 금지
 codex    코드 0.906× 감소 · 일찍 종료               →  루프를 더 돌려도 됨 · 라운드로 상한
```

## 실험 목록

harness-bench 는 **실험 모음**이다. `core` 가 측정 기계 — 샌드박스, 러너, 클러스터링,
사전등록, 통계, 원장 — 를 제공하고 어떤 주제도 알지 못한다. 실험 각각이 자기 과제·프롬프트·
오라클·지표·사전등록과 자기 `bench-<name>` 스킬을 가져온다. 현재 실험은 하나다:

| # | 실험 | 묻는 질문 | 상태 |
|---|---|---|---|
| **1** | [`review_convergence`](harness_bench/experiments/review_convergence) | AI 코드리뷰를 반복하면 수렴하는가? | **공개됨** — [결과](docs/review-convergence/README.ko.md) |
| 2… | — | — | 아직 없음 |

아래 실험 절을 제외한 나머지는 모두 모음 전체에 해당한다 — 어떤 실험을 돌리든 같은 명령,
같은 산출물, 같은 규율이 적용된다.

### 📊 실험 1 — `review_convergence`

**측정 11개 · 약 400회 모델 호출 · 두 벤더.** 결과 넷만 먼저 보이면 이렇다:

```
리뷰만 반복             진짜 결함 커버리지 34% -> 61% -> 76%, 코드 위험 0
리뷰->수정 루프 반복     준수율 이득 0, 코드 +24% ~ +152%

파일만 주고 리뷰         고유 결함의 29% 가 오탐이었고, 그 오탐들이 가장 자주
                        보고됐다 (평균 발견빈도 6.8 vs 진짜 3.4)
리포 접근을 주면         그 오탐이 0% 로 떨어진다. 두 벤더의 모델 모두에서
```

> **리뷰는 여러 번, 수정은 한 번.**

| | |
|---|---|
| **[발견 →](docs/review-convergence/FINDINGS.ko.md)** | 측정된 전부, 숫자와 함께 |
| **[그래서 리뷰를 어떻게 →](docs/review-convergence/PRESCRIPTION.ko.md)** | 측정이 뒷받침하는 레시피 |
| **[어떻게 측정했는가 →](docs/review-convergence/METHODS.ko.md)** | 계측기 전부와 각각의 검증 |
| [실험 1 전문 →](docs/review-convergence/README.ko.md) | 설계·과제·재현 가능한 tier-1 실행 |
| [장문 서사 →](docs/review-convergence/STUDY-ko.md) | 연구 전체를 한 흐름으로 |

과제 `retry_policy`, 두 모델, 각 3루프 — 2026-08-21 측정:

| 모델 | 콜 | 비용 | loop_decay | churn | 거절률 | 코드 크기 | 도구 차단 |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 30 | $15.74 | −1.25 | 수렴 안 함 | 0.209 | **1.258×** | 가능 |
| gpt-5.6-sol | 24 | 미상 | −0.25 | 측정 불가 | 0.273 | **0.906×** | **불가** |

`loop_decay` 는 라운드가 갈수록 지적 수가 줄어드는 기울기, `churn` 은 한 라운드에서
추가·삭제된 줄 수(손댄 양이지 품질이 아니다), `코드 크기` 는 마지막 라운드를 시작 코드로 나눈
값이다. 각 열의 정의는 [실험 문서](docs/review-convergence/README.ko.md#원장)에 있다.

54개 루프 라운드 전체에서 **계약 준수가 매 라운드 유지됐다** — 그러는 동안 리뷰어들은
이미 23개 인수 테스트를 전부 통과하는 코드에 대해 패스당 3~14건을 계속 보고했다. 전체
표는 [`results/ledger-review_convergence.md`](results/ledger-review_convergence.md) 이고
`bench compare` 가 재생성한다.

> **모델 순위표가 아니다.** 특성 값은 하네스 설계의 효과를 재는 것이지 모델 능력을 재지
> 않는다. 이 벤치로 주장할 수 없는 것: [`docs/LIMITS.ko.md`](docs/LIMITS.ko.md).

---

## 빠른 시작

```bash
pip install -e ".[dev]"
pytest -q                                    # 경계 + 재현 게이트. 모델 호출 없음

EXP=review_convergence
bench canary    --exp $EXP --model claude    # 격리를 양방향으로 먼저 확인
bench run       --exp $EXP --model claude --loops 3
bench compare   --exp $EXP                   # 그 실험의 원장 재생성
bench prescribe --exp $EXP --model claude    # 특성 → 운용 처방
```

실험이 하나뿐인 동안은 `--exp` 를 생략해도 된다. 두 번째 실험이 들어오면 필수가 된다 —
명령이 첫 실험의 의미를 조용히 물려받지 않도록.

## 산출물

실행 하나당 셋 — **raw**(모든 호출·응답·토큰·시각), **profile**(측정된 특성),
**prescription**(특성을 하네스 설정으로 옮긴 것, 줄마다 근거 등급 병기).

```
## Operating prescription
  [** ] round_cap                cap the rounds
        ← churn does not converge, so the loop has no self-firing stop condition
  [***] loop_budget              keep the loop short - this model grows the code each round
        ← loc_direction > 1.15; the opposite direction was measured on the other model

  grades: *** reproduced across models | ** measured once | * judgement, not measured
```

CLI 출력은 영어다. 대괄호 안이 **근거의 강도**이고 — `***` 두 모델 이상에서 재현,
`**` 한 번 측정, `*` 판단 — 문서에서는 같은 등급을 `[근거: 재현됨]` 처럼 풀어 쓴다.
등급 없는 규칙은 아예 렌더되지 않는다.

## 구조

```
harness_bench/
  core/          "어떻게 재는가" 를 알고 "무엇을 재는가" 는 모른다
                 (sandbox · runner · cluster · prereg · stats · ledger)
  experiments/
    review_convergence/    실험 1 — AI 코드리뷰를 반복하면 수렴하는가
    <다음>/                 두 번째 실험이 자기 bench-<name> 스킬과 함께 여기 들어온다
docs/
  DESIGN.ko.md · LIMITS.ko.md    모음 전체 — 어떻게 재는가, 무엇을 주장할 수 없는가
  review-convergence/            실험 1 의 문서 — 결과·방법·처방
  <다음>/                         두 번째 실험의 문서는 그 옆에 들어온다. 섞이지 않는다
results/
  ledger-<실험>.md                원장은 실험마다 하나
```

`core` 는 `experiments` 를 import 할 수 없고 도메인 어휘를 코드에 담을 수 없다. 테스트로
강제한다 — 두 번째 실험이 첫 실험의 가정을 조용히 물려받지 못하게.

## 코드로 강제되는 규율

위반은 경고가 아니라 거부를 낳는다.

```
양방향 카나리   POS/NEG 레그가 둘 다 없으면 Canary 가 생성 시점에 예외를 던진다.
               require_pass() 에 우회 플래그가 없다
재시도 금지     call() 에 retry 파라미터가 없고, 테스트가 그 부재를 강제한다
ARI 게이트      문턱 미달이면 숫자가 아니라 문자열 UNQUOTABLE 을 반환한다
사전등록        반증 조건 없는 예측은 거부된다. 동결 후 편집된 파일은 로드에 실패한다.
               미등록 실행에는 낙인이 찍힌다
근거 등급       등급 없는 처방 규칙은 렌더되지 않는다
환경 검증       /tmp 아래 스크래치는 거부된다. 별칭이 아니라 해석된 모델 id 를 기록한다.
               어댑터는 도구를 끌 수 있는지를 선언한다
```

각각의 근거: [`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) §3.

## 실험 추가하기

새 실험은 `harness_bench/experiments/` 아래의 패키지다. CLI 가 그것을 발견해 모듈 셋으로
구동한다 — `core` 도 CLI 도 이 셋의 의미를 알아서는 안 된다:

```
canary.build() / canary.plant(scratch)      양방향 격리 프로브
run.measure(model, ...) -> Profile          측정
traits.TRAIT_KEYS / traits.RULES            무엇을 재고, 그것이 무엇을 결정하는가
```

여기에 동결된 과제·프롬프트·오라클·사전등록과 자기 `bench-<name>` 스킬을 함께 가져온다.
문서는 `docs/<실험>/` 아래에 둔다 — 모음 전체를 다루는 `docs/` 최상위에 두지 않는다. 거기 두면
두 번째 실험의 결과가 모음 전체의 결과처럼 읽힌다.
[`CONTRIBUTING.ko.md`](CONTRIBUTING.ko.md) 참조.

## 문서

모음 전체:

| | |
|---|---|
| [`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) | 구조와 여섯 규율 |
| [`docs/LIMITS.ko.md`](docs/LIMITS.ko.md) | 이 벤치로 주장할 수 없는 것 |
| [`CONTRIBUTING.ko.md`](CONTRIBUTING.ko.md) | 모델 추가, 실험 추가 |

실험 1 — `review_convergence`:

| | |
|---|---|
| [`docs/review-convergence/README.ko.md`](docs/review-convergence/README.ko.md) | 실험 전문: 설계·과제·결과 |
| [`docs/review-convergence/METHODS.ko.md`](docs/review-convergence/METHODS.ko.md) | 각 숫자를 어떻게 얻었고 계측기를 어떻게 검증했는가 |
| [`docs/review-convergence/FINDINGS.ko.md`](docs/review-convergence/FINDINGS.ko.md) | 측정된 전부, 숫자와 함께 |
| [`docs/review-convergence/PRESCRIPTION.ko.md`](docs/review-convergence/PRESCRIPTION.ko.md) | 측정이 뒷받침하는 리뷰 레시피 |
| [`docs/review-convergence/STUDY-ko.md`](docs/review-convergence/STUDY-ko.md) | 장문 서사 — 실험과 정정의 전체 기록 |

## 라이선스

코드 — **Apache-2.0** ([`LICENSE`](LICENSE)).
프롬프트·과제·데이터·결과 — **CC BY 4.0** ([`LICENSE-DATA`](LICENSE-DATA)).
경계는 [`NOTICE`](NOTICE) 에 있다.
