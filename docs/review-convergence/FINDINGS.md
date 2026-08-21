# Findings

[한국어](FINDINGS.ko.md) · long-form: [`STUDY.md`](STUDY.md)

Everything measured in the study this benchmark derives from, and in the benchmark itself.

```text
tier-1   contract and frozen tests decide; no human adjudication, reproducible by anyone
tier-2   a real firmware module; the defects were adjudicated by the author — a case study
```

Read this with [`../LIMITS.md`](../LIMITS.md). **Only three statements here were reproduced
across models or conditions**; the rest were observed once.

## Before you read — the vocabulary that recurs

| term | meaning |
|---|---|
| **finding** | one item a reviewer reported. Says nothing yet about whether it is real |
| **raw findings** | the total number reported, duplicates included — several reviewers naming the same problem count several times |
| **distinct findings** | the count after findings that name the same defect are clustered. The number of *kinds* a human has to read |
| **duplication** | raw ÷ distinct. 3.6× means the same thing was said 3.6 times on average |
| **false positive** | a finding reported as a defect that is not one |
| **bare prompt** | close to "review this code" and nothing more |
| **structured prompt** | prescribes what to look at, in what order, and in what output format |
| **file-only** | the reviewer is given the target file alone; the repository is removed at the filesystem level |
| **repo access** | the same reviewer, with the source tree mounted read-only. **repo A / B** are two models from different companies |
| **mixed** | calls split between two models instead of repeating one |
| **median** | the middle value when the runs are sorted — unmoved by a single outlier |
| **churn** | lines added and deleted in a round. *How much was touched*, not a quality measure |
| **decline rate** | the share of handed-over findings the fixer refused to apply, with a stated reason |
| **acceptance criterion / test** | one verifiable sentence carved out of what the spec guarantees, and the test that checks it |

---

## 1. Repeated review and the fix loop are different activities

**The strongest result.** The same direction appeared under three separate conditions.

| | gain | cost |
|---|---|---|
| **review only, repeated** | real-defect coverage 34% → 61% → 76% | none; the code never changes |
| **review→fix loop, repeated** | compliance, already perfect, held for 40 rounds | code +24–152%, broken tests in one condition |

The gain in finding defects came from repeating the review; the risk of changing the code came
from the fix side. Nothing in the data says that binding the two into one auto-fix loop is an
advantage.

> **Review many times, fix once.**

## 2. One review found about a third of the real defects

tier-2. A 359-line firmware module, reviewed 10 times independently with the code held fixed.

```text
findings per run:   6  6  5  7  5  7  9  5  4  7     range 4–9, a 2.25× spread
61 findings  →  14 distinct defects
```

Grouping findings that describe the same defect in different words was validated too.
Reshuffling the input and repeating it three times produced the same groups (**ARI 1.000**),
and a different vendor's model clustering the same findings produced the same 14.
ARI measures how far two clusterings agree; 1.0 means they are identical.

```text
                  all 14        the 10 adjudicated real
1 review            44%                  34%
3 reviews           71%                  61%
5 reviews           83%                  76%
```

Some defects surfaced in only one run out of ten.

## 3. Given a single file, the most frequently reported findings were the more suspect ones

Of the 14 distinct defects, **4 were false**, and those four were among the most frequently
reported.

```text
mean detection frequency, the false    6.8 / 10     (8, 7, 7, 5)
mean detection frequency, the real     3.4 / 10     (9, 7, 6, 3, 3, 2, 1, 1, 1, 1)
```

All four false ones were **decidable only with information outside the file** — the real call
order, the init path, which thread actually runs the function. The reviewer had no way to check
any of it.

> Reviewers may agree on a finding not because it is true but because **none of them could see
> the same information.**

So a harness that hands over a diff and auto-accepts whatever several reviewers agree on was,
in this data, selecting false positives first.

## 4. Opening the source tree removed the same false positives in both models

One paragraph of the prompt changed.

```text
file condition:  you have no other files and no repository
repo condition:  the source tree is readable read-only; check callers and headers
                 before claiming a defect
```

