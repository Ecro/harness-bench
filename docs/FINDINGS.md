# Findings

[한국어](FINDINGS.ko.md) · long-form (Korean): [`STUDY-ko-rewrite.md`](STUDY-ko-rewrite.md)

Everything measured in the study this benchmark derives from, and in the benchmark itself.
Numbers are stated with the tier that produced them.

```
tier-1   contract-as-oracle, no human adjudication, reproducible by anyone
tier-2   real firmware module, defects adjudicated by the author — case study, not a claim
```

Read with [`LIMITS.md`](LIMITS.md). Only three statements here have been reproduced more
than once; the rest were observed once.

---

## 1. Repeated review and the fix loop are different activities

**The single strongest result.** Reproduced under three separate conditions.

| | gain | cost |
|---|---|---|
| **review only, repeated** | real-defect coverage 34% → 61% → 76% | none — the code never changes |
| **review→fix loop, repeated** | **zero.** 40 rounds, compliance unchanged | code +24% to +152%; broken tests in one arm |

The coverage gain lives entirely on the review side; the code risk lives entirely on the fix
side. Combining them into one cycle maximises risk per unit of gain — which is what most
auto-fix harnesses do.

> **Review many times. Fix once.**

## 2. One review pass sees about a third of the real defects

tier-2, 10 independent reviews of a 359-line firmware module, code held constant:

```
findings per run:   6  6  5  7  5  7  9  5  4  7     range 4-9, a 2.25x spread
61 findings  →  14 distinct defects
```

Grouping was validated: three shuffled runs produced the same partition (ARI 1.000), and a
different vendor's model grouping the same 61 findings produced the same 14.

```
                 all 14 groups     the 10 adjudicated real
1 review pass        44%                   34%
3 passes             71%                   61%
5 passes             83%                   76%
```

Some defects surface once in ten runs.

## 3. In a single-file scope, the most-reported finding is the most suspect

Of the 14 distinct defects, **4 were false** — and they were the most frequently reported.

```
false positives, mean detection frequency   6.8 / 10     (8, 7, 7, 5)
true defects,    mean detection frequency   3.4 / 10     (9, 7, 6, 3, 3, 2, 1, 1, 1, 1)
```

All four were claims that can only be settled outside the file — a caller's ordering, an
initialisation path, which thread actually runs a function. The reviewer had one file and no
way to check.

> Consensus arises not because a finding is true, but because the reviewers **share the same
> missing information.** Give them the means to check and the correlation inverts.

This matters in practice: most AI review harnesses supply the diff only, then pass whatever
several reviewers agree on. On this data that combination **preferentially selects false
positives.**

## 4. Repository access removes them — in both models

