# Limits — what this benchmark does not support

[한국어](LIMITS.ko.md)

**This is not a model leaderboard.** It measures the effect of *harness design*, not which model
is smarter — the question is how a given model should be operated. Quoted as a ranking, it is
being misread.

The harness is the loop, the prompts, the tool access and the stop condition wrapped around a
model. What follows are the constraints that belong beside every number this bench produces.

---

## 1. Evidence grades are part of the result

In this line of work, **only three statements have been reproduced more than once.**

```text
***  repeated review and the fix loop are different activities
***  in a single-file scope, the most confidently reported finding is the most suspect
***  contract compliance discriminates nothing — every condition holds it
```

Everything else was observed once. That is why every prescription line carries a grade, and why
an ungraded rule will not render at all. `***` means reproduced across two or more models or
conditions, `**` measured once, and `*` closer to judgement than to data.

## 2. Model comparison is tier-1 only

tier-1 means a task settled entirely by the contract and its frozen tests, with no human
judgement involved. tier-2 means a case study on a real codebase where a human adjudicated
which findings were real.

Model comparison stands only on tier-1. The tier-2 results embed a human judgement about what
counts as a real defect, so they are a record of *"this is what we saw"*, not a promise that
*"you will get the same numbers"*.

## 3. Recall denominators are optimistic

Recall is the share of the defects that exist which were found — but the denominator is the set
of **known** defects, not the set that exists.

A defect nobody found is in neither the numerator nor the denominator. Every new condition that
surfaces something new enlarges the denominator, so every coverage figure here is biased upward.

## 4. Models that cannot be muzzled

Some CLIs have no flag to disable the model's tools at all. A read-only sandbox policy *permits*
reads; it does not remove the capability.

> Putting a model that can be muzzled and one that cannot in the same table is itself a
> confound.

The current treatment is to **declare** it (`tools_blockable: false`) and brand that row. That
is disclosure, not a fix. Filesystem isolation still holds at the namespace level; symmetry of
capability does not.

## 5. Two tasks, one language

tier-1 is two Python tasks. Nothing here licenses carrying the results to another language or
domain.

One result did in fact reverse when the subject changed: category fan-out gained +52% distinct
findings at the same budget on Python, and gained nothing on the C firmware, where the review
axes overlapped.

## 6. Small n

Most results rest on three loops. Sharp contrasts usually soften as the sample grows.

Traits whose ratios cluster near a threshold are **only judged with three loops or more**, and
the framework refuses a verdict below that.

## 7. Automated runs measure the lower bound

One step of the recommended procedure is *"a human triages the findings"*, and an automated run
removes it. Numbers produced without it are a **floor**, not a ceiling.

## 8. Timing is part of the result

Models change without notice, and an alias can be repointed to a different backend mid-rollout.
So results record the **resolved** model id — not the alias that was requested — along with the
prompt's SHA-256.

Even so, the result files alone cannot always separate a difference between last quarter's
numbers and today's into a change of model or a change of conditions. A row that stops
reproducing is marked `stale`, not deleted.

## 9. Contamination — and why this benchmark's exposure differs

Contamination is when the subject of the measurement is already in the model's training data.

`retry_policy` (exponential backoff + full jitter + circuit breaker) and `ttl_cache` (TTL + LRU)
are **textbook patterns**. It is close to certain that every model measured here saw thousands
of implementations of both in training. For a capability benchmark that would be disqualifying.

Here it is not, and the reason is structural. **This bench does not score whether a model can
produce a correct implementation.** The implementation is given, and is verified correct before
measurement begins — 23/23 on the acceptance suite, itself validated by deleting a guarantee and
checking that the suite notices.

What is measured is **behaviour in a loop around code that is already correct**.

```text
how many findings it reports on correct code, and how much that count varies run to run
whether the count falls as rounds go by
whether the size of its edits converges
whether it grows or shrinks the code while applying findings
what share of handed-over findings it declines, and on what grounds
```

Familiarity with the subject makes these traits **easier** to measure, not harder. A model that
has never seen a circuit breaker would produce noise. The point is **what a model that
understands the code perfectly does when you ask it to review anyway.**

Three things follow, and they bound the claims rather than removing them.

**Absolute finding counts cannot be compared across tasks.** A familiar subject invites more
confident commentary. Finding counts are compared **between conditions within one task**, never
between tasks.

**A model trained on this repository is contaminated in a way that does matter.** The frozen
suites, the reference implementations and the results are all public, so a future model may have
memorised which findings this study adjudicated false. The `task_digest` — a hash of the task
files — carried in every result exists partly for this: it pins which bytes of the task were
measured, so a later re-measurement of the same digest can be set against the earlier one.

**The tier-2 case study uses a private codebase.** The firmware module measured there was not
public at the time, making it the one place in this work where contamination is bounded by
construction rather than by argument. It is also the place where the adjudication is the
author's — one weakness traded for another.

> Contamination is not neutralised here. **Its direction changes** — from "does the model know
> this problem" (where it would have been fatal) to "does it behave the same once it does"
> (the actual question).

---

## Questions this benchmark does not answer

- Whether the design is right, whether it reveals intent, whether the names are accurate — the
  things the canon of code review puts first are **not measured here at all.** Cognitive
  Complexity is a validated proxy for comprehension effort, not comprehension itself.
- Which model is the better programmer.
- Whether any of this holds in your codebase.