| | findings | distinct | real | false | precision |
|---|---|---|---|---|---|
| file-only | 61 | 14 | 10 | **4** | 71% |
| repo access (model A) | 30 | 7 | 7 | **0** | **100%** |
| repo access (model B) | 37 | — | — | **0** | — |

Clustering all three conditions in one pool gave **ARI 0.978**.
**Both models discarded the same four false positives from the file condition.**
It is the strongest cross-model result in the study.

The two models reacted differently.

```text
model A   61 → 30 findings  (−51%)   said less overall
model B   27 → 37 findings  (+37%)   said more
```

They also found different real defects: 4 of the 10 adjudicated each, but the **union is 5**.
One defect was found by model A in 1 run out of 10 and by model B in **all 10**.

### The price was recall

```text
             precision     recall
file-only       71%          77%
repo access    100%          54%
```

Precision is *how much of what was reported was real*; recall is *how much of what exists was
found*. Repository access removed the false positives and lost some faint real ones with them.
Running both conditions and taking the union recovered 13/13 at 20 calls.

## 5. A regression that looked strongly reproduced was an artefact of the conditions

In the file-only fix loop, **four independent runs broke exactly the same four tests.**
The finding behind them was later adjudicated false, disappeared entirely once the repository
was open, and never recurred in the repo-access loop.

```text
                            file-only      repo access
rounds completed               15               10
RED rounds                  12 / 15          6 / 10
those four tests              every time      never
```

The guard the model added was reasonable given only the file, but production can never enter
that state. The tests were pinning **a state the real system cannot reach**.

> If the same tests keep breaking, check whether they pin a **reachable** state before
> concluding that the model introduced a regression.

## 6. Reviewers keep reporting findings on code that already satisfies the contract

tier-1. A Python module passing all 23 tests derived from 19 acceptance criteria.

```text
model A, bare prompt          5, 5, 6, 8, 7, 8, 6            median  6
model A, structured prompt   11, 11, 12, 11, 12, 12, 11      median 12
model B, bare prompt          1, 1, 1, 1, 0, 1, 1            median  1
model B, structured prompt    1, 1, 2, 2, 3, 4, 5            median  2
```

14 of 15 runs returned findings.
**189 findings were applied across 40 fix rounds and compliance never broke once.**
The benchmark's own runs reproduced it — 23/23 in all 54 rounds.

So in this experiment **compliance alone cannot tell one approach from another.**

## 7. A silent reviewer does not mean "everything has been seen"

```text
model B, bare         1 → 1 → 0 → 0 → 0     nothing from round 3 on
model B, structured   6 → 3 → 2 → 1 → 1     decays steeply
model A, bare         5 → 6 → 7 → 6 → 7     no decay
model A, structured  12 → 11 → 10 → 11 → 9  no decay
```

The condition that went silent from round 3 had found **two** issues across all five rounds.
On the same code, the structured condition kept turning up other failure modes — clock failure,
process-control exceptions, wedges.

> Zero findings is not evidence that the review is complete.

## 8. The contract really did bound where the model could move

Each condition or operator in the code was deliberately altered one at a time and the frozen
tests were run. **If the alteration made a test fail, that behaviour counts as already fixed by
the contract.** That is the criterion behind the mutation testing here.

```text
120 mutation points
  104  caught by the tests → fixed by the contract (87%)
   16  survived
         9  observationally equivalent — no real difference
         4  gaps in the test suite
         3  genuinely free, all in a single region the contract never defined
```

Across 47 review→fix rounds, observable behaviour moved in **exactly one place** — that free
region.

That is, **where the model moved and where the contract stayed silent are the same place.**

In one condition, rounds 3 and 4 reversed the same design decision in opposite directions;
both arguments were sound and both honoured the contract. The defect there is less in the code
than in **the spec never having defined that behaviour.**

## 9. A less dense contract does not necessarily produce oscillation

The second task covered comparable functionality with **8 acceptance criteria** instead of 19.

