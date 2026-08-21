# harness-bench

**Reproducible measurement of LLM harness design — across models, and over time.**

[한국어](README.ko.md)

When a new model ships, one run puts it in the same table as the others — and produces the
**operating prescription** for it, not just a score.

```
             measured                          →  decided
 claude   grows code 1.258× · churn 0.688       →  cap the loop · no churn stop rule
 codex    shrinks code 0.906× · ends early      →  loop may run longer · cap by rounds
```

> This is **not a model leaderboard.** It measures harness design, not model capability.
> See [`docs/LIMITS.md`](docs/LIMITS.md).

## 📊 Does repeated AI code review converge?

**11 experiments · ~400 model calls · two vendors.** Start here:

| | |
|---|---|
| **[Findings →](docs/FINDINGS.md)** | every measurement, with the numbers |
| **[So how should you review? →](docs/PRESCRIPTION.md)** | the recipe the measurements support |
| **[How it was measured →](docs/METHODS.md)** | every instrument, and how each was validated |
| [Benchmark design and its own results →](docs/REVIEW-BENCH.md) | the reproducible tier-1 runs |
| [Long-form write-up (Korean) →](docs/STUDY-ko.md) | the narrative version |

Four of the results, to give the shape of it:

```
review only, repeated       real-defect coverage 34% -> 61% -> 76%, code risk zero
review->fix loop, repeated  compliance gain ZERO, code +24% to +152%

file-only review            29% of distinct defects were FALSE -- and the false ones were
                            the MOST frequently reported (6.8 detections vs 3.4)
repository access           those false positives drop to 0%, in BOTH vendors' models
```

> **Review many times. Fix once.**

Every instrument is validated before use — the isolation by a two-way canary, the acceptance
suite by deleting a guarantee and checking it notices, the clustering by a stability gate and
a second vendor's model, the differential harness by planted divergences, the free-space
denominator by mutation testing. Where an instrument cannot support a number, it returns
`UNQUOTABLE` or `None` rather than a number with a footnote. See
[`docs/METHODS.md`](docs/METHODS.md).

---

## Quick start

```bash
pip install -e ".[dev]"
pytest -q                                  # boundary + reproduction gates, no model calls

bench canary --model claude                # verify isolation in both directions first
bench run    --model claude --loops 3
bench compare                              # regenerate the ledger
bench prescribe --model claude             # traits → operating prescription
```

## What it produces

Three artefacts per run: **raw** (every call, response, token count, timestamp),
**profile** (the measured traits), and **prescription** (traits mapped to harness settings,
each line carrying an evidence grade).

```
## Operating prescription
  [**]  round_cap     cap the rounds — churn does not converge
  [***] loop_budget   keep the loop short; this model grows the code each round
        ← loc_direction > 1.15

  grades: *** reproduced across models · ** measured once · * judgement
```

An ungraded rule does not render.

## Layout

```
harness_bench/
  core/          knows HOW to measure, not WHAT   (sandbox · runner · cluster · prereg · stats · ledger)
  experiments/
    review_convergence/    does repeated AI code review converge?
```

`core` may not import `experiments`, and may not carry domain vocabulary in code — enforced
by tests, so a second experiment cannot silently inherit the first one's assumptions.

## Disciplines enforced in code

Violations produce a refusal, not a warning.

```
two-way canary   a Canary without both POS and NEG legs raises at construction;
                 require_pass() has no override
no retry         call() has no retry parameter, and a test enforces its absence
ARI gate         below threshold the result is the string UNQUOTABLE, not a number
pre-registration a prediction without a falsification condition is rejected;
                 an edited frozen file fails to load; unregistered runs are branded
evidence grades  a prescription rule without a grade will not render
environment      scratch under /tmp is refused; resolved model ids are recorded,
                 not aliases; adapters declare whether tools can be disabled
```

Rationale for each: [`docs/DESIGN.md`](docs/DESIGN.md) §3.

## Current results

`review_convergence` / `retry_policy`, two models, three loops each — measured 2026-08-21.

| model | calls | cost | loop_decay | churn | rejection | code size | tools blockable |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 30 | $15.74 | −1.25 | does not converge | 0.209 | **1.258×** | yes |
| gpt-5.6-sol | 24 | n/a | −0.25 | not measurable | 0.273 | **0.906×** | **no** |

Across 54 loop rounds, **contract compliance held in every single round** — while reviewers
kept reporting 3–14 findings per pass on code that already passes all 23 acceptance tests.

Full design and results: [`docs/REVIEW-BENCH.md`](docs/REVIEW-BENCH.md)

## Documentation

| | |
|---|---|
| [`docs/METHODS.md`](docs/METHODS.md) | how each number was obtained and each instrument validated |
| [`docs/FINDINGS.md`](docs/FINDINGS.md) | every measurement from the study, with the numbers |
| [`docs/PRESCRIPTION.md`](docs/PRESCRIPTION.md) | the review recipe the measurements support |
| [`docs/STUDY-ko.md`](docs/STUDY-ko.md) | long-form narrative write-up (Korean) |
| [`docs/DESIGN.md`](docs/DESIGN.md) | harness-bench architecture and the six disciplines |
| [`docs/REVIEW-BENCH.md`](docs/REVIEW-BENCH.md) | the review experiment: design, tasks, results |
| [`docs/LIMITS.md`](docs/LIMITS.md) | what this benchmark does not support |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | adding a model, adding an experiment |

## License

Code — **Apache-2.0** ([`LICENSE`](LICENSE)).
Prompts, tasks, data, results — **CC BY 4.0** ([`LICENSE-DATA`](LICENSE-DATA)).
Boundaries in [`NOTICE`](NOTICE).
