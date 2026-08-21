# How many times should you run an AI code review? — what ~400 calls taught me

[한국어](STUDY-ko.md)

> This is the long-form record of the experiments — and the mistakes — that produced
> `harness-bench`, told as one narrative.
> For the numbers alone see [`FINDINGS.md`](FINDINGS.md); for the procedure alone see
> [`PRESCRIPTION.md`](PRESCRIPTION.md); for the reproducible benchmark results see
> [`README.md`](README.md).
>
> Raw data, tools and experiment logs: <https://github.com/Ecro/spoton> `work-docs/`, `tools/`
>
> The "~400" in the title is the number of **LLM calls** the study actually spent. It is not a
> count of review calls only, nor of experiment runs.

---

## The conclusions first

The study began with one question: **how many times do you have to run an AI code review before
it is enough?**

I started out thinking it was simple.

> Review, fix, review again — surely it gets better each time?

The results were not that simple.

What survived:

1. **Repeating a review and repeating a review→fix loop are two different activities.**
   - Review alone, repeated, took real-defect coverage from roughly `34% → 61% → 76%`.
   - Alternating review and fix produced **no** gain in contract compliance, while the code
     grew `+24%` to `+152%`.

2. **One review is not enough.**
   - Reviewing the same unchanged code repeatedly surfaces different defects each time.
   - Some real defects showed up in only 1 run out of 10.

3. **But being reported many times is no guarantee of being real.**
   - Given a single file, the false positives (findings that are not defects at all) were
     reported *more* often than the real defects.
   - Not because the reviewers shared information — because they were all **missing the same
     information**.

4. **Letting the reviewer read the repository was the strongest false-positive killer in the
   study.**
   - With one file only, 29% of the distinct defects were false.
   - Given the callers, headers and init path, the same four false positives vanished — in both
     vendors' models.

5. **A quiet model has not necessarily finished.**
   - One model returned "nothing to report" from round 3 onward; given a structured prompt on
     the same code, it kept finding failure modes it had never mentioned.

6. **A green test suite does not mean the code got better.**
   - Compliance was identical across 47 rounds while size and complexity diverged sharply
     between arms.

7. **So the working prescription is short.**

> **Review many times. Fix once.**

And if the fix changed enough of the code, what follows is not a *re-review* — it is the **first
review of newly written code**.

---

# 1. It started as a simple suspicion

Our workflow had an AI review step in it.

```text
write code
  ↓
AI review
  ↓
fix
  ↓
AI review again
  ↓
fix again if needed
```

It looped up to three rounds automatically.

That structure rests on one assumption:

> **More review makes the code better.**

The problem is that the sentence looks so obvious that nobody had measured it.

So I measured it.

What I learned most in this study, though, was not about AI review — it was about **how to
measure**. My own conclusions kept getting overturned as the experiments came in, almost always
in the less dramatic direction.

The clearest case:

> "The AI's fixes reproduced the same bug 4 times out of 4."

That is what it looked like at first.

It turned out to be **not a bug at all — the tests were pinning a state production can never
reach**.

This document is the accumulation of corrections like that one.

---

# 2. Ten reviews of the same unchanged code

The first target was a real firmware module.

- file: `swing_capture.c`
- size: 359 lines
- shape: a ring buffer written by a sensor thread and read by an ML thread
- problem surface: concurrency, state invariants, resource limits
- tests: 18

Here the code was **never changed**; the same input was reviewed 10 times independently.

Each review ran in a completely fresh process. Asking repeatedly inside one conversation lets
the previous answer contaminate the next review.

The reviewer was given the target code only; the repository was removed at the filesystem level.

## 2.1 The results moved more than expected

```text
run:       01  02  03  04  05  06  07  08  09  10
findings:   6   6   5   7   5   7   9   5   4   7
```

Same code — one run reported 4, another 9.

**A 2.25× spread.**

Clustering the 61 findings from those 10 reviews by underlying defect gave 14 distinct groups.

The clustering was checked for arbitrariness:

- reshuffled and re-clustered three times: `ARI 1.000`
- a different vendor's model clustering the same 61 findings: the same 14 groups

> **ARI** (Adjusted Rand Index) — how far two clusterings agree on the same partition. `1.000`
> is identical; `0` is no better than grouping at random. It is used here to check that
> "which findings are the same defect" does not depend on who (or which model) grouped them,
> or in what order.