```text
4 independent implementations (3 by model A, 1 by model B)
  all pass 8/8
  all 6 implementation pairs: differential test 0/400 → identical observable behaviour
  sizes 54 / 101 / 133 / 138 lines → a 2.5× spread with the same behaviour

10 rounds applying 104 findings still gave 0/400
```

A differential test replays the same 400 inputs against two versions and looks for a divergence.
The harness was itself validated by planting deliberate differences, and it caught all of them
— 95/400, 400/400, 369/400.

```text
strong convention   TTL boundary · LRU refresh · meaning of len   → all 4 agree
weak convention     what to do with a wrong type                  → 4 gave 3 answers
```

> A sparse contract is not by itself what produces drift.
> **The choices split where no shared convention existed.**

## 10. Splitting review by category sometimes beat repeating it

tier-1, at an identical call budget.

| condition | calls | distinct findings | raw findings | duplication |
|---|---|---|---|---|
| single structured | 1 | 11.0 | 11.6 | 1.0× |
| same prompt, 6 calls | 6 | 19.7 | 69.3 | 3.6× |
| **six categories** | 6 | **30.0** | **54.7** | 1.8× |

Splitting by category raised **distinct findings by 52% while cutting raw findings by 21%.**
The extra material was concentrated in robustness, naming and style.

Adjudicating 39 of them (fan-out-exclusive and shared findings mixed together, unlabelled):

```text
REAL 12 (31%)   STYLE 27 (69%)   WRONG 0
```

Nothing was factually wrong about the code, but most were suggestions about naming, comments
and structure rather than real defects.

It **did not reproduce on the other task.** On the firmware task, fan-out recall at the same
budget was 43% against 50% for a single review, because the categories overlapped heavily.
A narrow "look only at module-internal state" lens also recreated one of the false positives
that repository access had removed.

> Fan-out paid off only where the review axes genuinely separate.

## 11. Whether to re-review tracked how much changed, not the round number

Because one review never finds everything, a second review produces new findings **even when
the code has not changed at all**. So the first step was to measure how many new findings appear
with the code held fixed. That is the null distribution.

Every combination of two disjoint triples from the existing 9 independent reviews — 1680 of
them — was enumerated.

```text
code unchanged      new-finding rate: median 11%, range 0–31%
after a real fix    new-finding rate: 77% / 89% / 63%
```

The post-fix rate lies far outside the range seen with unchanged code.
At the same time, **74–80% of the findings originally handed over disappeared** from the next
review.

What the new-finding rate moved with was the size of the fix.

```text
fix churn (lines)     143   87   82   36   28   36
genuinely new rate    82%   62%   43%  50%  40%  20%      r = 0.837 (n=6)
```

> The re-review question is less "which round is this?" than **"how much of this code was just
> written?"** If half the file was rewritten, it is effectively a first review of new code.

## 12. Compliance was identical; size and complexity were not

Ten conditions and 47 rounds all satisfied the contract at 19/19.
The maintainability measures on that same code diverged sharply.

```text
Cognitive Complexity   structured −17%   ·   bare +26%   ·   no contract +58%
most complex function    6.3              ·      10.3      ·      15
```

Cognitive Complexity measures how much nesting and branching a reader has to hold in their head.

Prompt and contract together did more than the sum of their parts.

```text
baseline: bare + no contract   37.0
contract only              →   33.3   (−3.7)
structured only            →   32.3   (−4.7)
both                       →   24.0  (−13.0)
```

Added separately the two effects come to 8.4; applied together they removed 13.0. That is an
**interaction** between the two conditions.

churn, meanwhile, behaved more like a measure of change cost than a quality score. The condition
that changed the most lines ended with the smallest, simplest code.

## 13. What the experiment called "the contract" was really two things

The variable bundled two elements together.

```text
B  the public API and behavioural surface are fixed; decline out-of-scope changes
C  the specification document itself
```

Measured apart:

