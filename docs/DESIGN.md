# Design

[한국어](DESIGN.ko.md)

`harness-bench` measures **harness design**, not model capability. The harness is the loop, the
prompts, the tool access and the stop condition wrapped around a model. The question it answers
is a practical one — *given this model, how should the loop around it be built?*

This document covers that structure, and why each of the six disciplines is enforced in code.

---

## 1. Two layers, one boundary

```text
harness_bench/
  core/                     knows HOW to measure, not WHAT
    sandbox/    filesystem isolation + the two-way canary framework
    runner/     model adapters · calls without retry · token accounting
    cluster/    provenance-blind clustering + the ARI stability gate
    prereg/     frozen predictions · the exploratory brand
    stats/      exhaustive-subset coverage · mutation · differential replay · complexity
    ledger/     result storage · model profiles · prescription rendering
  experiments/
    review_convergence/     tasks · prompts · oracle · metrics · traits
```

**The boundary rule**: `core` may not import `experiments`, and may not carry domain vocabulary
in code. `tests/test_core_boundary.py` enforces both halves.

An experiment supplies core with exactly five things — **tasks, prompts, oracle, metrics,
pre-registration**. The oracle here means whatever decides that a result is right or wrong;
pre-registration means freezing the predictions before the data is seen.

If something else is needed, core is incomplete — that is not a place to bend the boundary. The
boundary is fixed now, while there is only one experiment, because **a benchmark whose
measurement conditions move is not a benchmark.**

## 2. The output is a profile and a prescription, not a score

A score ranks models. A **profile** tells you how to operate the model you already have. The
profile is the set of measured traits; the prescription carries those traits into harness
settings.

```text
measured trait                           →  the knob it decides
────────────────────────────────────────────────────────────
spread          variance between runs     →  how many reviews to run
loop_decay      do findings fall off      →  is a round cap needed
churn_dries     does churn converge       →  can churn be a stop rule
rejection_rate  when used as the fixer    →  must the contract be supplied too
loc_direction   does it grow or shrink    →  how long the loop may run
malformed_rate  JSON compliance           →  can structured output be trusted
tools_blockable can its tools be disabled →  is it comparable at all
```

`spread` is how much the finding count moves across repeated reviews of the same code; `churn`
is the lines added and deleted in a round; `rejection_rate` is the share of findings the fixer
refused with a stated reason; `malformed_rate` is the share of responses that would not parse
despite a structured-output instruction.

The mapping rules belong to the experiment (`traits.py`); core owns the schema and the renderer.
The next experiment brings different knobs.

**Evidence grades are mandatory.** Every rule carries `***` (reproduced across two or more
models), `**` (measured once) or `*` (judgement). An ungraded rule does not render — without a
grade, an opinion is laundered into advice.

## 3. Six disciplines, enforced in code

Each is a runtime gate. A violation produces a refusal, not a warning.

### The two-way canary

A canary is a probe that checks the instrument is actually attached before anything is measured.

*"The model could not read the answer key"* proves nothing by itself, because a broken probe
returns **exactly what perfect isolation returns** — no tools attached, prompt undelivered, CLI
dead, a permission prompt auto-denied; all of them look like "could not read it".

So every isolation claim carries both legs **within the same call**: a **POS** target that
should be reachable and a **NEG** target that must not be. A `Canary` missing either raises at
construction, and `require_pass()` has no override flag. A failure on the POS side is reported
as a **broken probe**, not as isolation.

A canary must also probe only **what that adapter can actually do**. A read-only adapter cannot
be asked to prove isolation by writing.

### No retries

`call()` has no retry parameter, and a test enforces its absence. Calling again until a response
parses **keeps only the well-behaved samples**, and that variance is the thing being measured.

Failed and unparseable calls are recorded and returned as they are. If more samples are needed,
make an **independent call** and record it as an independent observation.

### The ARI gate

Frequency, duplication and coverage mean nothing until findings naming the same defect are
grouped, and a model does the grouping. So it runs three times, shuffling the order every run
(and recording the seed), and compares the three partitions with the Adjusted Rand Index (ARI),
which scores how far two partitions agree — 1.0 is identical.

Below threshold the result is the string `UNQUOTABLE`, not a number. **A number that leaves with
a caveat gets quoted without it.**

The shuffling matters. With identical input order the three runs correlate through
*presentation*, and the gate ends up measuring **prompt determinism** rather than clustering
stability.

### Pre-registration

A prediction with no falsification condition — what result would show it wrong — is a
description, not a prediction, and is rejected at construction. Frozen files are hashed, and
editing one afterwards makes it fail to load.

A run without pre-registration is not forbidden, it is **branded**: `exploratory: true` follows
it into the result and the ledger.

### Prompts derived by machine

Prompt variants are derived from a base by script, and the diff must show **exactly one axis**
changing. The output schema, the per-call cap and permissive clauses such as *"an empty result
is a valid answer"* stay byte-identical.

Delete that last clause and a specialist reviewer is under pressure to say something in its
area; that arm's higher finding count then becomes **an artefact of the prompt** rather than a
measurement. Every result records the prompt's SHA-256.

### Verify the environment before attributing anything

Model behaviour and harness configuration are indistinguishable from the outside. Before
recording a difference as a property of the model, the configuration is verified in both
directions.

Concretely: a scratch root under `/tmp` is refused (some CLIs refuse to materialise sandbox
helpers there, and that failure looks exactly like a model declining to use a capability); the
**resolved** model id is recorded rather than the alias that was requested; and every adapter
declares whether its tools can be disabled at all.

## 4. The reproduction gate

The real risk in a port or a refactor is not a crash but **silent drift** — the code runs, the
numbers look plausible, and nobody checks them against the previous ones.

So stored artefacts are re-analysed with the new code and compared against the earlier values,
**without calling a model.** A reproduction gate that calls a model is not a reproduction; it is
a new experiment.

## 5. Secrets

The runner copies real credentials into a scratch HOME so the CLI can authenticate. Committing
that directory even once cannot be undone, so three layers guard it — `.gitignore`, the
`pre-commit` hook, and CI. All three share `tools/secret_scan.sh` so the patterns cannot drift
apart.

The scanner self-tests against a planted token before every run, because *"nothing found"* is
also what a broken scanner reports.
