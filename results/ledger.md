# ledger

이 표는 **모델 순위표가 아니다.** 하네스 설계의 효과를 재는 특성값이다.
`docs/LIMITS.md` 를 같이 읽어라.

| model | version | when | calls | cost | spread | loop_decay | churn_dries | churn_ratio | rejection_rate | malformed_rate | ac_held | loc_direction | tools_blockable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude ~~(superseded)~~ | claude-opus-5 | 2026-08-21 | 15 | $6.60 | 2 | -0.5 | True | — | 0.458 | 0.0 | True | 1.391 | True |
| claude | claude-opus-5 | 2026-08-21 | 30 | $15.74 | — | -1.25 | False | 0.688 | 0.209 | 0.0 | True | 1.258 | True |
| codex | gpt-5.6-sol | 2026-08-21 | 8 | — | 2 | -4.0 | — | — | 0.0 | 0.0 | True | 1.016 | False |
| codex | gpt-5.6-sol | 2026-08-21 | 24 | — | — | -0.25 | — | 0.394 | 0.273 | 0.0 | True | 0.906 | False |

## 단서
- `claude` — EXPLORATORY: 예측을 사전 동결하지 않은 측정
- `claude` — superseded by 3-loop run (D-001). 삭제하지 않는다: n=1 루프. churn_dries=True 는 이 실행의 ratio 0.617 에서 나왔는데, 3루프 재측정 결과 세 값이 0.611~0.732 로 문턱 0.7 언저리에 몰려 있고 판정은 False(1:2)다. 이 행은 표본을 방향으로 착각한 사례로 보존한다.
- `codex` — EXPLORATORY: 예측을 사전 동결하지 않은 측정
- `codex` — 도구를 끌 수 없는 어댑터. 차단 가능한 모델과 같은 표에 놓는 것 자체가 교란이다 (LIMITS §4)
- `codex` — 비용 미상 (0 이 아니다)
