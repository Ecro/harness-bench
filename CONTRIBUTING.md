# Contributing

[한국어](CONTRIBUTING.ko.md)

How to add a model or an experiment to this repository, and which disciplines may not be
weakened. The reasoning behind the structure is in [`docs/DESIGN.md`](docs/DESIGN.md).

## Install the hooks

```bash
pip install pre-commit && pre-commit install
```

The secret scanner and the gates then run on every commit. `.git/hooks` does not travel with a
clone, so skipping this step leaves the secret defence the documents call three-layered actually
two-layered.

## Adding a model

One `Adapter` in `harness_bench/core/runner/adapters.py`. An adapter is the thin layer that
knows how to invoke that model's CLI and how to read what comes back. **Five obligations:**

```text
argv()        invoke it as a headless one-shot — not an interactive REPL, not a resumed session
STDIN         the prompt goes in on standard input, never in argv — large inputs get truncated
              or exceed the argument-length limit (ARG_MAX), and silently corrupted input is
              the worst failure available here, because every other number is measured
              against it
parse()       pull the final text, the resolved model id and token usage out of the envelope
usage()       input and output tokens. If they are unavailable, mark it `degraded` —
              never a silent zero
tools         declare whether that CLI can disable the model's tools (`tools_blockable`)
```

`parse()` must extract the **resolved** model id because an alias can be repointed to a
different backend mid-rollout. Recording the model that actually answered, rather than the name
that was requested, is what makes a later comparison possible.

`tools_blockable=False` is not a footnote. It is a known confound
([`docs/LIMITS.md`](docs/LIMITS.md) §4) and that adapter's row is branded with it.

Then `bench canary --exp <experiment> --model <name>` must pass. The canary is a probe that
checks the isolation is really in place before anything is measured, and it looks in both
directions — something that should be visible (POS) and something that must not be (NEG).
**A POS-leg failure means the probe is broken, not that isolation worked**, and data collected
in that state is void.

## Adding an experiment

`harness_bench/experiments/<name>/` supplying five things: tasks, prompts, oracle, metrics,
pre-registration. It also ships its own `bench-<name>` skill, for the same reason the code is
split this way.

The CLI discovers the package and drives it through three modules. No other name is imported by
`bench`, and neither the CLI nor `core` may know what any of them mean.

```text
canary.build() / canary.plant(scratch)      the two-way isolation probe
run.measure(model, ...) -> Profile          the measurement
traits.TRAIT_KEYS / traits.RULES            what it measures, and what that decides
```

A `Profile` is the set of measured traits; `TRAIT_KEYS` names and describes them; `RULES` maps
them into harness settings. Every rule carries an evidence grade — `***` reproduced across two
or more models, `**` measured once, `*` judgement. An ungraded rule will not render.

Results carry `"<experiment>/<task>"`, so the ledger (`results/ledger-<experiment>.md`) and
every prescription stay scoped to one experiment's trait vocabulary.

Its documents go in `docs/<experiment>/` — findings, methods, prescription, the long-form, and a
`README.md` as the experiment's front page. Only `DESIGN` and `LIMITS`, which are true of the
suite, stay at the `docs/` root.

If you need to change `core`, ask first whether core is incomplete or whether the boundary is
being crossed. `core` may not import `experiments` and may not carry domain vocabulary in code;
`tests/test_core_boundary.py` enforces both.

## The disciplines are not negotiable

`docs/DESIGN.md` §3 lists six. Removing them yields cleaner numbers, and those numbers are
wrong. Pull requests that weaken any of the following are declined:

- the two-way canary requirement, or an override for `require_pass()`
- a retry parameter — calling again until a response parses keeps only the well-behaved samples,
  and that variance is the thing being measured
- lowering the ARI threshold — including lowering it because a run came back `UNQUOTABLE`.
  `UNQUOTABLE` is the return value that withholds a number when the gate fails, and
  *"it could not be measured"* is itself a publishable result
- prescription rules without an evidence grade

## Do not edit results to agree

If a measurement disagrees with a previous one, record both. A row shown to be an outlier is
marked `superseded_by`, never deleted — the distribution is the finding.
