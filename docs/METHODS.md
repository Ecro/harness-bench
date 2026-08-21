# Methods — how each number was obtained, and how the instrument was checked

Every instrument here is validated before it is used. A measurement device that has not been
shown to respond to the thing it claims to measure — and to stay silent otherwise — produces
numbers, not evidence.

```
    subject               isolation            instrument            validation
  ──────────────────────────────────────────────────────────────────────────────────
  frozen source    →   bwrap namespace   →   model call         →   two-way canary
  findings         →   provenance-blind  →   clustering         →   ARI gate + cross-vendor
  candidate code   →   temp dir          →   acceptance suite   →   3-check oracle verify
  two revisions    →   seeded scenarios  →   differential replay →  planted divergences
  one revision     →   AST perturbation  →   mutation testing   →   suite must kill them
  N runs           →   exhaustive subsets →  coverage curve     →   degenerate-case checks
  observed effect  →   disjoint triples  →   null distribution  →   1680 exhaustive pairs
```

---

## 1. Isolation — the load-bearing invariant is negative

Each call is one fresh process inside a `bwrap --unshare-all` namespace. The invariant is
stated as an absence: **the subject repository is never bound into the namespace**, so an
absolute-path read of the specification, the answer key or prior findings cannot resolve —
regardless of which tool-restricting flags the CLI does or does not honour.

This matters because flags are not a boundary. One CLI's `-s read-only` is a shell-exec
sandbox policy that *permits* reads; it has no tool switch at all. Sandboxing only that CLI
would leave read capability asymmetric between models and therefore confounded with model
identity, so the namespace is applied to both.

The prompt is delivered on **stdin**, never argv: a large subject containing quotes, backticks
or `$` would be mangled or exceed ARG_MAX, and a silently corrupted subject is the worst
failure available here, because every other number is measured against it.

The subject is placed **first** at a fixed offset with the instruction after it, so the code
occupies identical token positions in every arm regardless of which instruction follows.

### Validation: the two-way canary

*"The model could not read the answer key"* proves nothing. A broken probe returns the same
answer as perfect isolation: no tools attached, prompt undelivered, CLI dead, permission
prompt auto-denied.

So every isolation claim carries both directions **in the same invocation**:

```
POS   a target that MUST be reachable, and is       (a planted marker; a system file)
NEG   a target that MUST NOT be, and isn't          (this repository)
```

A `Canary` missing either leg raises at construction; `require_pass()` has no override. A
POS-side failure is reported as a broken probe, not as isolation.

The POS leg must also ask only for something **that adapter can actually do** — a read-only
adapter cannot demonstrate isolation by writing, and reading that failure as a model
difference would be wrong.

Raw canary responses are always persisted. A failed canary is the evidence.

## 2. The acceptance oracle — verified in three directions

The contract is the oracle: a specification, a suite derived from it before any implementation
existed, and a reference implementation used only to check the suite is satisfiable.

A suite that has never been exercised cannot be an oracle. Three checks, run in CI on every
push, before any number from a task is quotable:

```
reference passes             the known-good implementation is green          23/23
import failure floors        an unimportable module scores 0, not "all pass"  0 passed
single-guarantee removal     delete one guard clause, the suite must notice   3 tests fail
```

The third is the one that matters. A suite that stays green after a guarantee is deleted is
not measuring that guarantee.

The suite is **frozen**: authored from the specification before implementation, never edited
afterwards. That freeze is the only defence against *"the tests were fitted to the
implementation"*, and it extends to comments and to translating them.

## 3. Grouping findings — three runs, shuffled, gated

Ten reviews describe one defect in ten different sentences. Frequency, overlap and coverage
mean nothing until they are grouped, and the grouping is done by a model.

Two properties are enforced:

**Provenance-blind.** The clusterer sees an opaque position, a location and the text — never
which model, run or arm produced it. Otherwise cluster boundaries could be drawn, however
unconsciously, in a way that flatters one arm, and every downstream comparison inherits it.

**Shuffled per run, seeded and recorded.** Identical input order would correlate the runs
through presentation rather than through the underlying grouping, and the gate would then
measure prompt determinism instead of clustering stability — passing for the wrong reason.

Three runs, compared by Adjusted Rand Index, medoid taken as the downstream partition.

### The gate refuses to produce a number

Below threshold the result is not a number, it is the string `UNQUOTABLE`. A number carried
with a caveat gets cited without the caveat.

This has bitten in practice: one arm clustered at **ARI 0.781** and its distinct-defect count
was therefore never cited anywhere in the study.

### Cross-vendor validation of the instrument

Three runs of one model agreeing proves consistency, not correctness — they can share a
systematic bias and agree perfectly while being wrong. So the same 61 findings were grouped by
a **different vendor's model**, which produced the same 14 groups.

Observed agreement where it was cited: **ARI 1.000** (single-arm pool), **0.978** (three-arm,
128 findings), **0.963** (193 findings).

## 4. The free-space denominator — measured, not asserted

"The loop moved one behaviour" is meaningless without knowing how many it *could* have moved.
Operational definition:

> **An answer is defined at a point if perturbing that point is killed by the frozen suite.**

Mutation testing over the reference implementation, one AST perturbation at a time, each
mutant run against the frozen suite:

