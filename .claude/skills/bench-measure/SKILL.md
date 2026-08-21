---
name: bench-measure
description: The invariant measurement procedure for any harness-bench experiment — canary, oracle gate, run, ledger, prescription — and the rules for reading the output honestly. Use whenever asked to benchmark, measure, or profile a model in the harness-bench repository, or when adding a new model adapter. Experiment-specific detail (tasks, call budget, what each trait means) lives in that experiment's own skill; load both.
---

# Measuring — the invariant procedure

This applies to **every** experiment in this repository. It deliberately contains nothing
experiment-specific: what a trait means, what a run costs, and which tasks exist belong to the
experiment's own skill (`bench-<experiment>`). Load that one too.

The ordering is not stylistic. Each step gates the next, and skipping one produces numbers
that look fine and are void.

## 0. Environment

```bash
export HB_REPO_ROOT="$PWD"        # the tree that must stay OUT of the namespace
```

Scratch defaults to `~/.cache/harness-bench` and **must not sit under a temporary directory**.
Some CLIs refuse to materialise sandbox helpers there and then fail opaquely on their first
shell command — indistinguishable, from the outside, from a model declining to use a
capability. `Config.require()` refuses such a root outright.

## 1. Canary — both directions

```bash
bench canary --exp <experiment> --model <name>
```

Read every leg. **If any POS leg fails, stop.**

A POS failure means the probe is broken, not that isolation worked: no tools attached, prompt
undelivered, CLI dead, permission prompt auto-denied. All of them return the same "not
reachable" that perfect isolation returns. Data collected in that state is void.

Diagnose before rerunning. The raw response is saved at
`~/.cache/harness-bench/canary/<experiment>/<model>/canary.raw.txt` — read it rather than guessing. Causes
are environmental, not behavioural:

- the probe needed tools the run did not grant
- the adapter is read-only and the leg asked it to write
- reads outside the working directory were auto-denied as permission prompts

A POS leg must only ask for something **that adapter can actually do**.

## 2. Oracle gate

`bench run` calls `oracle.verify()` first and refuses to proceed if it fails. Do not bypass it.

```
reference passes            the known-good implementation is green
import failure floors       an unimportable module scores 0, not "everything passed"
single-guarantee removal    deleting one guarantee is caught by the suite
```

A suite that stays green after a guarantee is removed is not measuring that guarantee, and no
number from that task is quotable.

## 3. Run

```bash
bench run --exp <experiment> --model <name> --loops 3
```

`--loops 3` is the floor for every experiment. Traits whose ratios cluster near a threshold are
refused a verdict below three loops — one loop's direction is a sample, not a direction.

Runs take tens of minutes. Launch in the background and wait for completion rather than polling
in a foreground loop.

**A failed or malformed call is never retried.** The loop stops there and only the observations
up to it are used. That is deliberate: retrying until a response parses selects for well-behaved
samples and biases the variance being measured.

## 4. Ledger and prescription

```bash
bench compare   --exp <experiment>
bench prescribe --exp <experiment> --model <name>
```

Read the caveats block under the table. `EXPLORATORY`, `TOOLS-UNBLOCKABLE` and `COST-UNKNOWN`
travel with the row and are part of the result.

## 5. Reading the output honestly

| output | meaning |
|---|---|
| `UNQUOTABLE` | the clustering did not reproduce; there is no number to cite |
| trait `None` | not measurable under these conditions — **not** zero, and not "no effect" |
| `split n:m` | a majority verdict that was not unanimous; read the continuous value too |
| `degraded` | the measurement itself was incomplete |

If a result contradicts an earlier one, **keep both**. Mark the superseded row `superseded_by`
with a note explaining what changed. The distribution is the finding.

**Never lower a gate to obtain a verdict** — not the ARI threshold, not `MIN_LOOPS`, not
`MIN_POINTS`. "Not measurable" is a publishable result; a number produced by relaxing its own
gate is not.

## 6. Adding a model adapter

One `Adapter` in `harness_bench/core/runner/adapters.py`, satisfying five obligations: headless
argv, prompt on stdin, `parse()` returning text + resolved model id + usage, usage or
`degraded`, and a `tools_blockable` declaration.

Declare `tools_blockable=False` honestly when the CLI cannot disable tools. It is a known
confound, the row is branded, and hiding it corrupts every comparison in the table.

Then return to step 1. A new adapter is not measured until its canary passes.

## 7. Adding an experiment

An experiment supplies exactly five things — tasks, prompts, oracle, metrics, pre-registration —
and **ships its own `bench-<name>` skill** covering its tasks, call budget, trait meanings and
how to read its particular results. Do not extend this skill with experiment detail; that is the
same boundary `core` and `experiments` already enforce in code.