On that basis, the fraction of distinct defects found as review count rises:

```text
1 review  :  6.1 / 14  = 44%
3 reviews : 10.0 / 14  = 71%
5 reviews : 11.6 / 14  = 83%
8 reviews : 13.2 / 14  = 94%
```

It would have been easy to stop here and conclude:

> "One AI review sees about half."

Then I adjudicated the 14 against the whole codebase, and the story changed.

---

# 3. The most frequently reported findings were the false ones

Of the 14 groups, 10 were real and 4 were false.

```text
real defects  10
false          4
false rate    29%
```

> **False positive** — a finding reported as a defect that is not one. Throughout this document,
> the real/false verdicts were made by reading **the whole repository**, not the target file.

The problem was *where* the false ones sat.

```text
mean detection frequency, the 4 false    6.8 / 10
mean detection frequency, the 10 real    3.4 / 10
```

**Four of the five most frequently reported findings were false.**

| group | freq | what the reviewer claimed | what is actually true |
|---|---:|---|---|
| D02 | 8/10 | descriptors left in the queue are corrupted on re-init | `init()` is called exactly once, at boot |
| D03 | 7/10 | underflow when `ring_total == 0` | `ring_push()` always runs first; the state is unreachable |
| D04 | 7/10 | `force_expire()` is called from another thread, so there is a race | it is the same `sensor_thread` |
| D07 | 5/10 | misbehaves under a particular call order | the real call order is different |

The four had one thing in common.

**Inside the target file none of them can be refuted; you have to look at another file to see
they are wrong.**

- call order
- init path
- which thread actually runs it
- invariants held outside the module

Every reviewer saw the same single file. So every reviewer was missing the same facts.

And so they converged, repeatedly, on the same wrong conclusion.

That gave the study one of its central lessons:

> **Agreement is not evidence of truth.**
>
> Sometimes many reviewers converge on the same wrong answer precisely because none of them has
> the information that would settle it.

Excluding the false positives, one review's real-defect coverage is not 44% but **34%**.

```text
                  all 14      the 10 real
1 review            44%           34%
3 reviews           71%           61%
5 reviews           83%           76%
```

So the accurate sentence for this data is:

> **One review sees about a third of the real defects.**

---

# 4. Does alternating review and fix help?

Next I built the actual auto-fix loop.

```text
review → fix → review → fix → ...
```

Five rounds made one loop; the loop ran three times.

The fixing AI could not see the tests. The tests were run separately after each round.

The raw result looked alarming.

```text
12 of 15 rounds ended RED
four independent runs broke exactly the same 4 tests
```

Those "four" are the round 1 of each of the three loops, plus one separate gate run. The four
differed in finding count (4, 5, 6, 7) and in resulting code size (439–505 lines), and still
broke the same tests.

I was nearly convinced:

> "The AI keeps writing the same bug."

That conclusion was wrong.

## 4.1 What broke was not the code but the tests' assumption

The core change the AI added was a guard:

```c
if (ring_total == 0) {
    return;
}
```

Looking at the one file, that is reasonable defensive code.

The catch is that in production, `ring_push()` always runs before that function is reached.

That is:

```text
production:
ring_push()
  ↓
arming()
```

Given that order, arming cannot be called with `ring_total == 0`.

But several unit tests called arming right after `reset()`, with no push.

The tests were pinning **a state that does not exist in production**.

So the guard the AI added changed nothing about real behaviour, and broke the tests anyway.

> **The code did not break. Only the tests did.**

After that, later experiments stopped treating tests as a plain answer key.

When a test fails, the first question is:

> Is this test pinning a state production can actually reach?

---

# 5. So I built the contract first and started over

The first experiment's real weakness was its oracle.

> **Oracle** — whatever decides that a result is right or wrong. Here the acceptance suite is
> the oracle. If the oracle itself is wrong, every number measured on top of it is void.

Whatever a failing test showed, you could always answer:

> "Wasn't that test over-specified?"

So the second task inverted the order.

```text
1. write the SPEC
2. freeze 19 acceptance criteria
3. write tests from the SPEC only  (the 19 criteria yielded 23 acceptance tests)
4. write the implementation from the SPEC only
5. the implementer never sees the tests
6. measure compliance with the acceptance tests
7. iterate review → fix
```