| what the fixer was given | decline rate | final LOC | cumulative churn |
|---|---|---|---|
| A — do not touch what you were not asked about | 26% | 254 | 195 |
| A+B — and the public surface is fixed | **50%** | 237 | **136** |
| A+B+C — and here is the specification | 26% | **202** | 191 |

Told only that the surface was fixed, the fixer produced smaller code and less churn — but with
no specification to check against, it declined a great many ambiguous suggestions.
The grounds for those refusals differed too: without a spec, none of the 17 refusals cited an
acceptance criterion (they quoted the code's own docstring instead), while with one, 7 of 12 did.

> **A sentence fixing the scope suppressed growth; the specification supplied the standard for
> deciding what to accept and what to refuse.** That one line, with no specification behind it,
> was worth −7% LOC and −30% churn; the specification added accuracy of judgement on top.

## 14. Letting tests be read but not edited made build failures disappear

Reviewer and fixer could both see the whole source tree, but the test harness linked only one
module. In that state a **legitimate cross-module fix** broke the test build.

Neither the code nor the test was wrong.
**The oracle's scope was narrower than the review's scope.**

Mounting the test directory read-only made the fixer decline such changes itself.

> *"This fix would require changing the tests too."*
> *"The test pins the effective ring capacity."*
> *"This cannot be fixed inside this file — the information is in sensor.c."*

Build failures across that loop went to zero without touching the build system.

About a third of those refusals, though, were **"real, but outside the current scope"**.
Deferred, not resolved.

## 15. Mixing models was more efficient than repeating one

Every subset of the existing runs, enumerated. No extra model calls.
The denominator is the 10 adjudicated real defects; each entry is the average of
**real found / false found**.

| calls | file-only | repo A | repo B | **mixed** |
|---|---|---|---|---|
| 1 | 3.40 / **2.70** | 1.40 / 0 | 2.70 / 0 | 2.70 / 0 |
| 2 | 5.04 / **3.62** | 2.09 / 0 | 3.07 / 0 | **3.18** / 0 |
| 3 | 6.11 / **3.90** | 2.54 / 0 | 3.27 / 0 | **3.57** / 0 |
| 4 | 6.93 / **3.98** | 2.90 / 0 | 3.40 / 0 | **3.90** / 0 |
| 6 | 8.20 / **4.00** | 3.43 / 0 | 3.60 / 0 | **4.43** / 0 |

**Three mixed calls (3.57) beat six calls of a single model (repo A, 3.43).**
And at equal call counts, mixed led everywhere from two calls up.

File-only review finds more per call, but the false positives climb just as fast: by the fifth
call all four adjudicated false positives have appeared. The budget saved is not gone — it has
**moved to whoever triages.**

*The denominator excludes defects that only the repo-access conditions found, so this table is
not tilted in favour of repository access.*

## 16. The benchmark's own runs also show per-model loop behaviour

tier-1. The `retry_policy` task, three loops per model, 2026-08-21.

| model | calls | cost | loop_decay | churn | decline rate | code size | tools blockable |
|---|---|---|---|---|---|---|---|
| A | 30 | $15.74 | −1.25 | does not converge (splits 1:2) | 0.209 | **1.258×** | yes |
| B | 24 | n/a | −0.25 | not measurable (loop ended early) | 0.273 | **0.906×** | **no** |

`loop_decay` is the slope of findings per round: negative means they fall, and −1.25 means about
1.25 fewer findings each round. `code size` is the final round's line count divided by the
starting code, so above 1 it grew and below 1 it shrank. `tools blockable` records whether that
CLI can actually disable the model's tools — a model that cannot be muzzled is a confound, so it
travels with the row.

The direction of code size was a property of the model: one grew the code as it applied
findings, the other shrank it. How long a review→fix loop can safely run depends on that.

**churn convergence did not make a usable stop rule.**
Model A's three loops measured 0.611 / 0.732 / 0.720, straddling the 0.7 threshold.
Model B's loop ended too early for convergence to be computed at all.

> **"Could not be measured" and "did not converge" are different results.**
