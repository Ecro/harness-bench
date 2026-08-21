# ledger

이 표는 **모델 순위표가 아니다.** 하네스 설계의 효과를 재는 특성값이다.
`docs/LIMITS.md` 를 같이 읽어라.

| model | version | when | calls | cost | spread | loop_decay | churn_dries | rejection_rate | malformed_rate | ac_held | loc_direction | tools_blockable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude | claude-opus-5 | 2026-08-21 | 15 | $6.60 | 2 | -0.5 | True | 0.458 | 0.0 | True | 1.391 | True |
| codex | gpt-5.6-sol | 2026-08-21 | 8 | — | 2 | -4.0 | — | 0.0 | 0.0 | True | 1.016 | False |

## 단서
- `claude` — EXPLORATORY: 예측을 사전 동결하지 않은 측정
- `codex` — EXPLORATORY: 예측을 사전 동결하지 않은 측정
- `codex` — 도구를 끌 수 없는 어댑터. 차단 가능한 모델과 같은 표에 놓는 것 자체가 교란이다 (LIMITS §4)
- `codex` — 비용 미상 (0 이 아니다)