The target was a Python retry-policy module with exponential backoff, full jitter and a circuit
breaker.

> **Acceptance criterion (AC)** — one verifiable sentence carved out of what the spec
> guarantees. "Frozen" means fixed before any implementation exists and never edited after —
> the only defence against *"the tests were fitted to the implementation"*.

From here on, "23/23" means all acceptance tests pass, and "19/19" means all 19 criteria hold.

## 5.1 The oracle was validated first

Three independent implementations passed the contract on the first attempt.

```text
reference implementation   23/23
codex independent build    23/23
claude build               23/23
```

Then I checked that the suite actually catches wrong behaviour.

```text
correct implementation             19/19
AC-19 deliberately violated        18/19  → fails exactly AC-19
code that will not even import      0/19
```

Only now was there a basis for saying "a failure means a spec violation".

---

# 6. Reviewers report findings even on code that is already correct

The starting point is the verified 19/19 implementation.

On compliance alone, there is nothing left to improve.

Show it to a reviewer anyway, and the findings keep coming.

### Claude

```text
bare prompt:
5, 5, 6, 8, 7, 8, 6
median 6

structured prompt:
11, 11, 12, 11, 12, 12, 11
median 12
```

All 14 runs returned findings.

> **bare vs structured prompt** — bare is close to "review this code" and nothing more;
> structured prescribes what to look at, in what order, and in what output format. The two arms
> differ in the prompt only — same code, same model, same number of rounds.

And many of them were not nitpicks:

- reading the `state` property alone triggers a state transition
- catching `BaseException` counts `KeyboardInterrupt` as a circuit failure
- the backoff exponent can overflow instead of saturating

None of these live inside the 19 acceptance criteria.

Passing every test does not mean there is nothing to review.

> **The contract does not describe the whole of the code.**

---

# 7. But the models differed in how they decide they are done

The same code and the same bare prompt went to codex.

```text
claude bare
5, 5, 6, 8, 7, 8, 6

codex bare
1, 1, 1, 1, 0, 1, 1
```

codex actually returned "nothing to report" in one run.

Running the loop made the difference sharper.

```text
codex bare
1 → 1 → 0 → 0 → 0

codex structured
6 → 3 → 2 → 1 → 1

claude bare
5 → 6 → 7 → 6 → 7

claude structured
12 → 11 → 10 → 11 → 9
```

codex decayed.

claude did not.

And all four conditions stayed at 19/19 the whole way.

Two things have to be kept apart here.

### 1. Do the findings decay?

Largely a property of the model.

### 2. Did it actually see everything?

The finding count cannot tell you.

Across five rounds, codex bare covered what amounted to two families of issue.

The structured condition, on the same code, kept turning up failure modes bare never mentioned
once:

- clock failure
- process-control exception
- half-open wedge
- stale cooldown

Therefore:

> **Silence is not evidence of completion.**
>
> Stopping because you said less and stopping because you saw enough look identical from
> outside.

---

# 8. Every test passed, and the code quality still diverged

At this point a new question appeared.

> If all the tests pass, is the code actually improving?

On compliance, all 47 rounds were identical.

So I layered other measurements onto the existing snapshots.

- **Differential testing** — replay identical inputs against two versions and see whether the
  observable behaviour diverges. It catches behaviour changes the tests never look at.
- **LOC** — lines of code.
- **Cognitive Complexity** — how much nesting and branching a reader has to hold in their head.
  Unlike cyclomatic complexity it weights nesting.
- **worst-function complexity** — not the file's total but the single most complex function:
  where the reading cost is concentrated.
- **mutation score** — the fraction of deliberately planted defects the suite catches. A proxy
  for what the tests actually guarantee.
- **relative churn** — **churn** is the number of lines added and deleted in a round, i.e. the
  *amount changed* (not a quality measure). Relative churn divides the accumulated churn by
  file size, so files of different sizes can be compared.

## 8.1 How much did behaviour outside the contract move?

300 deterministic scenarios compared v0 against every round.

Across all 47 rounds there was exactly **one** observable behaviour change.

```text
half_open → open
```

The point at issue:

> A circuit breaker whose cooldown has elapsed but which nobody has called yet — is that `open`
> or `half_open`?

The contract does not answer that.

So neither choice violated 19/19.

What is interesting is that the same review loop flipped the choice repeatedly.

In one round:

> Until an actual trial call happens, it must report `open`.

