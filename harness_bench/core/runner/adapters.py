"""Model adapters. Adding a new model means adding one class here and nothing else.

THE CONTRACT — five things, and a new model must satisfy all five or be marked degraded:

  1. argv()        a headless, single-shot invocation. No REPL, no resume.
  2. STDIN prompt  the subject is delivered on stdin, never argv. 359 lines of C with
                   quotes and `$` would be mangled or blow ARG_MAX, and a silently
                   corrupted subject is the worst failure mode here: everything else is
                   measured against it.
  3. parse()       pull the assistant's final text out of whatever envelope the CLI uses.
  4. usage()       input/output tokens. Missing usage => degraded, never a silent zero.
  5. tool policy   declare whether tools CAN be disabled. codex cannot.

`tools_blockable = False` is not a footnote. Putting a model that cannot be muzzled in the
same table as one that can is the single largest open problem in this benchmark, and the
source study mis-attributed it to model behaviour three separate times. Adapters that
cannot block tools are recorded as such and their rows carry the flag.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from .result import Usage


@dataclass
class Adapter:
    name: str
    model_id: str
    tools_blockable: bool

    def argv(self, cfg: Config, scratch: Path, allow_tools: set[str], extra: list[str]) -> list[str]:
        raise NotImplementedError

    def parse(self, stdout: str) -> tuple[str, str | None, Usage]:
        """-> (assistant text, resolved model id, usage)"""
        raise NotImplementedError

    def stage_home(self, home: Path) -> None:
        """Write adapter-specific config into the scratch HOME."""


_BLOCKABLE = ("Task", "Bash", "Read", "Write", "Edit", "Glob", "Grep",
              "WebFetch", "WebSearch")


class ClaudeAdapter(Adapter):
    def __init__(self, model_id: str = "opus", effort: str = "high"):
        super().__init__("claude", model_id, tools_blockable=True)
        self.effort = effort

    def argv(self, cfg, scratch, allow_tools, extra):
        cfg.require("claude_bin")
        return [
            str(cfg.claude_bin), "-p",
            "--model", self.model_id,
            "--effort", self.effort,
            "--strict-mcp-config",
            # json envelope carries usage + the RESOLVED model id. The prompt the model sees
            # is unchanged, so this does not alter the measured condition.
            "--output-format", "json",
            *extra,
            "--disallowed-tools", *[t for t in _BLOCKABLE if t not in allow_tools],
        ]

    def parse(self, stdout):
        try:
            doc = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout, None, Usage()          # envelope missing -> degraded upstream
        events = doc if isinstance(doc, list) else [doc]
        for e in reversed(events):
            if e.get("type") == "result":
                u = e.get("usage") or {}
                mu = e.get("modelUsage") or {}
                return (
                    e.get("result") or "",
                    next(iter(mu), None),
                    Usage(
                        input_tokens=u.get("input_tokens"),
                        output_tokens=u.get("output_tokens"),
                        cached_input_tokens=u.get("cache_read_input_tokens"),
                        reasoning_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens"),
                        cost_usd=e.get("total_cost_usd"),
                    ),
                )
        return stdout, None, Usage()


class CodexAdapter(Adapter):
    def __init__(self, model_id: str = "gpt-5.6-sol", effort: str = "high"):
        # codex has NO flag to disable tools. `-s read-only` permits reads; it does not
        # remove the capability. This is declared, not worked around.
        super().__init__("codex", model_id, tools_blockable=False)
        self.effort = effort

    def argv(self, cfg, scratch, allow_tools, extra):
        cfg.require("node_bin", "codex_js")
        return [str(cfg.node_bin), str(cfg.codex_js), "exec", "-",
                "--skip-git-repo-check", "-s", "read-only", "--ephemeral",
                "-C", str(scratch), "--json", *extra]

    def stage_home(self, home):
        # Effort goes in the config file, not argv: `-c` overrides are additive, and the
        # config is what the CLI echoes in its own header, so recorded metadata and the
        # actual setting cannot drift apart.
        d = home / ".codex"
        d.mkdir(parents=True, exist_ok=True)
        (d / "config.toml").write_text(
            f'model = "{self.model_id}"\nmodel_reasoning_effort = "{self.effort}"\n'
        )

    def parse(self, stdout):
        text, usage, ver = "", Usage(), None
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            if t == "turn.completed":
                u = d.get("usage") or {}
                usage = Usage(
                    input_tokens=u.get("input_tokens"),
                    output_tokens=u.get("output_tokens"),
                    cached_input_tokens=u.get("cached_input_tokens"),
                    reasoning_tokens=u.get("reasoning_output_tokens"),
                )
            elif t in ("item.completed", "response.output_text.done"):
                item = d.get("item") or d
                if item.get("type") in ("assistant_message", "agent_message", None):
                    text = item.get("text") or item.get("content") or text
            elif t == "session.created":
                ver = (d.get("session") or {}).get("model") or ver
        return (text or stdout), (ver or self.model_id), usage


REGISTRY: dict[str, type[Adapter]] = {"claude": ClaudeAdapter, "codex": CodexAdapter}
