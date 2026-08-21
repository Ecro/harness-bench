# ledger

**This is not a model leaderboard.** These are trait values measuring the effect of harness design.
Read it with `docs/LIMITS.md`.

| model | version | when | calls | cost | spread | loop_decay | churn_dries | churn_ratio | rejection_rate | malformed_rate | ac_held | loc_direction | tools_blockable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude ~~(superseded)~~ | claude-opus-5 | 2026-08-21 | 15 | $6.60 | 2 | -0.5 | True | — | 0.458 | 0.0 | True | 1.391 | True |
| claude | claude-opus-5 | 2026-08-21 | 30 | $15.74 | — | -1.25 | False | 0.688 | 0.209 | 0.0 | True | 1.258 | True |
| codex | gpt-5.6-sol | 2026-08-21 | 8 | — | 2 | -4.0 | — | — | 0.0 | 0.0 | True | 1.016 | False |
| codex | gpt-5.6-sol | 2026-08-21 | 24 | — | — | -0.25 | — | 0.394 | 0.273 | 0.0 | True | 0.906 | False |

## Caveats
- `claude` -- EXPLORATORY: predictions not frozen before the run
- `claude` -- superseded by 3-loop run. Kept, not deleted: Single loop (n=1). churn_dries=True came from this run's ratio 0.617; the three-loop re-measurement gave 0.611 / 0.732 / 0.720 -- clustered around the 0.7 threshold, verdict False (split 1:2). Kept because the distribution is the finding: one loop lands on either side of the boundary by chance.
- `codex` -- EXPLORATORY: predictions not frozen before the run
- `codex` -- cost unknown (not zero)
- `codex` -- tools cannot be disabled for this adapter; sharing a table with one that can is itself a confound (LIMITS 4)
