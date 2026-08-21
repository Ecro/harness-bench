# So how should you review?

[한국어](PRESCRIPTION.ko.md) · long-form: [`STUDY.md`](STUDY.md)

A working recipe based on what was measured. Each item carries the strength of the evidence
behind it. The numbers themselves are in [`FINDINGS.md`](FINDINGS.md), and what these results
cannot be used to claim is in [`../LIMITS.md`](../LIMITS.md).

```
***  reproduced across models or conditions
**   measured once
*    judgement
```

---

## The principle that matters most

| | gain | cost |
|---|---|---|
| **review only, repeated** | real-defect coverage 34% → 61% → 76% | none; the code never changes |
| **review→fix loop, repeated** | compliance, already perfect, stayed exactly the same | code +24% to +152% |

> ### Review many times. Fix once. `***`

The gain in discovery comes from the review side, and the risk of changing the code comes from
the fix side. A harness that alternates the two on every pass grows the cost of fixing faster
than the benefit of finding.

---

## The procedure

```
1  give reviewers read access to the source tree                    ***
     29% false positives when the reviewer saw one file; 0% with the repository open.
     The same in both models.
     The price is recall, which fell from 77% to 54%.
     If you want neither loss, run both conditions and merge them (13/13 for 20 calls).

2  if you can afford it, split by category instead of repeating     **
     For the same six calls, repeating one prompt found 19.7 distinct issues while six
     category prompts found 30.0 (+52%) — with 21% fewer raw findings to read.
     ⚠ On a task whose lenses overlapped, however, it gained nothing.
       Check that the categories genuinely separate before spending on it.
     ⚠ A narrow lens can partly undo the benefit of repository access. Told to look only
       at module-internal state, one lens brought back a false positive the repository
       had already removed.

3  do not use agreement between reviewers as a test of truth        ***
     With a single file in scope, false positives were found 6.8 times out of 10 on
     average and real defects 3.4 — the opposite of what you would assume.
     Opening the repository inverts that correlation.
     ⚠ In one condition this conflicted with rule 2. There is no filter rule yet for
       using both together.

4  have a human triage once                                         ** — do not automate
     69% of the adjudicated findings were about naming, comments and structure.
     There is no need to pass all of that to a fixer.
     Removing the human step still worked — the fixer declined 34% instead — but the
     code grew 152% in three rounds.

5  merge the findings and fix once, with the contract and read-only tests   **
     74-80% of the findings handed over genuinely disappeared from the next review.
     Once the fixer could read the tests but not edit them, it began declining
     out-of-module changes rather than attempting them, and build failures that had
     recurred through an entire loop went to zero.
     Note that this defers the problem out of scope rather than solving it.

6  record size, complexity and churn alongside the tests            ***
     Compliance was 19/19 in all ten arms across 47 rounds, and 23/23 in all 54 rounds of
     the benchmark's own run. On that metric alone no approach can be told from another.
     Complexity, by contrast, split sharply: −17% (structured) against +58% (no contract).
     It costs one AST pass. No extra model calls.

7  decide re-review by how much changed, not by round count         **
     When the fix was small, the next review yielded little.
     When it was large, there was a lot of newly written code and reviewing again paid.
     The new-finding rate tracked fix churn at r = 0.837.
     ⚠ "Stop when churn converges to zero" was not a universal rule.
       It held on a contract-bearing task; on one without a contract churn went
       194 → 262 → 395 and kept rising.
       Without a contract, set a round cap instead.

8  if the loop keeps reversing the same decision, check the spec    **
     Across 47 rounds exactly one observable behaviour moved, and it was the single
     region the contract left undefined.
     If the same decision is reversed twice, look for the blank in the spec before
     changing more code.

9  even without a spec, state the scope: "the public surface is fixed"   **
     That one line alone cut LOC by 7% and churn by 30%.
     ⚠ In exchange, the decline rate rose from 26% to 50%.
       With nothing to check against, a fixer declines anything ambiguous.
       How much of that was real loss was not measured.

10 run two models once each rather than one model twice             ***
     Both models removed the same four false positives, but the real defects they found
     differed (4/10 each, union 5/10).
     Three mixed calls found more real defects than six calls of a single model (repo A).
```

---

## Budget

Every subset of the existing runs, enumerated exhaustively.
The figures are averages against the 10 adjudicated real defects (true found / false found).

| calls | file only | repo A | repo B | **mixed** |
|---|---|---|---|---|
| 2 | 5.04 / **3.62** | 2.09 / 0 | 3.07 / 0 | **3.18** / 0 |
| 3 | 6.11 / **3.90** | 2.54 / 0 | 3.27 / 0 | **3.57** / 0 |
| 4 | 6.93 / **3.98** | 2.90 / 0 | 3.40 / 0 | **3.90** / 0 |
| 6 | 8.20 / **4.00** | 3.43 / 0 | 3.60 / 0 | **4.43** / 0 |

**Two calls:** one from each model. 3.18 real on average, zero false.
Spending the same two calls file-only on one model finds 5.04 real — and 3.62 false along
with them. Those false ones are the most plausible-looking findings in the set.

**Four calls:** two from each model finds 3.90.
That is close to a single model's ten-call result of 4.00, at 60% fewer calls.

Reviewing from the file alone finds more per call.
The saving does not disappear, though — it moves to whoever does the triage.

---

## Getting out of the endless loop

Of the four candidate stop rules, three are hard to use as a general criterion.

```
churn → 0        held only on contract-bearing tasks; elsewhere it kept rising
zero findings    it did end one loop, but it can also mean the reviewer saw less
round cap        truncation, not convergence
don't loop       ← the simplest alternative
```

There is one more practical stopping force: as the file grows, the review itself slows down.
In one experiment the round-4 reviews of a 900-line file exceeded a 15-minute ceiling.
A loop run long enough can end in a timeout rather than in convergence.

## If your team writes specifications

Two further things are available to you on top of the procedure above.

**Record size, complexity and churn beside compliance.**
It takes one AST pass and no extra model calls.
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

You do not need the research apparatus for this.

> Occasionally, ask the reviewer to quote a specific line **of a caller file** — not the file
> under review. If it cannot, repository access was never really attached.

"The configuration did not apply" and "the model just behaves that way" look identical from the
outside. This one check separates them.
