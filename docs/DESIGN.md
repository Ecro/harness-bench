# Design

[한국어](DESIGN.ko.md)

`harness-bench` measures **harness design**, not model capability. It answers a practical
question: *given this model, how should the loop around it be configured?*

---

## 1. Two layers, one boundary

```
harness_bench/
  core/                     knows HOW to measure, not WHAT
    sandbox/    filesystem isolation + two-way canary framework
    runner/     model adapters · no-retry call · token accounting
    cluster/    provenance-blind grouping + ARI stability gate
    prereg/     frozen predictions · exploratory branding
    stats/      exhaustive coverage · mutation · differential replay · complexity
    ledger/     result store · model profile · prescription rendering
  experiments/
    review_convergence/     tasks · prompts · oracle · metrics · traits
```

**The boundary rule:** `core` may not import `experiments`, and may not carry domain
vocabulary in code. Enforced by `tests/test_core_boundary.py`.

An experiment supplies exactly five things — **tasks, prompts, oracle, metrics,
pre-registration**. Anything else it needs means core is incomplete, not that the boundary
should bend. The boundary is fixed now, while there is one experiment, because a benchmark
whose measurement conditions shift is not a benchmark.

## 2. Output is a profile and a prescription, not a score

A score ranks models. A **profile** tells you how to operate the one you have.

```
measured trait                        →  harness knob it decides
────────────────────────────────────────────────────────────────
spread          run-to-run variance   →  how many review passes
loop_decay      do findings decline   →  is a round cap needed
churn_dries     does churn converge   →  can churn be a stop rule
rejection_rate  as a fixer            →  does it need the contract document
loc_direction   grows or shrinks code →  how long the loop may run
malformed_rate  JSON adherence        →  can structured output be trusted
tools_blockable can tools be disabled →  is it comparable at all
```

Mapping rules live with the experiment (`traits.py`); core owns the schema and the renderer.
The next experiment brings different knobs.

**Evidence grades are mandatory.** Every rule carries `***` (reproduced across models),
`**` (measured once), or `*` (judgement). A rule without a grade will not render — an
ungraded recommendation launders opinion into advice.

## 3. Six disciplines, enforced in code

Each is a runtime gate. Violations do not produce a warning; they produce a refusal.

### Two-way canary

*"The model could not read the answer key"* proves nothing on its own: a broken probe returns
the same answer as perfect isolation — no tools attached, prompt undelivered, CLI dead,
permission prompt auto-denied.

Every isolation claim carries both legs in the same invocation: a **POS** target that must be
reachable, and a **NEG** target that must not be. A `Canary` missing either leg raises at
construction. `require_pass()` has no override flag, and a POS-side failure is reported as a
broken probe, not as isolation.

A canary must also probe only what the adapter can actually do. A read-only adapter cannot
demonstrate isolation by writing.

### No retry

`call()` has no retry parameter, and a test enforces its absence. Retrying until a response
is well-formed selects for well-behaved samples and biases the very variance being measured.
A failed or malformed call is recorded and returned; if you want another sample, make an
independent call and record it as one.

### ARI gate

Findings must be grouped before frequency, overlap or coverage mean anything, and the
grouping is done by a model. Three runs, shuffled per run with a recorded seed, and the
partitions compared by Adjusted Rand Index.

Below threshold the result is not a number — it is the string `UNQUOTABLE`. A number carried
with a caveat gets cited without the caveat.

Shuffling matters: identical input order would correlate the runs through presentation and
make the gate measure prompt determinism instead of clustering stability.

### Pre-registration

A prediction without a falsification condition is a description, and is rejected at
construction. Frozen files are hashed; editing one after the fact fails to load.

A run without a pre-registration is not forbidden — it is **branded**. `exploratory: true`
travels into the result and into the ledger.

### Machine-derived prompts

Prompt variants are derived from a base by script, and the diff must show exactly one axis
changing. Output schema, caps, and permissive clauses such as *"an empty result is a valid
answer"* stay byte-identical: removing that one clause turns a fan-out arm's finding count
into an artefact of the prompt. Every result records the prompt SHA-256.

### Environment before attribution

Model behaviour and harness configuration are indistinguishable from the outside. Before a
difference is recorded as a model property, the configuration is verified in both directions.
Concretely: scratch roots are refused under `/tmp` (a CLI may refuse to materialise sandbox
helpers there), resolved model ids are captured rather than aliases, and adapters declare
whether tools can be disabled at all.

## 4. Reproduction gate

Porting risk is not a crash; it is silent drift — the code runs, the numbers look plausible,
nobody compares them to before. So stored artefacts are re-analysed by the new code and
checked against the prior values, **without calling a model**. A reproduction gate that calls
a model is not reproducing anything; it is running a new experiment.

## 5. Secrets

The runner copies real credentials into a scratch HOME so the CLIs can authenticate. One
commit of that directory is irreversible, so three layers guard it: `.gitignore`, a
`pre-commit` hook, and CI — all three sharing `tools/secret_scan.sh` so the patterns cannot
diverge.

The scanner self-tests against a planted token before every run. *"Nothing found"* is the
same output a broken scanner produces.
