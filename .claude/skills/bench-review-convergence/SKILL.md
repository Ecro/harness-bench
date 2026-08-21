---
name: bench-review-convergence
description: The review-convergence experiment in harness-bench — its tasks, measurement plan and call budget, what each trait means, and how to read its results. Use when running, extending or interpreting review-convergence, adding a task to it, or answering what its numbers mean. Pairs with the bench-measure skill, which holds the procedure and gates common to every experiment.
---

# review-convergence

**Does repeated AI code review converge, and what does the loop around it cost?**

The invariant procedure — canary, oracle gate, run, ledger, prescription — is in the
`bench-measure` skill. This one holds only what is specific to this experiment.

Full design and results: `docs/review-convergence/README.md` (`.ko.md` for Korean).

## Tasks (tier-1)

| task | contract | reference | note |
|---|---|---|---|
| `retry_policy` | 19 acceptance criteria | yes, 128 lines | dense contract; the default |
| `ttl_cache` | 8 acceptance criteria | **none, by design** | sparse contract: what does a model pick where it is silent |

Standard library only, `pytest` oracle, no toolchain. **The contract is the oracle**, so no
human adjudication is involved — which is what makes this re-runnable against a new model with
nobody in the loop.

`ttl_cache` ships no reference deliberately. Do not add one.

## Measurement plan and budget

```
spread    n_spread calls              repeated review of the verified v0; the code never
                                      changes, so the observation IS the variance
loop      n_loops x n_rounds x 2      review -> fix -> oracle
derived   0 calls                     LOC, compliance, malformed and rejection rates
```

```bash
bench run --exp review_convergence --model <name> --loops 3             # ~35 calls, full profile
bench run --exp review_convergence --model <name> --spread 0 --loops 3  # ~30 calls, loop behaviour only
```

Adding a model to the table should cost about that. Make it more expensive and nobody adds one.

## Traits, and which tier can measure them

```
tier-1   spread · loop_decay · churn_dries · churn_ratio
         rejection_rate · malformed_rate · ac_held · loc_direction
adapter  tools_blockable
tier-2   finds_per_call · verbosity_shift        ← tier-1 CANNOT measure these
```

The two tier-2 traits are unmeasurable here by construction, not by omission:

- `finds_per_call` needs an adjudicated defect set, and tier-1's `v0` is a verified-correct
  implementation with no defects to adjudicate.
- `verbosity_shift` is a contrast between repository access and none, and tier-1 tasks are
  single files with no repository.

They stay `None`. **Do not fill them with an estimate** — rules keyed on them simply do not
fire, and the profile shows the gap.

## Reading the churn traits

`churn_dries` compares the mean churn of the last half of a loop against the first half.

- Below 4 points in a loop, that loop yields no ratio.
- Below 3 usable loops, `churn_dries` is `None` — not `False`.
- Observed ratios for one model clustered at 0.611–0.732 around the 0.7 threshold, so a single
  loop lands on either side by chance. **Always read `churn_ratio` alongside the boolean.**
- A `split n:m` note means the majority was not unanimous. Say so when quoting it.

`None` here means *the loops ended too early to judge*, which is a different statement from
*churn does not converge*. Both appear in the results; do not conflate them.

## Established results

Two models, three loops each, `retry_policy`:

```
reviewers report 3-14 findings per pass on code passing 23/23 acceptance tests
contract compliance held in all 54 loop rounds  -> compliance discriminates nothing
loc_direction    1.258x  vs  0.906x             -> a model property; decides loop length
rejection_rate   0.209   vs  0.273              -> the fixer is not a rubber stamp
churn            does not converge / not measurable
```

`loc_direction` is the strongest cross-model result here and is graded `***`. The churn rules
are graded `**` — the verdict was a split, and the second model cannot be measured on that
trait at all, so "reproduced across models" is structurally unreachable for it.

## Adding a task

```
tasks/<slug>/SPEC.md              the human-readable contract
tasks/<slug>/test_acceptance.py   the frozen suite — this is the oracle
tasks/<slug>/reference.py         optional known-good implementation
```

Register a `Task(slug, module_name, n_ac, has_reference)` in `tasks/__init__.py`. It must pass
`oracle.verify()` before any number from it is quotable; CI runs that on every push.

Write the suite from the SPEC **before** any implementation exists, and do not edit it
afterwards. That freeze is the only defence against *"the tests were fitted to the
implementation"* — it covers comments, and it covers translating them.
