# Limits — what this benchmark does not support

[한국어](LIMITS.ko.md)

**This is not a model leaderboard.** It measures the effect of *harness design*: not
"which model is smarter" but "how should this model be operated". Cited as a ranking, it is
misread.

---

## 1. Evidence grades are part of the result

Only three statements in this line of work have been reproduced more than once:

```
***  repeated review and the fix loop are different activities
***  in a single-file scope, the most-confidently-reported finding is the most suspect
***  contract compliance discriminates nothing — every arm holds it
```

Everything else has been observed once. This is why every prescription line carries a grade,
and why an ungraded rule does not render at all.

## 2. Tier-1 only, for model comparison

Model comparison rests on tier-1 tasks, where the contract is the oracle and no human
adjudicates. Tier-2 case studies carry human judgement about what is a real defect; they are
recorded as *"this is what we saw"*, not *"you will get the same numbers"*.

## 3. Recall denominators are optimistic

A recall denominator is the set of defects **known**, not the set that exists. Anything nobody
has found appears in neither numerator nor denominator, and the denominator grows every time a
new condition finds something new. All coverage figures are therefore biased upward.

## 4. Models that cannot be muzzled

Some CLIs have no flag to disable tools; a read-only sandbox policy permits reads, it does not
remove the capability.

> Placing a model whose tools can be disabled and one whose tools cannot in the same table is
> itself a confound.

The current handling is to **declare** it (`tools_blockable: false`) and brand that row.
That is disclosure, not a solution. Filesystem isolation still holds via the namespace;
capability symmetry does not.

## 5. Two tasks, one language

Tier-1 is two Python tasks. There is no basis for transferring these results to another
language or domain — and at least one result has already reversed on a different target
(category fan-out gained 52% unique findings at equal budget on Python, and gained nothing on
C firmware, where the lenses overlapped).

## 6. Small n

Most results rest on three loops. Sharp contrasts shrink as n grows; a trait whose ratios
cluster near its threshold needs at least three loops before it is judged at all, and the
framework refuses to judge below that.

## 7. Automated runs measure the lower bound

One step of the recommended process is *"a human triages the findings"*, which an automated
run omits. Numbers produced without it are a floor, not a ceiling.

## 8. Timing is part of the result

Models change without notice, and an alias can be repointed mid-batch. Results record the
**resolved** model id and the prompt SHA-256. Even so, the difference between a figure from
six months ago and today cannot always be attributed to model change versus condition change
from the result file alone. Rows that can no longer be reproduced are marked `stale`, never
deleted.

## 12. Contamination — and why this benchmark's exposure differs

`retry_policy` (exponential backoff, full jitter, a circuit breaker) and `ttl_cache`
(TTL plus LRU) are **textbook patterns**. Every model measured here has almost certainly seen
thousands of implementations of both during training. For a capability benchmark that would
be disqualifying.

It is not disqualifying here, for a structural reason: **this benchmark does not score whether
a model can produce a correct implementation.** The implementation is given, and is verified
correct before measurement begins — 23 of 23 acceptance tests, on a suite that was itself
validated by deleting a guarantee and confirming it is caught.

What is measured is the model's behaviour in a loop around code that is already correct:

```
how many findings it reports on correct code, and how that count varies run to run
whether that count declines as rounds pass
whether the edit size converges
whether it grows or shrinks the code while applying findings
what fraction of handed-over findings it rejects, and on what grounds
```

Familiarity with the subject makes those traits **easier** to elicit, not harder. A model that
has never seen a circuit breaker would produce noise; the point is what a model does when it
understands the code perfectly well and is asked to review it anyway.

Three things follow, and they bound the claim rather than dissolving it:

**Absolute finding counts are not comparable across tasks.** A familiar subject invites more
confident commentary. Counts are compared between arms **on the same task**, never between
tasks.

**A model trained on this repository would be contaminated in the way that matters.** The
frozen suites, the reference implementation and the results are public. A future model could
have memorised which findings this study adjudicated as false. The `task_digest` in every
result exists partly for this: it identifies exactly which task bytes a measurement used, so a
later re-measurement on the same digest can be checked against an earlier one.

**Tier-2 case studies use a private codebase.** The firmware module measured there was not
public when the study ran, which is the one place in this work where contamination is
constrained by construction rather than by argument — and also the place where the adjudication
is the author's, so it trades one weakness for another.

> Contamination is not neutralised here. It is **redirected**: from "does the model know this
> problem" — where it would be fatal — to "does the model behave the same way once it does",
> which is the actual question.

---

## Questions this benchmark does not answer

- Whether a design is right, whether it reveals intent, whether names are accurate — the
  things canonical code review puts first are **not measured here at all**. Cognitive
  Complexity is a validated proxy for comprehension effort, not comprehension itself.
- Which model is the better programmer.
- Whether any of this holds on your codebase.
