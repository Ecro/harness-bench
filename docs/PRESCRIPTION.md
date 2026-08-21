# So how should you review?

[한국어](PRESCRIPTION.ko.md) · long-form: [`STUDY.md`](STUDY.md)

The recipe the measurements support. Every line carries the evidence behind it; see
[`FINDINGS.md`](FINDINGS.md) for the numbers and [`LIMITS.md`](LIMITS.md) for what none of
this establishes.

```
***  reproduced across models or conditions
**   measured once
*    judgement
```

---

## The one that matters most

| | gain | cost |
|---|---|---|
| **review only, repeated** | real-defect coverage 34% → 61% → 76% | none; the code never changes |
| **review→fix loop, repeated** | zero | code +24% to +152% |

> ### Review many times. Fix once. `***`

The coverage gain is entirely on the review side and the code risk is entirely on the fix
side. A harness that alternates them maximises risk per unit of gain.

---

## The procedure

```
1  give reviewers read access to the source tree                    ***
     file-only: 29% false positives.  repo open: 0%.  Both models.
     the price is recall, 77% → 54%. To keep both, run both conditions
     and take the union (13/13 for 20 calls).

2  if you can afford the calls, split by category instead of repeating   **
     same 6 calls: identical prompt → 19.7 distinct; six category prompts → 30.0 (+52%),
     with 21% FEWER raw findings.
     ⚠ this did not transfer to a task whose lenses overlapped — there it gained nothing.
       Verify the axes separate before spending on it.
     ⚠ a narrow lens partially undoes rule 1: a lens told to look only at module-internal
       state reintroduced a false positive that repo access had removed.

3  do not use agreement as a proxy for truth                        ***
     in a file-only scope, false positives averaged 6.8 detections in 10 and true defects
     3.4 — anti-predictive. Opening the repo inverts the correlation.
     ⚠ conflicts with rule 2 in one case; that combination has no filter rule yet.

4  a human triages                                                  ** — do not automate
     69% of findings are naming, comments and structure. Those do not go to a fixer.
     Removing this step still worked (the fixer rejected 34% instead) but the code grew
     152% in three rounds.

5  fix once, with the contract and read-only test access            **
     74-80% of the findings handed over actually disappear.
     Read access without edit access makes the fixer decline out-of-module fixes rather
     than attempt them — build failures went from an entire loop to zero without touching
     the build system. It defers rather than fixes; that is the trade.

6  record tests AND size AND complexity AND churn                   ***
     compliance was 19/19 in all ten arms across 47 rounds, and 23/23 in all 54 rounds of
     the benchmark's own run. It discriminates nothing.
     Where the arms separate: complexity −17% (structured) vs +58% (no contract).
     Cost: one AST pass. No model calls.

7  decide re-review by churn, not by round count                    **
     small fix → small yield, move on. Large fix → that is a FIRST review of new code.
     new-finding rate tracks fix churn at r = 0.837.
     ⚠ "stop when churn converges" is conditional. It held on a contract-bearing task and
       failed on one without: churn went 194 → 262 → 395 and the loop ended on "zero
       findings" instead — the criterion this rule rejects. Without a contract, cap rounds.

8  if the loop reverses the same decision twice, fix the spec       **
     across 47 rounds exactly one observable behaviour moved, in the single region the
     contract left undefined. Oscillation is a free-specification signal, and it is a
     specification audit you get for nothing.

9  even without a spec, say "the public surface is fixed"           **
     one line buys −7% LOC and −30% churn.
     ⚠ rejection rate doubles, 26% → 50%. Told a surface is fixed with nothing to check
       against, a fixer rejects everything ambiguous. Whether half of that is real loss
       was not measured.

10 run two models once each rather than one model twice             ***
     both dropped the same four false positives, but found different true ones
     (4/10 each, union 5/10). Three mixed calls beat six same-model calls.
```

---

## Budget

Exhaustive over all subsets of existing runs; (true found / false found) against 10
adjudicated defects:

| calls | file only | repo A | repo B | **mixed** |
|---|---|---|---|---|
| 2 | 5.04 / **3.62** | 2.09 / 0 | 3.07 / 0 | **3.18** / 0 |
| 3 | 6.11 / **3.90** | 2.54 / 0 | 3.27 / 0 | **3.57** / 0 |
| 4 | 6.93 / **3.98** | 2.90 / 0 | 3.40 / 0 | **3.90** / 0 |
| 6 | 8.20 / **4.00** | 3.43 / 0 | 3.60 / 0 | **4.43** / 0 |

**Two calls:** one from each model. 3.18 true, zero false. The same two calls spent
file-only on one model see 5.04 true — and hand a human 3.62 false ones, which are the most
plausible-looking findings in the set.

**Four calls:** two from each. 3.90 — close to a single model's ten-call result (4.00), at
60% less budget.

File-only finds more per call. That budget is not saved, it is **moved to whoever triages.**

---

## Escaping the endless loop

Four candidate stop rules. Three do not survive.

```
churn → 0        holds only on contract-bearing tasks; elsewhere churn increased monotonically
zero findings    what actually ended one loop — and the criterion rule 7 rejects
round cap        truncation, not convergence
don't loop       ← what is left
```

There is a second, quieter stopping force: **the file grows, so review slows.** In one
loop the reviews at round 4 exceeded a 15-minute ceiling on a 900-line file. Run a loop
long enough and it ends in timeout rather than convergence.

## For a team with specifications

Six of the above apply directly. Two more are available only to you:

**Record size, complexity and churn beside compliance.** One AST pass, no model calls. The
moment the two diverge is the moment the loop started making the code worse.

**Treat oscillation as a specification audit.** Where the loop reverses itself is exactly
where your contract is silent, and that costs nothing to collect.

### A one-minute version of the canary

No research apparatus needed:

> Once a month, ask the reviewer to quote line N **of a caller file** — not the file under
> review. If it cannot, the access was never attached.

"The configuration did not apply" and "the model behaves that way" look identical from the
outside. That single check is what separates them.
