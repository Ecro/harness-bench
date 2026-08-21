# So how should you review?

[한국어](PRESCRIPTION.ko.md) · long-form: [`STUDY.md`](STUDY.md)

A working recipe based on what was measured. It is written for **anyone building or fixing a
pipeline that has a model review code**, and every item carries the strength of the evidence
behind it.

The numbers themselves are in [`FINDINGS.md`](FINDINGS.md), and what these results cannot be
used to claim is in [`../LIMITS.md`](../LIMITS.md).

Each recommendation ends with a marker for **how strong the evidence is**. Two items can both be
"recommended" and rest on very different ground.

```text
[evidence: reproduced]     the same result appeared in different models or different conditions
[evidence: measured once]  measured once, in one condition. Not yet reproduced
[evidence: judgement]      not directly supported by data — a judgement based on what was observed
```

In the machine output of `bench prescribe` and in the ledger, those same grades print as `***`,
`**` and `*`. An ungraded rule does not render at all — without a grade, an opinion is laundered
into advice.

## The vocabulary on this page

The study measured review as **two separate roles**, and that split is the backbone of
everything below.

```text
reviewer   reads the code and reports problems. Never touches the code
fixer      takes those reports and actually edits the code. May decline
```

| term | meaning |
|---|---|
| **finding** | one item a reviewer reported. Whether it is real is a separate question |
| **false positive** | a finding reported as a defect that is not one |
| **distinct / raw findings** | the count after findings naming the same problem are grouped / the total before grouping |
| **call** | one model invocation. The unit of cost |
| **round / loop** | one review→fix pass is a round; repeating that pass several times is a loop |
| **contract** | the specification pinning what the code must do, and the tests that check it |
| **compliance** | how much of that contract holds. `19/19` and `23/23` mean every criterion and every test passed |
| **public surface** | the parts other code depends on — names, signatures, documented behaviour |
| **file-only / repo access** | the reviewer is given the target file alone / the source tree is mounted read-only |
| **mixed** | calls split between two different models instead of repeating one |
| **precision / recall** | the share of reported findings that were real / the share of existing defects that were found |
| **churn** | lines added and deleted in a round. *How much was touched*, not a quality measure |
| **decline rate** | the share of handed-over findings the fixer refused to apply, with a stated reason |
| **fan-out** | splitting one reviewer into several specialists instead of asking one to cover everything |
| **lens** | the perspective assigned to one such reviewer — "look only at concurrency", say |

---

## The principle that matters most

| | gain | cost |
|---|---|---|
| **review only, repeated** | real-defect coverage 34% → 61% → 76% | none; the code never changes |
| **review→fix loop, repeated** | compliance, already perfect, stayed exactly the same | code +24% to +152% |

Coverage is *what share of the real defects that exist were found*, and those three figures are
one, three and five reviews.

> ### Review many times. Fix once. `[evidence: reproduced]`

The gain in discovery comes from the review side, and the risk of changing the code comes from
the fix side. A harness — the loop wrapped around the model — that alternates the two on every
pass grows the cost of fixing faster than the benefit of finding.

---

## The procedure

```text
1  give reviewers read access to the source tree                    [evidence: reproduced]
     With only the target file, 29% of the distinct defects were false positives;
     with the repository readable, 0%. The same in both models.
     The price is recall, which fell from 77% to 54% — able to check, the reviewer
     concludes "this is barely reachable in practice" and says less.
     If you want neither loss, run both conditions and merge them
     (20 calls spent that way found all 13 adjudicated defects).

2  if you can afford it, split by category instead of repeating     [evidence: measured once]
     For the same six calls, repeating one prompt found 19.7 distinct findings while
     six areas (design, functionality, complexity, robustness, naming, style) found
     30.0 (+52%) — with 21% fewer raw findings to read, because less is repeated.
     ⚠ On a task whose areas overlapped, it gained nothing.
       Check that the categories genuinely separate before spending on it.
     ⚠ A narrow lens can partly undo the benefit of repository access. Told to look
       only at module-internal state, one lens brought back a false positive the
       repository had already removed.

3  do not use agreement between reviewers as a test of truth        [evidence: reproduced]
     With a single file in scope, false positives were reported 6.8 times out of 10 on
     average and real defects 3.4 — the more often reported were the false ones.
     The reviewers converged because none of them could see the same information.
     Opening the repository inverts that relation.
     ⚠ In one condition this conflicted with rule 2. There is no filter rule yet for
       using both together.

4  have a human triage once — do not automate                       [evidence: measured once]
     69% of the adjudicated findings were about naming, comments and structure: not
     wrong, but not defects either. There is no need to pass all of that to a fixer.
     Without the human step the pipeline still ran — the fixer declined 34% instead —
     but the code grew 152% in three rounds.

5  merge the findings and fix once, with the contract and read-only tests  [evidence: measured once]
     74-80% of the findings handed over genuinely disappeared from the next review;
     fixing everything in one pass does work.
     Once the fixer could read the tests but not edit them, it began declining
     out-of-module changes rather than attempting them, and build failures that had
     recurred through an entire loop went to zero.
     Note that this defers the problem out of scope rather than solving it.

6  record size, complexity and churn alongside the tests            [evidence: reproduced]
     Compliance was 19/19 in all ten conditions across 47 rounds, and 23/23 in all 54
     rounds of the benchmark's own run: on pass/fail alone no approach can be told
     from another.
     Complexity split sharply — −17% for the condition using a structured review
     prompt, +58% for the one whose fixer was given no contract.
     It costs one parse of the code. No extra model calls.

7  decide re-review by how much changed, not by round count         [evidence: measured once]
     When the fix was small, the next review yielded little.
     When it was large, there was a lot of newly written code and reviewing again paid.
     The new-finding rate moved with fix churn (correlation r = 0.837).
     ⚠ "Stop when churn converges to zero" was not a universal rule.
       It held on a contract-bearing task; on one without a contract churn went
       194 → 262 → 395 lines and kept rising.
       Without a contract, set a round cap instead.

8  if the loop keeps reversing the same decision, check the spec    [evidence: measured once]
     Across 47 rounds exactly one behaviour actually moved, and it was the single
     region the contract left undefined.
     If the same decision is reversed twice, look for the blank in the spec before
     changing more code.

9  even without a spec, state the scope: "the public surface is fixed"  [evidence: measured once]
     That one line — do not change what other code depends on — cut the final line
     count by 7% and cumulative churn by 30%.
     ⚠ In exchange, the decline rate rose from 26% to 50%.
       With nothing to check against, a fixer declines anything ambiguous.
       Whether half of those refusals were real loss was not measured.

10 run two models once each rather than one model twice             [evidence: reproduced]
     Both models removed the same four false positives, but the real defects they
     found differed (4 of 10 each, union 5).
     Three mixed calls found more real defects than six calls of a single model (repo A).
```

