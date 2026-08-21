# Methods — how each number was obtained, and how the instrument was checked

[한국어](METHODS.ko.md)

This document is about the **instruments**, not the results. Every device here is validated
before it is used. A device that has not been shown to respond to the thing it claims to
measure — and to stay silent otherwise — produces numbers, not evidence.

```text
    subject               isolation            instrument            validation
  ──────────────────────────────────────────────────────────────────────────────────
  frozen source    →   bwrap namespace   →   model call        →   two-way canary
  findings         →   provenance-blind  →   clustering        →   ARI gate + cross-vendor
  candidate code   →   temp directory    →   acceptance suite  →   three-way oracle check
  two versions     →   seeded scenarios  →   differential replay →  planted divergence
  one version      →   AST perturbation  →   mutation testing  →   the suite must kill it
  N runs           →   exhaustive subsets →  coverage curve    →   degenerate-case check
  observed effect  →   disjoint triples  →   null distribution →   all 1680 pairs
```

## The vocabulary that recurs

| term | meaning |
|---|---|
| **oracle** | whatever decides that a result is right or wrong. Here, the acceptance suite |
| **frozen** | fixed before any implementation exists and never edited afterwards — comments and translations included |
| **acceptance suite** | the tests that check the behaviour the specification guarantees |
| **finding** | one item a reviewer reported |
| **arm** | a set of runs with one condition changed — "the structured-prompt arm", for instance |
| **`UNQUOTABLE`** | the return value when a gate fails: it **withholds the number** rather than qualifying it |
| **degraded** | a marker that the value could not be measured, kept distinct from a silent zero |
| **malformed** | a response that would not parse despite a structured-output instruction |

---

## 1. Isolation — the invariant that holds it up is a negative one

Each call is a fresh process inside a `bwrap --unshare-all` namespace. bwrap builds a new
filesystem and process view and runs the command inside it, so **a path that was not mounted
into the namespace does not exist for that process.**

That is why the invariant is stated as an absence: **the target repository is never bound into
the namespace.** The specification, the answer key, the previous findings — an absolute path to
any of them simply does not resolve, whether or not the CLI honours its own tool-restriction
flags.

Flags are not a boundary. One CLI's `-s read-only` is a shell-execution policy that *permits*
reads, and it has no tool switch at all. Sandboxing only that CLI would make read capability
asymmetric between models and confound it with model identity, so the namespace is applied
identically to both.

Prompts arrive on **stdin**, not in the command line (argv). Large inputs containing quotes,
backticks and `$` get mangled by the shell or exceed the argument-length limit (ARG_MAX), and
**silently corrupted input is the worst failure available here** — every other number is
measured against it.

The target code sits **first**, at a fixed offset, with the instructions after it, so that the
code occupies the same token positions in every arm no matter what instruction follows.

### Validation: the two-way canary

*"The model could not read the answer key"* proves nothing on its own. A broken probe returns
exactly what perfect isolation returns — no tools attached, prompt undelivered, CLI dead, a
permission prompt auto-denied; all of them look like "could not read it".

So every isolation claim carries both directions **within the same call**.

```text
POS   something that should be reachable, and is      (a planted marker, a system file)
NEG   something that must not be reachable, and is not (this repository)
```

A `Canary` missing either leg raises at construction, and `require_pass()` has no override.
A failure on the POS side is reported as a **broken probe**, not as isolation.

The POS leg must ask only for **what that adapter can actually do**. Asking a read-only adapter
to prove isolation by writing produces a failure that would be misread as a model difference.

The canary's raw response is always saved. A failed canary is the evidence.

## 2. The acceptance oracle — validated three ways

The contract is the oracle: a specification, a suite derived from it before any implementation
existed, and a reference implementation used only to show the suite is satisfiable.

A suite that has never been run cannot be an oracle. CI runs three checks on every push, and no
number from that task may be quoted until they pass.

```text
reference passes           the known-good implementation is green         23/23
floor on import failure    a module that cannot import scores 0,          0 passed
                           not "everything passed"
one guarantee removed      delete a guard clause and the suite notices    3 failures
```

