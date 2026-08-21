# review-convergence — design and results

[한국어](REVIEW-BENCH.ko.md)

The question: **does repeated AI code review converge, and what does the loop around it cost?**

---

## 1. Design

### Contract-as-oracle

Each task ships a specification, a frozen acceptance suite derived from it, and (where a
known-good implementation exists) a reference. The suite is the oracle, so **no human
adjudication is needed** — which is what makes the experiment re-runnable against a new model
with nobody in the loop.

### Tier-1 tasks

| task | contract | reference | note |
|---|---|---|---|
| `retry_policy` | 19 acceptance criteria | yes, 128 lines | exponential backoff + full jitter + circuit breaker |
| `ttl_cache` | 8 acceptance criteria | **none, by design** | the question is what a model picks where the contract is silent |

Pure standard library, `pytest` only, no toolchain.

### The oracle is verified before it is used

```
retry_policy    reference passes            23/23
                import failure floors       0 passed
                single-guarantee removal    3 tests catch it
ttl_cache       reference passes            SKIP (ships none, by design)
                import failure floors       0 passed
```

A suite that stays green after a guarantee is deleted is not measuring that guarantee.
No number from a task is quotable until `oracle.verify()` passes; CI runs it on every push.

### What one measurement costs

```
spread     n_spread calls            repeated review of the verified v0; code never changes
loop       n_loops × n_rounds × 2    review → fix → oracle
derived    0 calls                   LOC, compliance, malformed rate, rejection rate
```

Default 5 spread + 3 loops × 5 rounds = **35 calls per model**. Adding a new model to the
table should cost about that; more and nobody adds one.

---

## 2. Results

Measured 2026-08-21. `retry_policy`. Two models, three loops each.

### The headline

**Reviewers report findings on code that is already correct — and the loop never breaks the
contract while doing so.**

```
v0 passes 23/23 acceptance tests.

claude   every one of 5 independent reviews reported 12-14 findings
codex    every one of 5 independent reviews reported  3-5  findings

30 loop rounds (claude) + 24 (codex): contract compliance 23/23 in EVERY round.
```

Compliance is therefore useless as a discriminator. What separates the arms is everything
else.

### Ledger

| model | version | calls | cost | spread | loop_decay | churn_dries | churn_ratio | rejection | loc_direction | tools_blockable |
|---|---|---|---|---|---|---|---|---|---|---|
| claude | claude-opus-5 | 30 | $15.74 | — | −1.25 | False | 0.688 | 0.209 | **1.258×** | yes |
| codex | gpt-5.6-sol | 24 | n/a | — | −0.25 | — | 0.394 | 0.273 | **0.906×** | **no** |

### Finding 1 — the loop grows or shrinks code, and the direction is a model property

```
claude   1.258×    code grows every round
codex    0.906×    code shrinks while findings are applied
```

This is the strongest cross-model result here: both directions measured independently, and
consistent with the same split observed on a second task family. It decides how long a loop
may safely run.

### Finding 2 — churn convergence is not a usable stop rule for every model

The intuition that "churn falls to zero, so stop there" holds for neither model, for
different reasons.

```
claude   L1 [90, 100, 107,  65, 51]   ratio 0.611
         L2 [101, 82, 101, 101, 33]   ratio 0.732
         L3 [106, 69,  82,  51, 75]   ratio 0.720
         verdict: does not dry (split 1:2)

codex    L1 [54, 13]                  2 points — too short to judge
         L2 [22, 20, 3, 15, 5]        ratio 0.476
         L3 [49, 18, 18, 3]           ratio 0.313
         verdict: NOT MEASURABLE (2 of 3 loops usable)
```

Two things follow.

**The three claude ratios sit at 0.611–0.732, straddling the 0.7 threshold.** A single loop
lands on either side of it. This trait requires at least three loops before it is judged at
all, and the continuous `churn_ratio` should be read alongside the boolean.

**codex terminates before the series is long enough.** The correct statement is not "codex
dries quickly" but "codex ends too early for this to be measured" — its loops reached zero
findings at rounds 3 and 5. A different statement, and the accurate one.

### Finding 3 — the fixer rejects a fifth to a quarter of what it is handed

```
claude   0.209   (32 / 153)
codex    0.273   ( 9 /  33)
```

Rejections cite the contract. The fixer is the last gate before a review finding becomes a
code change, and it is not a rubber stamp.

### Finding 4 — findings decline slowly, and never to zero for one model

```
claude   13 → 9 → 9 → 9 → 8      slope −1.25, still 8 at round 5
codex     4 → 4 → 4 → 3 → 3      slope −0.25, but loops end early at 0
```

### Prescriptions produced from these traits

```
claude   [**]  round_cap      cap the rounds — churn does not converge
         [**]  churn_gate     do not use churn convergence as a stop rule
         [***] loop_budget    keep the loop short; this model grows the code each round

codex    [*]   churn_gate     no basis for a churn stop rule — cap the rounds instead
         [***] loop_budget    the loop may run longer; this model does not grow the code
         [*]   comparability  not directly comparable — tools cannot be disabled
```

---

## 3. What this bench does not measure

`finds_per_call` and `verbosity_shift` are **tier-2 traits**: the first needs an adjudicated
defect set, and tier-1's `v0` is a verified-correct implementation with no defects to
adjudicate; the second needs a repository-access contrast, and tier-1 tasks are single files.

Consequently the strongest result from the wider study this bench derives from — that giving
reviewers repository access removes false positives — is **not re-confirmed by a tier-1 run**.
See [`LIMITS.md`](LIMITS.md).

## 4. Adding a task

```
tasks/<slug>/SPEC.md              the human-readable contract
tasks/<slug>/test_acceptance.py   the frozen suite — this is the oracle
tasks/<slug>/reference.py         optional known-good implementation
```

Then register a `Task(slug, module_name, n_ac, has_reference)`. It must pass
`oracle.verify()` before any number from it is quotable.
