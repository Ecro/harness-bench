"""Traits this experiment measures, and the harness knobs they decide.

Core owns the schema and the renderer; the mapping lives here, because what a measurement
implies is domain knowledge and the next experiment brings different knobs.

Grades are mandatory. Some rules below are reproduced across models (***), some are a single
measurement (**), and some are judgement (*). Erasing that distinction launders an opinion
into a recommendation.
"""
from __future__ import annotations

from ...core.ledger.profile import Rule

# `tier` records WHICH TIER CAN MEASURE the trait.
#
# tier-1 (contract-as-oracle) cannot measure two of them, by construction:
#   finds_per_call   counting "real" defects needs an adjudicated defect set, and tier-1's v0
#                    is a verified-correct implementation with no defects to adjudicate.
#   verbosity_shift  it is a contrast between repo access and none, and tier-1 tasks are
#                    single files with no repository.
#
# Unmeasurable traits are left None rather than filled with an estimate. Rules keyed on them
# simply do not fire (Profile.prescribe swallows the KeyError), and the profile shows the gap.
TRAIT_KEYS = {
    "spread":            ("tier-1", "range of finding counts across independent reviews of the same code"),
    "loop_decay":        ("tier-1", "slope of findings per round across the loop"),
    "churn_dries":       ("tier-1", "is the mean churn of the last half below 0.7x the first half (>=4 points)"),
    "churn_ratio":       ("tier-1", "mean churn of the last half / first half"),
    "rejection_rate":    ("tier-1", "fraction of handed-over findings the fixer rejects"),
    "malformed_rate":    ("tier-1", "fraction of responses unparseable despite a structured-output instruction"),
    "ac_held":           ("tier-1", "did contract compliance hold in every loop round"),
    "loc_direction":     ("tier-1", "final LOC / starting LOC. >1 grows, <1 shrinks"),
    "tools_blockable":   ("adapter", "can tools be disabled for this adapter"),
    "finds_per_call":    ("tier-2", "real defects found per call under repo access"),
    "verbosity_shift":   ("tier-2", "change in raw finding count when the repo is opened"),
}

RULES: list[Rule] = [
    Rule("fanout", lambda v: v["finds_per_call"] < 2.0,
         "add category fan-out (only when a 3x call budget is available)", "**",
         "low yield per call; a single reviewer truncates low-frequency findings"),

    # Graded ** rather than ***: the three-loop verdict was a 1:2 split, and the second model
    # cannot be measured on this trait at all (its loops end too early), so "reproduced across
    # models" is structurally unreachable here.
    Rule("round_cap", lambda v: v["churn_dries"] is False,
         "cap the rounds", "**",
         "churn does not converge, so the loop has no self-firing stop condition"),

    Rule("churn_gate", lambda v: v["churn_dries"] is False,
         "do not use churn convergence as a stop rule", "**",
         "verdict was a 1:2 split and the observed ratios straddle the threshold; "
         "read churn_ratio alongside the boolean"),

    Rule("churn_gate", lambda v: v["churn_dries"] is True,
         "churn convergence is usable as a stop rule", "**",
         "this model's edit size shrinks as rounds progress"),

    Rule("churn_gate", lambda v: v["churn_dries"] is None,
         "no basis for a churn stop rule - cap by rounds instead", "*",
         "loops end too early for the series to be judged: not measurable is not the "
         "same as does not converge"),

    Rule("loop_budget", lambda v: v["loc_direction"] > 1.15,
         "keep the loop short - this model grows the code each round", "***",
         "loc_direction > 1.15; the opposite direction was measured on the other model"),

    Rule("loop_budget", lambda v: v["loc_direction"] < 1.0,
         "the loop may run longer - this model does not grow the code", "***",
         "loc_direction < 1.0; it shrinks the code while applying findings"),

    Rule("triage_load", lambda v: v["verbosity_shift"] > 0,
         "budget heavily for human triage - opening the repo makes this model say more", "**",
         "repo access increases the raw finding count for this model"),

    Rule("triage_load", lambda v: v["verbosity_shift"] < -0.3,
         "human triage load is light - but suspect what it dropped", "**",
         "repo access halves the finding count; the terse arm misses things"),

    Rule("repetition", lambda v: v["spread"] >= 3,
         "do not stop at one pass - run-to-run variance is large", "***",
         "finding counts on identical code swing widely between runs"),

    Rule("as_fixer", lambda v: v["rejection_rate"] > 0.45,
         "give the fixer the contract document, not just a scope instruction", "**",
         "high rejection rate: told a surface is fixed with nothing to check against, "
         "a fixer rejects everything ambiguous"),

    Rule("json_contract", lambda v: v["malformed_rate"] > 0.05,
         "treat parse failure as a normal path, not an exception", "**",
         "responses arrive unparseable despite a structured-output instruction"),

    Rule("comparability", lambda v: v["tools_blockable"] is False,
         "not directly comparable with adapters whose tools can be disabled", "*",
         "tools cannot be disabled; the largest open problem in this benchmark, and "
         "judgement rather than measurement"),
]
