# Contributing


## Set up the hooks

```bash
pip install pre-commit && pre-commit install
```

The secret scanner and the gates run on every commit. `.git/hooks` does not travel with a
clone, so without this step you have two layers of secret protection where the
documentation claims three.

## Adding a model

One `Adapter` in `harness_bench/core/runner/adapters.py`. **Five obligations:**

```
argv()        a headless single-shot invocation — no REPL, no resume
STDIN         the prompt goes on stdin, never argv: large inputs are truncated or
              exceed ARG_MAX, and a silently corrupted input is the worst failure
              mode here, since every other number is measured against it
parse()       extract final text, resolved model id, and token usage from the envelope
usage()       input/output tokens — missing usage is `degraded`, never a silent zero
tools         declare whether tools can be disabled (`tools_blockable`)
```

`tools_blockable=False` is not a footnote. It is a known confound (`docs/LIMITS.md` §4) and
that adapter's rows are branded.

Then `bench canary --model <name>` must pass. A POS-leg failure means the probe is broken,
not that isolation worked, and data collected in that state is void.

## Adding an experiment

`harness_bench/experiments/<name>/` supplying five things: tasks, prompts, oracle, metrics,
pre-registration.

If you need to change `core`, ask first whether core is incomplete or whether the boundary is
being crossed. `core` may not import `experiments` and may not carry domain vocabulary in
code; `tests/test_core_boundary.py` enforces both.

## The disciplines are not negotiable

`docs/DESIGN.md` §3 lists six. Removing them yields cleaner numbers, and those numbers are
wrong. Pull requests that weaken any of the following are declined:

- the two-way canary requirement, or an override for `require_pass()`
- a retry parameter
- lowering the ARI threshold — including lowering it because a run came back `UNQUOTABLE`
- prescription rules without an evidence grade

## Do not edit results to agree

If a measurement disagrees with a previous one, record both. A row shown to be an outlier is
marked `superseded_by`, never deleted — the distribution is the finding.
