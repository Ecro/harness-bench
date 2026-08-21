# review-convergence — design and results

[한국어](README.ko.md)

The question this experiment asks: **does repeated AI code review converge, and what does the
loop around it cost?**

This page covers the experiment's design and the benchmark's own runs.
The measurements from the wider study are in [`FINDINGS.md`](FINDINGS.md), and how each
instrument was validated is in [`METHODS.md`](METHODS.md).

---

## 1. Design

### The contract is the oracle

An oracle is whatever decides that a result is right or wrong.

Here each task ships a specification, a **frozen** acceptance suite derived from it, and — where
a known-good implementation exists — a reference. Frozen means fixed before any implementation
existed and never edited since.

**Because the suite is the oracle, no human adjudication is needed.** That is what makes it
possible to rerun the whole thing, unattended, when a new model ships.

### The tier-1 tasks

tier-1 means a task where the contract and its frozen tests settle everything, so anyone can
reproduce it.

| task | contract | reference | notes |
|---|---|---|---|
| `retry_policy` | 19 acceptance criteria | yes, 128 lines | exponential backoff + full jitter + circuit breaker |
| `ttl_cache` | 8 acceptance criteria | **none, deliberately** | what does a model choose where the contract is silent |

An acceptance criterion is one verifiable sentence carved out of what the specification
guarantees. The tasks use the standard library and `pytest` only — no toolchain.

### The oracle is validated before it is used

```text
retry_policy    reference passes             23/23
                floor on import failure      0 passed
                one guarantee removed        3 tests catch it
ttl_cache       reference passes             SKIP (no reference, deliberately)
                floor on import failure      0 passed
```

A suite that stays green after a guarantee is deleted **is not measuring that guarantee.**
No number from a task may be quoted until `oracle.verify()` passes, and CI runs it on every
push.

### What one measurement costs

```text
spread    n_spread calls             repeated review of the verified v0; the code never changes
loop      n_loops × n_rounds × 2     review → fix → oracle
derived   0 calls                    LOC · compliance · malformed · decline rate
```

`n_spread` is how many times the same code is reviewed, `n_rounds` how many review→fix passes
one loop makes, and `n_loops` how many times that loop is repeated. The last row costs nothing
because it is computed from responses already collected — `malformed` is the share of responses
that would not parse despite a structured-output instruction.

At the defaults — spread 5 plus 3 loops × 5 rounds — that is **35 calls per model**. Putting a
new model in the table should cost about that. Make it more expensive and nobody adds one.

---

## 2. Results

Measured 2026-08-21 on `retry_policy`, three loops per model.

### The headline

**Reviewers report findings on code that is already correct — and the loop never breaks the
contract while they do.**

```text
v0 passes 23/23 acceptance tests.

claude   all 5 independent reviews reported 12-14 findings
codex    all 5 independent reviews reported  3-5 findings

30 loop rounds (claude) + 24 (codex): compliance 23/23 in every round.
```

So **compliance discriminates nothing.** Everything that separates the conditions is elsewhere.

### The ledger

| model | version | calls | cost | loop_decay | churn_dries | churn_ratio | decline rate | loc_direction | tools blockable |
|---|---|---|---|---|---|---|---|---|---|
| claude | claude-opus-5 | 30 | $15.74 | −1.25 | False | 0.688 | 0.209 | **1.258×** | yes |
| codex | gpt-5.6-sol | 24 | n/a | −0.25 | — | 0.394 | 0.273 | **0.906×** | **no** |

What each column means:

| column | meaning |
|---|---|
| **loop_decay** | the slope of findings per round. −1.25 means about 1.25 fewer findings each round |
| **churn_dries** | did the mean churn of the second half fall below 0.7× the first half (true/false) |
| **churn_ratio** | that ratio itself, kept alongside the boolean for when it lands near the threshold |
| **decline rate** | the share of handed-over findings the fixer refused to apply, with a stated reason |
| **loc_direction** | final round's line count ÷ starting code. Above 1 it grew, below 1 it shrank |
| **tools blockable** | can that CLI actually disable the model's tools. A model that cannot be muzzled is a confound |