In the next:

> The cooldown is over, so behaviourally it is already `half_open` and should say so.

Both were plausible.

Both honoured the contract.

And they were opposites.

Which matters because:

> **If a loop keeps reversing the same decision, the defect is probably not in the code but in
> the blank left by the spec.**

---

# 9. "A sparse contract makes it oscillate" was also not quite right

My first explanation was that a large free space lets the AI keep wobbling inside it.

So I built a second task — a TTL cache covered by **8** criteria instead of 19.

Far sparser contract.

The result was not what I predicted.

- 3 independent implementations by claude
- 1 by codex
- all pass 8/8
- sizes from 54 to 138 lines — a 2.5× spread
- all 6 implementation pairs: differential test `0/400`
- a 10-round loop applied 104 findings and observable behaviour never moved

A contract can leave a lot unsaid and the behaviour still agrees.

Why?

Because convention was strong there.

```text
strong convention
- TTL boundary
- LRU refresh
- meaning of len

→ all four implementations chose the same
```

Where convention is weak — say, which exception a wrong type should raise — the implementations
split.

```text
weak convention
- TypeError?
- ValueError?
- no validation at all?

→ four implementations, three answers
```

So the more accurate conclusion is:

> **Oscillation is not caused by a sparse contract as such, but by places where there is neither
> a contract nor a strong convention.**

---

# 10. The structured prompt was not simply a "find more" prompt

Same model, same code, same number of rounds — and the final code differed sharply by prompt.

v0:

```text
LOC 121
Cognitive Complexity 26
worst function 7
```

Final:

| arm | LOC | Cognitive Complexity | worst function |
|---|---:|---:|---:|
| claude structured | 120.7 | 21.7 | 6.3 |
| claude bare | 150.7 | 32.7 | 10.3 |
| codex structured | 105 | 24 | 9 |
| codex bare | 126 | 29 | 7 |
| fixer given no contract | 178 | 41 | 15 |

In both models the structured condition suppressed code growth relative to bare.

In claude the direction itself reversed.

```text
structured → smaller and simpler
bare       → larger and more complex
```

One honest caveat: Cognitive Complexity and LOC are strongly correlated here.

In this data `r = 0.807`.

So this must not be inflated into "complexity improved independently".

The safer reading:

> the structured prompt suppressed growth in volume and complexity together.

---

# 11. churn behaved like a cost signal, not a quality signal

Per-round changed lines differed enormously by model.

```text
codex bare
10 → 6 → 0 → 0 → 0

codex structured
41 → 16 → 15 → 5 → 8

claude bare
29 → 45 → 73 → 53 → 68

claude structured
69 → 71 → 73 → 49 → 100
```

codex genuinely dries up.

claude does not.

But high churn did not mean worse final code.

The arm that rewrote the most — claude structured — ended up smaller and simpler.

So in this study churn is:

> **a signal of cost and re-review surface, rather than of quality.**

---

# 12. After one big fix, do you have to review again?

The first prescription was simple.

> Review many times, merge the issues, fix once, stop.

One problem remained.

A large fix produces new code.

Shouldn't that be looked at?

So I tested it.

## 12.1 First, control for "new findings appear even without a code change"

Independent reviews of identical code produce new findings purely from sampling variance.

So I enumerated every disjoint combination inside the existing review pool to build the
"novelty rate with no code change".

```text
claude, code unchanged:
median 11%
range 0–31%
```

> **Null distribution** — how far a value ranges when there is no effect at all. Here it is the
> novelty rate with the code unchanged; only a post-fix value outside that range licenses the
> claim that the fix caused it.

Then compared re-reviews after a real fix.

```text
novelty after the fix:
77%
89%
63%
```

Sampling variance does not explain that.

And `74–80%` of the issues handed to the fixer genuinely disappeared from the next review.

So two things are true at once.

1. Fixing everything in one pass does resolve most of the existing issues.
2. A large fix creates a lot of newly written code that has never been reviewed.

The correlation between fix size and the genuinely-new finding rate:

```text
r = 0.837  (n = 6)
```

Small sample, clear direction.

Which makes a different re-review rule natural:

> **Not "which round is this" but "how much changed".**

- small fix → little to harvest from a re-review
- half the file rewritten → that is not a re-review, it is the first review of new code

---

# 13. Does splitting reviewers by category do better?