The third is the point. A suite that stays green after a guarantee is deleted **is not measuring
that guarantee.**

The second is not trivial either: if a module that cannot even be imported comes back green as
"0 tests run, 0 failures", that suite will pass anything.

The suite is **frozen** — written from the specification alone, before the implementation, and
never edited since. That freeze is the only defence against *"the tests were fitted to the
implementation"*.

## 3. Clustering the findings — three times, shuffled, behind a gate

Ten reviews describe one defect in ten different sentences. Frequency, duplication and coverage
mean nothing until findings that name the same defect are grouped, and the grouping is done by
a model.

Two properties are enforced on that grouping.

**Provenance-blind.** The clusterer sees opaque positions, locators and bodies only. It never
sees which model, which run or which arm produced a finding. Otherwise the cluster boundaries
can be drawn — even unconsciously — in a way that favours one arm, and every later comparison
inherits it.

**Shuffle the order every run, and record the seed.** With identical input order the three runs
correlate through *presentation*, and the gate ends up measuring **prompt determinism** rather
than clustering stability — passing for the wrong reason.

The three runs are compared with the Adjusted Rand Index (ARI), which scores how far two
partitions agree: 1.0 is identical, 0 is no better than random. The partition closest to the
other two (the medoid) is used downstream.

### The gate refuses to release a number

Below threshold the result is the string `UNQUOTABLE`, not a number. **A number that leaves with
a caveat gets quoted without it.**

It bit once: an arm came back at **ARI 0.781**, and that arm's distinct-defect count is quoted
nowhere in the study.

### Cross-vendor validation of the instrument itself

Three runs of one model agreeing proves consistency, not correctness — models sharing a
systematic bias can agree perfectly and be wrong together. So the same 61 findings were given to
**a different vendor's model** to cluster, and the same 14 groups came back.

Measured agreement where it is quoted: **ARI 1.000** (single-arm pool), **0.978** (128 findings
across three arms), **0.963** (193 findings).

## 4. The free-space denominator — measured, not asserted

"The loop moved one behaviour" means nothing without knowing **how many places there were to
move.** That denominator was measured with this definition:

> **If deliberately altering a point makes the frozen suite fail, the answer at that point is
> already fixed by the contract.**

The reference implementation's conditions and operators are altered one at a time, at the AST
level, and each altered version — a mutant — is run against the frozen suite.

```text
120 mutation points
  104  killed by the suite — fixed by the contract       (87%)
   16  survive, classified by hand:
         9  observationally equivalent (not even the differential test separates them)
         4  gaps in the suite — it never checks the opposite direction
         3  genuinely free, forming a single region
```

Those four gaps are a finding about **the oracle**, not about any model. Changing `if x < 0` to
`if x < 1` leaves all 23 tests passing, because the criterion says only *what must be rejected*
and never checks *what must be accepted* — so code that rejects a valid configuration passes.

Across 47 loop rounds, observable behaviour moved in exactly one place, inside that single free
region: where the model moved and where the contract was silent line up one to one.

## 5. Differential testing — and testing the harness first

A differential test **replays identical inputs** against two versions and looks for a divergence
in what is observable. Here, 300 seeded operation scenarios are replayed against each version
and the traces compared. It is possible because the subject is fully deterministic — time, sleep
and randomness are all injected from outside.

Before trusting the harness, it is validated with planted changes.

```text
v0 against v0                          0/300     no false positives
jitter multiplied before the cap       39/300    real differences are caught
comments / exception messages only     0/300     style changes are not caught
```

The second task ran the same check by deliberately flipping choices in the free region —
**95/400, 400/400, 369/400**, all caught.

Divergences are reduced to **signatures**, so that "how many distinct behaviour changes" is a
count rather than an impression of how many scenarios differed.

## 6. The chance baseline — enumerated, not estimated

Because one review never sees everything, a second batch produces "new" findings even when the
code has not changed. Quoting a novelty rate without that baseline measures sampling, not the
fix.