```
120 mutation points
  104  killed by the suite -- the contract pins them          (87%)
   16  survive, and are then classified by hand:
         9  observationally equivalent (differential testing cannot distinguish them)
         4  suite holes -- the suite fails to check the reverse direction
         3  genuinely free, forming one region
```

The 4 suite holes are a finding about the oracle, not about the model: `if x < 0` mutated to
`if x < 1` passes all 23 tests while rejecting valid configurations, because the criterion
states what must be rejected and never checks what must be accepted.

47 loop rounds moved exactly one observable behaviour, inside that single free region — a
one-to-one match between where the model moved and where the contract was silent.

## 5. Differential testing — and the harness is tested first

Two revisions are compared by replaying **300 seeded operation scenarios** against both and
diffing the observable traces. This is possible only because the subject is fully
deterministic: time, sleep and randomness are all injected.

The harness itself is validated against planted changes before it is trusted:

```
v0 against v0                              0/300     no false positives
jitter multiplied before the cap           39/300    real differences ARE caught
comment-only / message-only edits           0/300    style changes are NOT caught
```

On the second task the same check was run against deliberately inverted free-region choices:
**95/400, 400/400, 369/400** — all caught.

Divergences are then reduced to **signatures** so that "how many distinct behaviour changes"
is a count, not an impression.

## 6. Chance baselines — computed exhaustively, not estimated

Because one review pass sees only part of the field, a second batch produces "new" findings
even with the code unchanged. Quoting a new-finding rate without that baseline measures the
sampling, not the fix.

The null distribution was built by enumerating **all 1680 disjoint triples** within the
existing pool of nine reviews of unchanged code — no additional model calls:

```
null (code unchanged)     median 11%, range 0-31%
after a merged fix        77% / 89% / 63%      100th percentile of the null
```

## 7. Budget curves — exhaustive over subsets already paid for

"How much would k calls have found?" is not an estimate when N independent runs exist. It is
the mean over all C(N,k) subsets, and it costs nothing further.

The implementation is checked against degenerate cases before use: pools where every run finds
the same set must give a constant, and pools where runs are disjoint must scale linearly.

Mixed-model curves enumerate every split of k between the two arms and report the best,
alongside the split that produced it.

## 8. Complexity — a proxy chosen on evidence, not familiarity

Cyclomatic complexity was **deliberately excluded**: it correlates with lines of code at
r ≈ 0.85–0.87, so it adds almost nothing on top of size. Measured on this data, r = 0.807.

Cognitive Complexity was used instead, because its correlation with *comprehension time* has
been measured empirically. It is still a proxy, and is reported as one.

Reported alongside, never alone: line count, cumulative churn, surviving mutant count, and
acceptance-suite compliance. Compliance was identical across ten arms and 47 rounds, which is
itself the finding — the metric everyone reaches for discriminates nothing.

Absolute surviving-mutant counts are preferred to ratios: the ratio moved 0.83–0.90 across all
arms and supports no claim, while the absolute count separated one arm cleanly (16 → 24).

## 9. Prompt variants — derived by script, diff-checked

Hand-writing six category prompts makes vocabulary, emphasis and output rules drift, and that
drift is then read as the arm's effect. Variants are derived from a base by script, and the
diff must show **exactly one axis** changing.

What stays byte-identical, because each is a confound:

- the output schema and the per-call finding cap
- the permissive clause *"an empty result is a valid answer"* — removing it pressures a
  specialist into saying **something** in its area, and the arm's higher finding count
  becomes an artefact of the prompt rather than a measurement
- the instruction to cite a specific line

The derivation script self-checks that only one block changed, and every result records the
prompt SHA-256.

## 10. Adjudication — blind, with an internal control

Where "is this finding real" requires judgement, the procedure is fixed in advance:

- exclusive findings are **mixed with findings both arms produced** and the order shuffled, so
  the adjudicator cannot tell which arm produced which;
- the common set functions as an internal control — if the exclusive set is not better, the
  difference shows up against it;
- the answer key is written to a separate file and not opened until the verdicts are recorded.

Adjudication remains the weakest link in this work, and is labelled as such wherever its
numbers appear: the adjudicator was the study's author. Tier-1 tasks exist precisely because
they need no adjudication at all.

## 11. Pre-registration and the no-retry rule

Predictions are frozen before data, hashed, and refused at construction if they carry no
falsification condition. An edited frozen file fails to load. Runs without a pre-registration
are branded `exploratory: true` in the result and the ledger.

Of five predictions frozen in this study, **two failed** — and both failures were more
informative than the successes. Neither would have survived post-hoc narration.

**No call is ever retried.** There is no retry parameter, and a test enforces its absence.
Retrying until a response is well-formed selects for well-behaved samples and biases exactly
the variance being measured. Failed and malformed calls are recorded and kept; where one ended
a loop early, the loop is reported as ending early rather than restarted.

---

## What the instruments refuse to do

| situation | what you get |
|---|---|
| clustering does not reproduce | `UNQUOTABLE`, not a number with a footnote |
| fewer than three loops | `None`, not a majority of two |
| fewer than four points in a series | no ratio for that loop |
| usage not reported by the CLI | `degraded`, never a silent zero |
| canary POS leg fails | a raised exception; the run does not proceed |
| a prescription rule has no evidence grade | it does not render |

Each of those is a case where a number could have been produced and would have been wrong.