Many AI review harnesses fan out, for example:

- design
- functionality
- complexity
- robustness
- naming
- style

Each area goes to its own reviewer and the results are merged at the end.

Three conditions were compared.

```text
A. structured, 1 call
B. 6 category calls
C. the same structured prompt, 6 calls
```

C is the important one.

Comparing only B against A shows nothing but "six calls find more than one".

Comparing the same six calls is what isolates the effect of the fan-out structure itself.

## 13.1 On the Python task, fan-out clearly won

### Claude

```text
same structured prompt, 6 calls
distinct issues 19.7
raw findings   69.3

category, 6 calls
distinct issues 30.0
raw findings   54.7
```

For the same six calls:

- distinct issues `+52%`
- raw findings `-21%`

Less for a human to read, more kinds of thing found.

The new material was concentrated in:

- robustness
- naming
- style

— exactly what a general reviewer truncates when it caps output by severity.

## 13.2 It did not reproduce on the C firmware

Same budget on the firmware task:

```text
single reviewer recall: 50%
fan-out recall:         43%
```

> **Recall** — of the real defects that exist, what fraction was found. **Precision** — of the
> findings reported, what fraction was real. They usually trade off: say less and precision
> rises while recall falls. The recall denominator in this study is the set of *known* defects,
> so it is optimistic (§23.5).

The single review was slightly better.

The most plausible reason is that **the review axes did not actually separate**.

The `state-invariant` lens, for instance, pushed attention onto module-internal state — and that
brought back one of the false positives repository access had removed.

So fan-out must not be applied as a general law.

> **Fan-out pays off only where the axes genuinely separate.**

---

# 14. Repository access was the strongest false-positive remover in the study

All four false positives from part 1 could be refuted by looking at another file.

So exactly one thing was changed.

```diff
- you have no other files and no repository.
+ the production source tree is readable.
+ check callers, headers, init path and threading before claiming a defect.
```

`work-docs/` — which holds the answer key — stayed blocked; only `src/` was readable.

## 14.1 Claude's result

```text
                findings   distinct   real   false
file only            61        14      10      4
repo access          30         7       7      0
```

All four false positives vanished.

And it found real defects that a single file cannot establish, such as:

- a time hole left in the ring history after a FIFO overflow
- the interaction of pre-roll and debounce length recording an earlier swing under the later
  swing's key
- low-power 50 Hz samples labelled as 1000 Hz

None of these can be decided from a single file.

## 14.2 The same four false positives died in the other model

codex ran the same condition.

```text
D02  8/10 → 0
D03  7/10 → 0
D04  7/10 → 0
D07  5/10 → 0
```

**Two models from different companies removed the same four false positives.**

It is the strongest cross-model result in the study.

The two models got there by opposite routes.

```text
claude: fewer findings (61 → 30)
codex:  more findings  (27 → 37)
```

Given the repository, one model talked less and the other found more.

What mattered was not the volume of speech but **whether claims could be checked**.

---

# 15. Repository access is not free

It raised precision sharply and lowered recall.

```text
file only
precision 71%
recall    77%

repo access
precision 100%
recall    54%
```

Why?

Because a reviewer that checks the real call path concludes:

> "Possible in theory, but essentially unreachable in practice."

— and reports less.

In the process it drops not only false positives but some low-frequency real defects.

So:

> Repository access is not free.
> **It trades away some faint real defects for the false ones it removes.**

If you need both, run file-only and repo-open side by side.

In this study the union of the two conditions reached 13/13 at 20 calls.

At twice the call cost, of course.

---

# 16. "Give the fixer the contract and regressions stop" was rejected

Early on it looked like this:

```text
no contract  → the fixer accepts nearly every finding
contract     → the fixer declines some
```

So my first thought was:

> Give the fixer the contract and you prevent regressions.

The 2×2 rejected that hypothesis.

```text
                   contract     no contract
C firmware          3/4 broke     4/4 broke
Python              0/40          0/5
```

Fisher exact test:

```text
p = 1.0
```

> **Fisher exact test · p-value** — a test for whether a difference in a small 2×2 table is
> distinguishable from chance. `p = 1.0` means it is not — the presence of a contract does not
> explain the breakage.

The contract does not explain the breakage on the C side.

As shown above, the real cause was **tests pinning an unreachable state**.

So the honest summary now is:

> The contract is not a magic safety device against regressions.

