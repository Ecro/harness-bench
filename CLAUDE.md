# harness-bench — working agreement

This repository measures LLM harness design. Its value is not the numbers; it is that the
numbers are **trustworthy**. Every rule below exists because the opposite produces cleaner,
wronger results.

Read [`docs/DESIGN.md`](docs/DESIGN.md) before changing anything under `harness_bench/core/`.

---

## Before you measure anything

Load two skills, not one:

```
bench-measure                the procedure and gates common to EVERY experiment
bench-<experiment>           that experiment's tasks, budget, trait meanings, results
```

The split mirrors the `core` / `experiments` boundary the code already enforces. A new
experiment ships its own `bench-<name>` skill; do not grow `bench-measure` with
experiment detail.

The short version:

```bash
bench canary    --exp <experiment> --model <name>   # MUST pass, in BOTH directions, first
bench run       --exp <experiment> --model <name> --loops 3
bench compare   --exp <experiment>                 # -> results/ledger-<experiment>.md
bench prescribe --exp <experiment> --model <name>
```

A canary failure on the **POS** side is not isolation working — it is a broken probe, and
every number collected in that state is void. Do not proceed. Do not work around it. Diagnose
the environment.

`--loops 3` is not a suggestion. Traits whose ratios cluster near a threshold are refused a
verdict below three loops, and a single loop's direction is a sample, not a direction.

## Hard rules

**Never add a retry.** `call()` has no retry parameter and `tests/test_core_boundary.py`
enforces its absence. Retrying until a response parses selects for well-behaved samples and
biases the variance being measured. If you want another sample, make an independent call and
record it as one.

**Never lower a gate to get an answer.** Not the ARI threshold, not `MIN_LOOPS`, not
`MIN_POINTS`. If a run comes back `UNQUOTABLE` or `None`, that IS the result. "Not measurable"
is a publishable finding; a number obtained by relaxing its own gate is not.

**Never edit a frozen artefact.** `harness_bench/experiments/*/tasks/*/` — `SPEC.md`,
`test_acceptance.py`, `reference.py` — were authored before any implementation existed. That
freeze is the only defence against *"the tests were fitted to the implementation"*. This
includes comments and includes translating them.

**Never make results agree.** If a measurement contradicts an earlier one, keep both. Mark the
superseded row `superseded_by` with a note; do not delete it. The distribution is the finding.

**Never ship an ungraded prescription rule.** Every `Rule` carries `***` / `**` / `*`. An
ungraded rule will not render, by design — it would launder judgement into advice.

## The core/experiments boundary

`core` knows HOW to measure. It does not know WHAT is being measured.

- `core` may not import `experiments`.
- `core` may not carry domain vocabulary in code (docstrings explaining rationale are fine).
- An experiment supplies exactly five things: tasks, prompts, oracle, metrics, pre-registration.
- An experiment also ships its own `bench-<name>` skill, for the same reason.

If you need something else from core, core is incomplete — say so rather than reaching across.
`tests/test_core_boundary.py` enforces both halves.

## Before attributing anything to a model

Model behaviour and harness configuration are indistinguishable from the outside. Before
recording a difference as a model property, verify the configuration in both directions:

- Did the adapter actually have the tools the probe needed?
- Is the scratch root outside any temporary directory?
- Is the **resolved** model id recorded, or just the alias you asked for?
- Can this adapter disable tools at all (`tools_blockable`)?

A canary POS leg exists to separate "the model did not use the capability" from "the
capability was never attached". They look identical in the output.

## Prompts

Prompt variants are **derived by script** from a base, and the diff must show exactly one axis
changing. Output schema, caps, and permissive clauses such as *"an empty result is a valid
answer"* stay byte-identical — removing that clause turns a finding count into an artefact of
the prompt. Every result records the prompt SHA-256.

## Documentation

Every user-facing document is **bilingual**: `X.md` (English) and `X.ko.md` (Korean),
cross-linked at the top. Code comments and CLI output are English.

Write about design and results. Do not write project history or narrate mistakes — state the
technical reason a rule exists, not the incident that produced it.

## Secrets

The runner copies real credentials into a scratch HOME. `.gitignore`, the `pre-commit` hook and
CI all call `tools/secret_scan.sh`; do not weaken any of the three, and do not add a bypass.
The scanner self-tests against a planted token before every run, because *"nothing found"* is
also what a broken scanner reports.

## Checks before you commit

```bash
pytest -q                         # boundary + reproduction + regression, no model calls
./tools/secret_scan.sh staged
```

If you touched an oracle or a task, also:

```bash
python -c "from harness_bench.experiments.review_convergence.tasks import TASKS; \
           from harness_bench.experiments.review_convergence import oracle; \
           [oracle.verify(t) for t in TASKS.values()]"
```

No number from a task is quotable until `oracle.verify()` passes.
