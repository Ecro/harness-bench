# harness-bench

**LLM 하네스 설계를 모델에 걸쳐, 시간에 걸쳐 재현 가능하게 측정한다.**

[English](README.md)

새 모델이 나오면 한 번 돌려 기존 모델과 같은 표에 얹고 — 점수가 아니라 **그 모델의 운용
처방**을 받는다.

```
             측정                                  →  결정
 claude   코드 1.258× 증가 · churn 0.688            →  루프 상한 · churn 정지기준 금지
 codex    코드 0.906× 감소 · 일찍 종료               →  루프를 더 돌려도 됨 · 라운드로 상한
```

> **모델 순위표가 아니다.** 하네스 설계의 효과를 재는 것이지 모델 능력을 재지 않는다.
> [`docs/LIMITS.ko.md`](docs/LIMITS.ko.md) 참조.

## 실험 목록

harness-bench 는 **실험 모음**입니다. `core` 가 측정 기계를 제공하고, 실험 각각이 자기
과제·프롬프트·오라클·지표·사전등록을 가져옵니다. 현재 실험은 하나입니다:

| # | 실험 | 묻는 질문 | 상태 |
|---|---|---|---|
| **1** | [`review_convergence`](harness_bench/experiments/review_convergence) | AI 코드리뷰를 반복하면 수렴하는가? | **공개됨** — 아래 결과 |
| 2… | — | — | 아직 없음 |

### 📊 실험 1 — `review_convergence`: AI 코드리뷰를 반복하면 수렴하는가?

**이 모음의 첫 번째 실험입니다. 측정 11개 · 약 400회 모델 호출 · 두 벤더.**
여기서 시작하십시오:

| | |
|---|---|
| **[발견 →](docs/FINDINGS.ko.md)** | 측정된 전부, 숫자와 함께 |
| **[그래서 리뷰를 어떻게 →](docs/PRESCRIPTION.ko.md)** | 측정이 뒷받침하는 레시피 |
| **[어떻게 측정했는가 →](docs/METHODS.ko.md)** | 계측기 전부와 각각의 검증 |
| **[장문 서사 →](docs/STUDY-ko.md)** | 초고 전문 (1700줄) |
| [벤치 설계와 자체 결과 →](docs/REVIEW-BENCH.ko.md) | 재현 가능한 tier-1 실행 |

결과 넷만 먼저 보이면 이렇습니다:

```
리뷰만 반복             진짜 결함 커버리지 34% -> 61% -> 76%, 코드 위험 0
리뷰->수정 루프 반복     준수율 이득 0, 코드 +24% ~ +152%

파일만 주고 리뷰         고유 결함의 29% 가 오탐이었고, 그 오탐들이 가장 자주
                        보고됐다 (평균 발견빈도 6.8 vs 진짜 3.4)
리포 접근을 주면         그 오탐이 0% 로 떨어진다. 두 벤더의 모델 모두에서
```

> **리뷰는 여러 번, 수정은 한 번.**

모든 계측기는 쓰이기 전에 검증됩니다 — 격리는 양방향 카나리로, 인수 스위트는 보증을 하나
지우고 알아채는지 확인해서, 클러스터링은 안정성 게이트와 다른 벤더 모델로, 차등 하네스는
심어둔 발산으로, 자유 공간 분모는 뮤테이션 테스트로. 계측기가 숫자를 뒷받침할 수 없으면
각주 달린 숫자가 아니라 `UNQUOTABLE` 또는 `None` 을 반환합니다.
[`docs/METHODS.ko.md`](docs/METHODS.ko.md)

---

## 빠른 시작

```bash
pip install -e ".[dev]"
pytest -q                                  # 경계 + 재현 게이트. 모델 호출 없음

bench canary --model claude                # 격리를 양방향으로 먼저 확인
bench run    --model claude --loops 3
bench compare                              # 원장 재생성
bench prescribe --model claude             # 특성 → 운용 처방
```

## 산출물

실행 하나당 셋 — **raw**(모든 호출·응답·토큰·시각), **profile**(측정된 특성),
**prescription**(특성을 하네스 설정으로 옮긴 것, 줄마다 근거 등급 병기).

```
## 운용 처방
  [**]  round_cap     라운드 상한을 걸어라 — churn 이 수렴하지 않는다
  [***] loop_budget   루프를 짧게 끊어라 — 이 모델은 라운드마다 코드를 불린다
        ← loc_direction > 1.15

  등급: *** 두 모델 이상에서 재현 · ** 단일 측정 · * 판단
```

등급 없는 규칙은 렌더되지 않는다.

## 구조

```
harness_bench/
  core/          "어떻게 재는가" 를 알고 "무엇을 재는가" 는 모른다
                 (sandbox · runner · cluster · prereg · stats · ledger)
  experiments/
    review_convergence/    실험 1 — AI 코드리뷰를 반복하면 수렴하는가
    <다음>/                 두 번째 실험이 자기 bench-<name> 스킬과 함께 여기 들어온다
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

## 현재 결과

실험 1(`review_convergence`), 과제 `retry_policy`, 두 모델, 각 3루프 — 2026-08-21 측정.

| 모델 | 콜 | 비용 | loop_decay | churn | 거절률 | 코드 크기 | 도구 차단 |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 30 | $15.74 | −1.25 | 수렴 안 함 | 0.209 | **1.258×** | 가능 |
| gpt-5.6-sol | 24 | 미상 | −0.25 | 측정 불가 | 0.273 | **0.906×** | **불가** |

54개 루프 라운드 전체에서 **계약 준수가 매 라운드 유지됐다** — 그러는 동안 리뷰어들은
이미 23개 인수 테스트를 전부 통과하는 코드에 대해 패스당 3~14건을 계속 보고했다.

전체 설계와 결과: [`docs/REVIEW-BENCH.ko.md`](docs/REVIEW-BENCH.ko.md)

## 문서

| | |
|---|---|
| [`docs/METHODS.ko.md`](docs/METHODS.ko.md) | 각 숫자를 어떻게 얻었고 계측기를 어떻게 검증했는가 |
| [`docs/FINDINGS.ko.md`](docs/FINDINGS.ko.md) | 실험 1에서 측정된 전부, 숫자와 함께 |
| [`docs/PRESCRIPTION.ko.md`](docs/PRESCRIPTION.ko.md) | 측정이 뒷받침하는 리뷰 레시피 |
| [`docs/STUDY-ko.md`](docs/STUDY-ko.md) | 장문 서사 초고 |
| [`docs/DESIGN.ko.md`](docs/DESIGN.ko.md) | harness-bench 구조와 여섯 규율 |
| [`docs/REVIEW-BENCH.ko.md`](docs/REVIEW-BENCH.ko.md) | 실험 1 전문: 설계·과제·결과 |
| [`docs/LIMITS.ko.md`](docs/LIMITS.ko.md) | 이 벤치로 주장할 수 없는 것 |
| [`CONTRIBUTING.ko.md`](CONTRIBUTING.ko.md) | 모델 추가, 실험 추가 |

## 라이선스

코드 — **Apache-2.0** ([`LICENSE`](LICENSE)).
프롬프트·과제·데이터·결과 — **CC BY 4.0** ([`LICENSE-DATA`](LICENSE-DATA)).
경계는 [`NOTICE`](NOTICE) 에 있다.