That does not make it useless. Its other effects were clear.

---

# 17. "The contract" was in fact two things

Re-reading the prompt showed that what we called the contract bundled two elements.

```text
A. do not touch code you were not asked about
B. the public interface and behavioural surface are fixed
C. the SPEC that says what that fixed surface actually is
```

B and C were separated and tested.

| what the fixer was given | decline rate | final LOC | cumulative churn |
|---|---:|---:|---:|
| A only | 26% | 254 | 195 |
| A+B | 50% | 237 | 136 |
| A+B+C | 26% | 202 | 191 |

> **Decline rate** — the share of handed-over findings the fixer *explicitly refused, with a
> stated reason* — not the share it quietly ignored. High is not bad and low is not good; the
> information is in what the refusal was grounded on.

Their roles turn out to be different.

### B: "the public surface is fixed"

Suppresses code growth and unnecessary change.

```text
LOC 254 → 237
churn 195 → 136
```

### C: the actual SPEC

Makes the fixer's judgement concrete.

Without a SPEC, anything ambiguous was declined by citing the code's own docstring.

With a SPEC, the fixer quoted acceptance criteria directly.

So the more accurate phrasing:

> **A fixed scope suppresses growth; the SPEC corrects judgement.**

---

# 18. Letting the fixer read the tests but not edit them beats hiding them

Early on the tests were hidden from the fixer, so that they remained an independent oracle.

In practice, though, a fixer who cannot read the tests is the unrealistic setup.

So later experiments used:

- tests readable
- tests not editable

The change mattered more than expected.

Previously, when a review proposed a correct fix outside the module, the narrow test harness
failed to link.

A fixer that could read the tests started making judgements like:

> "This fix would require changing the tests too."

> "The current test pins this behaviour."

> "The problem is real but cannot be fixed within this file."

Build failures that had recurred across an entire loop dropped to zero.

But this is **deferral**, not resolution.

> **accept / decline / defer** — the three verdicts a fixer can return on a finding: fixed,
> "not a problem", and "a real problem that cannot be fixed within this scope". A defer is not
> resolved; if it is not counted, it disappears quietly.

Real problems that fall outside the scope simply do not get fixed.

So read-only test access is a safety device and a scope limiter at the same time.

---

# 19. Running the whole prescription at once broke one more of my beliefs

Late in the study I applied everything I had learned at once.

Everything except the final human triage:

- repository access
- structured review
- fan-out
- issue merging
- fix once
- tests readable / not editable
- size, complexity and churn measured
- a stop rule

On compliance the result was good.

```text
original file-only loop
RED 12 / 15

repo-access loop
RED 6 / 10

full prescription
RED 0 / 4
```

But the same arm grew the code fastest of all (+152% in four rounds). And the stop rule failed.

The prescription said:

> stop when churn approaches zero.

The threshold — 5 lines — was written into the code before the run.

Actual churn:

```text
194 → 262 → 395
```

It rose monotonically.

The loop ended not on churn but **because findings hit zero**.

That is, the loop terminated on the criterion my own prescription had explicitly rejected.

Why did churn dry up on the earlier Python task and grow here?

The most plausible difference is contract density.

But that too is not an experiment with all conditions separated.

So the safe conclusion for now:

> **"Stop when churn converges to zero" is not a universal stop rule.**

On weakly specified code you still need a hard cap such as a round limit.

---

# 20. So how do you end an unbounded review loop?

There were four candidate stop criteria.

```text
1. churn → 0
2. findings → 0
3. a round cap
4. do not repeat the fix loop at all
```

The first three all have problems.

### churn → 0

Fires only under some conditions.

### findings → 0

Means different things per model.

A quiet reviewer may simply have seen less.

### a round cap

Truncation, not convergence.

Which leaves a simpler operational strategy:

> **Do not make the repeated review→fix loop the default.**

---

# 21. How I would run it today

## 21.1 The single most important rule

> **Review many times. Fix once.**

The strongest result in the study.

```text
review only, repeated
real-defect coverage
34% → 61% → 76%

review→fix loop, repeated
compliance gain zero
code size +24% to +152%
```

The gain in discovery comes from the review side.

The risk comes from the fix side.

Binding them into one cycle and spinning it maximises risk per unit of gain.

---

## 21.2 Give the reviewer read access to the repository

The strongest false-positive lever in the study.