`churn` is the number of lines added and deleted in a round — how much was touched, not a
quality measure.

### Result 1 — the loop grows or shrinks the code, and the direction is a property of the model

```text
claude   1.258×    the code grows each round
codex    0.906×    the code shrinks as findings are applied
```

The strongest cross-model result in this bench. The two directions were measured independently
and match the same split observed on other tasks. **This is what decides how long a loop can
safely run.**

### Result 2 — churn convergence is not a usable stop rule across models

The intuition *"churn falls to zero, so stop there"* held in neither model, and it failed for
different reasons in each.

```text
claude   L1 [90, 100, 107,  65, 51]   ratio 0.611
         L2 [101, 82, 101, 101, 33]   ratio 0.732
         L3 [106, 69,  82,  51, 75]   ratio 0.720
         verdict: does not converge (splits 1:2)

codex    L1 [54, 13]                  2 points — too short to judge
         L2 [22, 20, 3, 15, 5]        ratio 0.476
         L3 [49, 18, 18, 3]           ratio 0.313
         verdict: not measurable (only 2 of 3 loops usable)
```

Two things follow.

**claude's three ratios, 0.611 to 0.732, straddle the 0.7 threshold.** Pick a single loop and it
can fall either side. So this trait is **only judged with three loops or more**, and the
continuous `churn_ratio` is read alongside the boolean.

**codex's loops end before the series is long enough.** The accurate statement is not *"codex
dries up quickly"* but *"codex does not run long enough for this to be measured"* — its loops
reached zero findings at rounds 3 and 5. Those are different statements, and the second is the
true one.

### Result 3 — the fixer declines a fifth to a quarter of what it is handed

```text
claude   0.209   (32 / 153)
codex    0.273   ( 9 /  33)
```

The refusals cite the contract. The fixer is the last gate before a review finding becomes a
code change, and it is not a rubber stamp.

### Result 4 — findings decay slowly, and in one model never reach zero

```text
claude   13 → 9 → 9 → 9 → 8      slope −1.25, still 8 at round 5
codex     4 → 4 → 4 → 3 → 3      slope −0.25, but the loop ends early at zero
```

### The prescription generated from these traits

`bench prescribe` carries measured traits into harness settings. The bracket is the strength of
the evidence: `***` reproduced across two or more models, `**` measured once, `*` judgement.

```text
claude   [**]  round_cap      cap the rounds — churn does not converge
         [**]  churn_gate     do not use churn convergence as a stop rule
         [***] loop_budget    keep the loop short — this model grows the code each round

codex    [*]   churn_gate     no basis for a churn stop rule — cap by rounds instead
         [***] loop_budget    the loop may run longer — this model does not grow the code
         [*]   comparability  not directly comparable — its tools cannot be disabled
```

---

## 3. What this bench does not measure

`finds_per_call` (real defects found per call) and `verbosity_shift` (how the finding count
changes when the repository is opened) are **tier-2 traits** — tier-2 meaning a real codebase
where a human adjudicates which findings are real.

The first needs an adjudicated defect set, and tier-1's `v0` is a verified-correct
implementation with no defects to adjudicate. The second needs a contrast between repo access
and none, and the tier-1 tasks are single files with nothing to contrast.

So the strongest result of the wider study this bench derives from — *give reviewers repository
access and the false positives disappear* — is **not re-confirmed by the tier-1 runs.**
Read it with [`../LIMITS.md`](../LIMITS.md).

## 4. Adding a task

```text
tasks/<slug>/SPEC.md              the human-readable contract
tasks/<slug>/test_acceptance.py   the frozen suite — this is the oracle
tasks/<slug>/reference.py         (optional) a known-good implementation
```

Then register it with `Task(slug, module_name, n_ac, has_reference)`. Before any number from
that task can be quoted, `oracle.verify()` must pass.