That baseline is the null distribution — how far the value ranges when there is no effect at
all. It was built by enumerating **all 1680 pairs of disjoint triples** within nine existing
reviews of unchanged code. No extra model calls.

```text
null (code unchanged)     median 11%, range 0–31%
after the merged fix      77% / 89% / 63%      the 100th percentile of the null
```

## 7. The budget curve — exhaustive over subsets already paid for

Given N independent runs, "how much would k calls have found" needs no estimate. It is the
average over every way of choosing k of the N, and it costs nothing extra.

The implementation is checked against degenerate cases before it is used: a pool where every run
finds the same set must give a flat curve, and a pool of disjoint runs must rise linearly.

The mixed curve enumerates every split of k across the two arms, reports the best, and records
which split produced it.

## 8. Complexity — a proxy chosen on evidence, not familiarity

Cyclomatic complexity was **deliberately excluded.** Its correlation with LOC is r ≈ 0.85–0.87,
so it adds almost nothing on top of size. Measured in this data it came to r = 0.807.

Cognitive Complexity was used instead: it measures how much nesting and branching a reader has
to hold in their head, and its correlation with *comprehension time* has been measured
empirically. It is still a proxy, and it is reported as one.

It is never reported alone. Line count, cumulative churn, surviving mutants and acceptance
compliance go out beside it. Compliance was identical across all ten arms and 47 rounds, and
**that is itself a finding** — the metric everyone reaches for first discriminates nothing.

Surviving mutants are reported as an **absolute count**, not a ratio. The ratio moved only
between 0.83 and 0.90 across every arm and supported no claim; the count separated one arm
cleanly (16 → 24).

## 9. Prompt variants — derived by script, verified by diff

Writing six category prompts by hand lets vocabulary, emphasis and output rules drift, and that
drift then reads as the effect of the arm. So variants are derived from a base by script, and
the diff must show **exactly one axis** changing.

What stays byte-identical, because each would otherwise be a confound:

- the output schema and the per-call cap on findings
- the permissive clause *"an empty result is a valid answer"* — delete it and a specialist
  reviewer is under pressure to say **something** in its area, at which point that arm's higher
  finding count is an artefact of the prompt rather than a measurement
- the instruction to point at specific lines

The derivation script checks that only one block changed, and every result records the prompt's
SHA-256.

## 10. Adjudication — blinded, with an internal control

Where human judgement is needed for *"is this finding real"*, the procedure is fixed in advance.

- findings exclusive to one arm are **mixed with findings both arms produced** and shuffled, so
  the adjudicator cannot tell which arm anything came from
- the shared set then acts as an internal control: if the exclusive set is no better, the
  contrast shows it
- the answer key is written to a separate file and not opened until the verdicts are recorded

Adjudication remains the weakest link in this work, and it is marked as such everywhere its
numbers appear, because the adjudicator was the author of the study. That is exactly why the
tier-1 tasks exist: there, no adjudication is needed at all.

## 11. Pre-registration, and no retries

Predictions are frozen and hashed before the data is seen. A prediction without a
**falsification condition** — what result would show it wrong — is rejected at construction. A
frozen file that is edited afterwards fails to load. A run without pre-registration is branded
`exploratory: true` in its result and in the ledger.

Of the five predictions frozen in this study, **two failed**, and those two were more
informative than the three that held. Neither would have survived being written up afterwards.

**No call is ever retried.** `call()` has no retry parameter and a test enforces its absence.
Calling again until a response parses selects for well-behaved samples, which biases the very
variance being measured. Failed and unparseable calls are recorded and kept, and if one ended a
loop early, the loop is not restarted — it is **reported as having ended early.**

---

## What the instruments refuse to do

| situation | what comes out |
|---|---|
| clustering does not reproduce | `UNQUOTABLE`. Not a number with a footnote |
| fewer than three loops | `None`. Not a two-out-of-three verdict |
| a series with fewer than four points | no ratio for that loop |
| the CLI reports no usage | `degraded`. Not a silent zero |
| a canary POS leg fails | an exception. The run does not proceed |
| a prescription rule has no evidence grade | it does not render |

Each is a place where a number could have been produced, and would have been wrong.