```text
file-only
false 4/14

repo-open
false 0
```

And it reproduced in both models.

But you must verify that the access was actually attached.

Several times during the study, what I took for:

> the model just cannot do this

was in fact an environment configuration problem.

### A canary for practice

> **Canary** — a probe that checks the *instrument is actually attached* before you measure
> anything, the way the bird in the mine did. The point is that it must run in both directions:
> something that should be reachable (POS) and something that must not be (NEG). Read a failed
> POS leg as "isolation worked" and you record a run that measured nothing as a success.

Once a month or so, ask the reviewer to do this:

> "Quote line N of the *caller's* file verbatim — not the file you were just shown."

If it cannot, repository access is not really attached.

---

## 21.3 Do not use agreement count as a truth score

In the file-only condition:

```text
mean detection frequency, false   6.8 / 10
mean detection frequency, real    3.4 / 10
```

In this data, agreement was anti-predictive.

When reviewers are all missing the same information, a majority can agree on the same wrong
answer.

---

## 21.4 Mix two models where you can

Enumerating every combination of the existing runs, mixing models beat repeating one.

```text
mixed 3 calls (claude 2 + codex 1)
→ 3.57 real defects on average

claude alone, 6 calls
→ 3.43 on average
```

Mixing perspectives beats repeating one model, and mixing won at every budget of two calls or
more.

This is consistent with the repo-open finding that the two models see *different* real defects.

---

## 21.5 Do not reach for fan-out unconditionally

On the Python task it added +52% distinct issues at the same six calls.

On the C firmware it gained nothing at the same budget.

So the question to ask first is:

> are the review axes genuinely independent?

Design / naming / robustness separate reasonably well.

Concurrency / state invariant / lifetime overlap, and may just spend calls.

---

## 21.6 A human passes over it once

Adjudicating the 39 fan-out findings:

```text
REAL   31%
STYLE  69%
WRONG   0%
```

What is interesting is that the reviewers invented no facts; most findings were naming, comments
and structure.

(The adjudicator was the author of the experiment, and the difference between fan-out-exclusive
and shared findings was not significant, `p = 0.236`.)

Handing all of that to an automatic fixer shakes the code for no reason.

So a human triage step belongs before the final fix.

---

## 21.7 Give the fixer three things

1. the merged issue list
2. a SPEC, or at minimum the scope instruction "the public surface is fixed"
3. read-only tests

And require an explicit verdict on every finding:

```text
accept
decline
defer
```

Receiving a finding is not an instruction to change the code.

---

## 21.8 Do not look at tests alone

Alongside pass/fail, record at least:

```text
test compliance
LOC
complexity
worst-function complexity
churn
```

Compliance was identical across all 47 rounds.

Size and complexity were not.

If the suite is green while the code keeps growing and getting more complex, it is hard to argue
the review loop is improving quality.

---

## 21.9 Decide re-review by fix size, not by round number

Small fix: stop.

Large fix: look again.

But frame it as:

> "There is a lot of newly written code here; this is its first review."

rather than:

> "Let's verify it once more."

---

# 22. If the budget is tight

Every subset of the existing runs was enumerated — no extra calls.

The denominator is the 10 adjudicated real defects; entries are (real found / false found).

| calls | file-only | repo model A | repo model B | repo mixed |
|---:|---:|---:|---:|---:|
| 2 | 5.04 / **3.62 FP** | 2.09 / 0 | 3.07 / 0 | **3.18 / 0** |
| 3 | 6.11 / **3.90 FP** | 2.54 / 0 | 3.27 / 0 | **3.57 / 0** |
| 4 | 6.93 / **3.98 FP** | 2.90 / 0 | 3.40 / 0 | **3.90 / 0** |
| 6 | 8.20 / **4.00 FP** | 3.43 / 0 | 3.60 / 0 | **4.43 / 0** |

File-only finds more per call.

The false positives come with it.

The cost has not disappeared — it moved to the person doing triage later.

### If you can spend two calls

```text
model A once
model B once
```

### If you can spend four

```text
model A twice
model B twice
```

came close to running a single model ten times.

⚠️ The denominator here is the 10 real defects the control condition found. Defects that only
the repo-open arms surfaced are unadjudicated and excluded, so this table is biased **against**
repository access.

---

# 23. What is still unknown

Separating what was established from what was not matters more than the results.