---

## Budget

Every subset of the existing runs, enumerated exhaustively. No extra calls.
The figures are averages against the 10 adjudicated real defects
(**real found / false found**).

| calls | file-only | repo A | repo B | **mixed** |
|---|---|---|---|---|
| 2 | 5.04 / **3.62** | 2.09 / 0 | 3.07 / 0 | **3.18** / 0 |
| 3 | 6.11 / **3.90** | 2.54 / 0 | 3.27 / 0 | **3.57** / 0 |
| 4 | 6.93 / **3.98** | 2.90 / 0 | 3.40 / 0 | **3.90** / 0 |
| 6 | 8.20 / **4.00** | 3.43 / 0 | 3.60 / 0 | **4.43** / 0 |

repo A and repo B are two models from different companies, both with repository access.

**Two calls:** one from each model. 3.18 real on average, zero false.
Spending the same two calls file-only on one model finds 5.04 real — and 3.62 false along
with them. Those false ones are the most plausible-looking findings in the set.

**Four calls:** two from each model finds 3.90.
That is close to a single model's ten-call result of 4.00, at 60% fewer calls.

Reviewing from the file alone finds more per call.
The saving does not disappear, though — it moves to the person who has to sort the false
positives out.

---

## Getting out of the endless loop

How long should review→fix repeat? Of the four candidate stop rules, three are hard to use as a
general criterion.

```text
churn → 0        held only on contract-bearing tasks; elsewhere it kept rising
zero findings    it did end one loop, but it can also mean the reviewer saw less
round cap        truncation, not convergence
don't loop       ← the simplest alternative
```

"Zero findings" is dangerous for a concrete reason. One model reported nothing from round 3 on,
while on the same code a structured prompt kept turning up other failure modes afterwards. The
one that went quiet had not seen everything.

There is one more practical stopping force: as the file grows, the review itself slows down.
In one experiment the round-4 reviews of a 900-line file exceeded a 15-minute ceiling.
A loop run long enough can end in a timeout rather than in convergence.

## If your team writes specifications

Two further things are available to you on top of the procedure above.

**Record size, complexity and churn beside compliance.**
It takes one parse of the code and no extra model calls.
If the tests keep passing while size and complexity climb, that is the point to ask again what
the review is actually improving.

**Use recurring oscillation as a specification audit.**
Where the loop keeps reversing the same decision is likely a region the contract never defined.
Rather than continuing to change the code, pin the intent in the spec first.

### A one-minute version of the canary

> **Canary** — a probe that checks the *instrument is actually attached* before anything is
> measured. This bench's canary runs in both directions: something that should be reachable
> (POS) and something that must not be (NEG). A failed POS leg is not isolation working, it is
> a **broken probe**, and numbers collected in that state are void. See
> [`METHODS.md`](METHODS.md).

You do not need the research apparatus for this — only a check that rule 1 actually took effect.

> Occasionally, ask the reviewer to quote a specific line **of a caller file** — not the file
> under review. If it cannot, repository access was never really attached.

"The configuration did not apply" and "the model just behaves that way" look identical from the
outside. This one check separates them.