Changing one paragraph of the prompt (*"you have no repository"* → *"the source tree is
mounted read-only; check callers and headers before you claim a defect"*):

| | findings | distinct | true | false | precision |
|---|---|---|---|---|---|
| file only | 61 | 14 | 10 | **4** | 71% |
| repo open (model A) | 30 | 7 | 7 | **0** | **100%** |
| repo open (model B) | 37 | — | — | **0** | — |

Pooled clustering of all three arms: **ARI 0.978**, control frequency profile reproduced
exactly. **Both models dropped the same four false positives.** This is the strongest
cross-model result in the study.

The two models reach that precision by opposite routes:

```
model A   61 → 30 findings  (−51%)   says less
model B   27 → 37 findings  (+37%)   says more
```

They also see different things. Each found 4 of the 10 adjudicated real defects; their union
was 5. One defect was found by A in 1 run of 10 and by B in **10 of 10**.

### The cost is recall

```
             precision     recall
file only       71%          77%
repo open      100%          54%
```

The filter that removes false positives also removes faint true ones — low-reachability
defects, observability complaints, compiler-ordering arguments. Running both conditions and
taking the union recovers 13/13 for 20 calls.

## 5. A famous-looking regression was an artefact of the condition

In the file-only loop, **four independent runs broke exactly the same four tests.** The
finding behind it was later adjudicated **false**, disappeared entirely once the repo was
opened, and did not reproduce in a repo-access loop:

```
                          file only      repo open
completed rounds              15             10
RED rounds                 12 / 15        6 / 10
those four tests           all four        never
```

The guard the model added was correct in isolation and unreachable in production — the
"regression" was four tests pinning a state the system cannot enter.

> When a fix repeatedly breaks the same tests, check whether those tests pin a **reachable**
> state before concluding the model introduced a defect.

## 6. Reviewers report findings on code that is already correct

tier-1, a Python module passing 23/23 acceptance tests derived from a 19-criteria contract:

```
model A, bare prompt          5, 5, 6, 8, 7, 8, 6            median  6
model A, structured prompt   11, 11, 12, 11, 12, 12, 11      median 12
model B, bare prompt          1, 1, 1, 1, 0, 1, 1            median  1
model B, structured prompt    1, 1, 2, 2, 3, 4, 5            median  2
```

Fourteen of fifteen passes returned findings. Across **40 loop rounds and 189 applied
findings, contract compliance never broke** — and the benchmark's own later run reproduced
this: 54 rounds, 23/23 in every one.

**Compliance therefore discriminates nothing.** Everything that separates the arms is
elsewhere.

## 7. Silence is not completion

```
model B, bare         1 → 1 → 0 → 0 → 0     silent from round 3
model B, structured   6 → 3 → 2 → 1 → 1     decays sharply
model A, bare         5 → 6 → 7 → 6 → 7     no decay
model A, structured  12 → 11 → 10 → 11 → 9  no decay
```

The silent arm saw **2 findings in 5 rounds**. On the same code, its structured counterpart
kept surfacing clock-failure, process-control and wedge cases. A model that stops is not
necessarily a model that finished.

## 8. The contract pins where the loop may move

Operational definition: *an answer is defined at a point if perturbing it is killed by the
frozen suite.*

```
120 mutation points
  104  pinned by the contract (87%)
   16  survive  →  9 observationally equivalent
                   4 suite holes (the suite fails to check the reverse direction)
                   3 genuinely free — one region

47 loop rounds moved exactly one observable behaviour, in that one free region.
```

**Where the model moved and where the contract was silent match one-to-one.**

Corollary: when a loop reverses the same decision twice, the defect is in the specification,
not the code. In one arm rounds 3 and 4 wrote opposite justifications for opposite choices,
both persuasive, both compliant.

## 9. Oscillation comes from absent convention, not from a sparse contract

A second task covered the same surface with **8** criteria instead of 19, with eight free
regions predicted and registered before implementation.

```
four independent implementations (three from model A, one from model B)
  all pass 8/8
  differential testing across all six pairs: 0/400 — behaviourally identical
  sizes 54 / 101 / 133 / 138 lines — a 2.5x spread with identical behaviour

a 10-round loop applied 104 findings and moved 0/400
```

The harness was verified against planted divergences (95/400, 400/400, 369/400 — all caught).

But where convention is weak, they split:

```
strong convention (TTL boundary, LRU refresh, len semantics)   4 implementations agree
weak convention  (type-error handling)                          4 implementations, 3 answers
```

> A sparse contract does not create drift. **Absent convention does.**

## 10. Splitting the reviewer by category beats repeating it

At equal call budget, tier-1:

| arm | calls | distinct findings | raw findings | duplication |
|---|---|---|---|---|
| single structured | 1 | 11.0 | 11.6 | 1.0× |
| same prompt, 6 calls | 6 | 19.7 | 69.3 | 3.6× |
| **six category prompts** | 6 | **30.0** | **54.7** | 1.8× |

**+52% distinct findings and 21% fewer raw findings.** The gain is confined to robustness,
naming and style — the areas a generalist truncates under an "in order of importance" cap.

Adjudicating 39 of those findings blind (fan-out-exclusive mixed with common ones):

```
REAL 12 (31%)   STYLE 27 (69%)   WRONG 0
```

Nothing was factually wrong about the code. Most of it was naming, comments and structure.

**This did not transfer.** On the firmware task at equal budget, category fan-out gained
nothing (recall 43% vs 50% for a single reviewer) — its lenses overlapped, so the split spent
budget without adding coverage. And a lens told to look only at module-internal state
reintroduced one of the false positives that repository access had removed.

> Fan-out helps when the axes genuinely separate. Verify that before spending on it.

## 11. Re-review after a fix is decided by churn, not by round count

Because one pass sees only part of the field, a second batch produces "new" findings even
with the code unchanged. The null distribution was built exhaustively — all 1680 disjoint
triples within the existing pool:

```
null (code unchanged)   median 11%,  range 0-31%
after a merged fix      77% / 89% / 63%      100th percentile
```

Also: **74–80% of the findings handed over actually disappear.** Fixing once works.

The driver is not reviewer diligence:

```
fix churn (lines)   143   87   82   36   28   36
true-new rate       82%   62%   43%  50%  40%  20%      r = 0.837 (n=6)
```

> Re-review is not "has the review converged". It is "have I looked at the code I just wrote".
> If the fix rewrote half the file, that is a **first** review of new code.

## 12. Compliance is blind; size and complexity are not

Ten arms, 47 rounds, all 19/19 compliant. Same data:

```
Cognitive Complexity   structured −17%   ·   bare +26%   ·   no contract +58%
worst function          6.3              ·      10.3      ·        15
```

Prompt and contract interact rather than adding:

```
worst (bare, no contract)    37.0
contract only            →   33.3   (−3.7)
prompt only              →   32.3   (−4.7)
both                     →   24.0  (−13.0)      3.7 + 4.7 = 8.4  <  13.0
```

Churn is a **cost** signal, not a quality one: the highest-churn arm produced the smallest,
simplest final code.

## 13. "Contract" is two things, and they do different work

The variable called *contract* bundled two: **B**, "the public surface is fixed, reject
out-of-scope findings", and **C**, the specification document itself. Separated:

| given to the fixer | rejection rate | final LOC | cumulative churn |
|---|---|---|---|
| A — do not touch what wasn't asked | 26% | 254 | 195 |
| A+B — ...and the surface is fixed | **50%** | 237 | **136** |
| A+B+C — ...and here is the spec | 26% | **202** | 191 |

LOC forms a ladder; rejection does not. Told a surface is fixed with **no document to check
against**, a fixer rejects everything ambiguous — citing the code's own docstrings rather than
criteria (0 of 17 rejections cited a criterion, versus 7 of 12 with the document).

> **B suppresses growth. C calibrates judgement.** One line of scope instruction buys −7% LOC
> and −30% churn without a specification; the specification buys accuracy on top.

## 14. Reading tests, without permission to edit them, replaces widening the oracle

When reviewer and fixer both had repository access but the test harness linked only one
module, a *correct* cross-module fix broke the build for an entire loop — a third failure
category beyond "the code broke" and "the tests broke": **the oracle's scope was narrower than
the review's.**

Mounting the test directory read-only removed it. The fixer declined instead:

> *"the fix here would require editing a test"* · *"the tests pin the effective ring capacity"*
> · *"not fixable inside this file — known only to sensor.c"*

Build failures went from every round of a loop to zero, without touching the build system.
The cost is honest: roughly a third of those declines are *"real but out of scope"* — deferred,
not fixed.

## 15. Budget: mixing models beats repeating one

Exhaustive over all subsets of the existing runs — no additional calls. Denominator is the 10
adjudicated real defects; entries are (true found / false found):

| calls | file only | repo, model A | repo, model B | **mixed** |
|---|---|---|---|---|
| 1 | 3.40 / **2.70** | 1.40 / 0 | 2.70 / 0 | 2.70 / 0 |
| 2 | 5.04 / **3.62** | 2.09 / 0 | 3.07 / 0 | **3.18** / 0 |
| 3 | 6.11 / **3.90** | 2.54 / 0 | 3.27 / 0 | **3.57** / 0 |
| 4 | 6.93 / **3.98** | 2.90 / 0 | 3.40 / 0 | **3.90** / 0 |
| 6 | 8.20 / **4.00** | 3.43 / 0 | 3.60 / 0 | **4.43** / 0 |

**Three mixed calls (3.57) beat six same-model calls (3.43).** Mixing wins at every k ≥ 2.

File-only finds more per call — and drags along false positives that saturate at 4 by the
fifth call. That budget is not saved; it is **moved to whoever triages**.

*(The denominator excludes defects only the repo-open arms found, so this table is biased
against repository access, not for it.)*

## 16. What the benchmark measures on its own tasks

tier-1, `retry_policy`, two models, three loops each, 2026-08-21:

| model | calls | cost | loop_decay | churn | rejection | code size | tools blockable |
|---|---|---|---|---|---|---|---|
| A | 30 | $15.74 | −1.25 | does not converge (split 1:2) | 0.209 | **1.258×** | yes |
| B | 24 | n/a | −0.25 | not measurable (loops end early) | 0.273 | **0.906×** | **no** |

**Loop code-size direction is a model property** — one grows the code every round, the other
shrinks it while applying findings. It decides how long a loop may safely run, and it is the
only trait here graded `***`.

**Churn convergence is not a usable stop rule.** For one model the three loop ratios
(0.611 / 0.732 / 0.720) straddle the 0.7 threshold, so a single loop lands on either side by
chance. For the other the loops end too early to measure at all — *not measurable* is a
different statement from *does not converge*.