## 23.1 When does fan-out pay off?

It won on Python and did not on C.

"How separable the review axes are" looks like the deciding factor, but how to measure that
separability in advance is unknown.

## 23.2 How do repository access and a narrow lens combine?

Repository access says look outward.

A narrow fan-out lens says concentrate on one internal area.

Where they conflict, false positives that repository access had removed can come back.

There is no stable filtering rule yet.

## 23.3 Can a churn-based stop rule work on large uncontracted code?

In the current data it failed.

Whether another stop signal is needed, or a plain cap is more realistic, needs more work.

## 23.4 "Are there external callers?" versus language and size

The C firmware and the Python task differ in too many ways at once.

An intermediate cell — a Python module with external callers — would separate the causes.

## 23.5 Final adjudication of individual findings

Some groups were adjudicated; the whole set was never re-verified by an independent judge.

The tier-2 results in particular were adjudicated by the author and should be read as a case
study.

Also, the denominator of recall is the set of **known** defects, not the set of defects that
exist. Anything nobody found is in neither the numerator nor the denominator, so every coverage
figure here is biased upward.

## 23.6 Isolation of the experimental environment

A post-hoc audit confirmed repository access was controlled (zero tool calls across 190 session
transcripts), but capabilities were not symmetric between models.

In particular codex offers no way to disable network tools, while they were disabled on the
claude side. Nothing in the logs shows those tools being used — but "the capabilities were
identical" is not a claim that can be made.

## 23.7 Contamination

`retry_policy` and `ttl_cache` are textbook patterns, and it is near certain that every model
measured has seen thousands of similar implementations in training.

That is not disqualifying here, because what is scored is not "can it produce a correct
implementation" but "how does it behave in a loop around code that is already correct". What it
does mean is that **absolute finding counts cannot be compared across tasks** — familiarity buys
more confident commentary.

---

# 24. The thing that changed most in this study was my own conclusions

Sentence after sentence written early on had to be revised.

| what I thought first | what turned out to be true |
|---|---|
| the AI's fixes make the same bug, 4/4 | the tests were pinning a state production never reaches |
| AI review never ends, even on correct code | true for claude; codex genuinely went silent |
| codex stopping early is the superior behaviour | the silent arm may simply have seen far less |
| give the fixer the contract and regressions stop | rejected by the 2×2, `p = 1.0` |
| behaviour outside the contract will wander a lot | across 47 rounds exactly one behaviour moved |
| the less you change, the safer | the arm that changed most ended smaller and simpler |
| repeated findings from many reviewers mean it is real | in file-only, false positives repeated more than real ones |
| after one big fix there is nothing to review | the larger the fix, the more genuinely new findings |
| fan-out only adds noise | on Python, +52% distinct issues and -21% raw findings at the same six calls |
| fan-out is always better | on the C firmware it gained nothing at the same budget |
| stop when churn converges to zero | on the weakly contracted C module it rose, 194→262→395 |
| codex cannot run the repo-access condition | it was a `/tmp` environment configuration problem |

That table is close to being the point of the study.

The subject was AI review, but the AI was not the only thing that kept failing.

- I misread experimental conditions
- I over-trusted tests
- I mistook configuration problems for model properties
- I generalised from one task far too quickly

And each time, the next question changed the conclusion:

> Is it really a bug?

> Does it hold in another model?

> Is that difference the model, or the environment?

> What does this test actually guarantee?

> Beyond passing tests, did the code actually get better?

---

# Conclusion

The first question was simple.

> **How many times should you run an AI code review?**

I now think the question itself is slightly wrong.

Bundling review count and fix count into one "round" erases the distinction that matters.

In this data, the thing worth repeating was the **review**.

Each repetition saw more real defects.

Repeated fixing, by contrast, often left compliance untouched while growing the volume of change
and the risk that comes with it.

So the current answer is:

> ## Review many times. Fix once.
>
> And if the fix is large enough, the next review is not "one more round".
> **It is the first review of newly written code.**

Do not look for the end of AI review in the model's silence.

What matters more:

- can the reviewer see the real context of the code
- do the tests actually pin production behaviour
- how far does the fixer's scope extend
- how much of the code changed
- how did size and complexity move outside the tests
- is the same design decision being reversed over and over

In the end, the better question than "how many times?" is:

> **What should be repeated, and what should happen only once?**
