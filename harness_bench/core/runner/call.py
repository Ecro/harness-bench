"""One isolated model call.

Two invariants are enforced by construction, not by convention.

  NO RETRY.  There is no retry parameter and no loop. A failed or malformed call is
  recorded and returned. Retrying until well-formed selects for well-behaved samples and
  biases exactly the variance these experiments measure. If you find yourself wanting a
  retry, what you want is a second INDEPENDENT call, recorded as such.

  PROMPT ON STDIN.  Never argv. A large subject containing quotes, backticks or `$` would be
  mangled or blow ARG_MAX, and a silently corrupted subject is the worst failure here
  because every other number is measured against it.

The subject is placed FIRST at a fixed offset by the caller, with the instruction after it,
so the subject occupies identical token positions regardless of which instruction follows.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from ..config import CONFIG, Config
from .adapters import Adapter, REGISTRY
from .result import CallResult, Usage

_SANDBOX = Path(__file__).resolve().parents[1] / "sandbox" / "sandbox.sh"

# Claude Code exports these into every child; they make a nested `claude -p` behave as a
# child session rather than a clean root invocation.
_STRIP_ENV = (
    "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_PID", "CLAUDE_EFFORT",
)

_CREDENTIALS = (
    (".claude/.credentials.json", ".claude/.credentials.json"),
    (".claude.json", ".claude.json"),
    (".codex/auth.json", ".codex/auth.json"),
)


def stage_home(scratch: Path, adapter: Adapter) -> Path:
    """Copy (never bind) the credentials the CLI needs into the scratch HOME.

    A copy, because the CLIs write to their config dirs and a run must not mutate the
    operator's real profile. Nothing binds $HOME: $HOME may contain the subject repo.
    """
    home = scratch / "home"
    for sub in (".claude", ".codex"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    for rel_src, rel_dst in _CREDENTIALS:
        src = Path.home() / rel_src
        if src.exists():
            dst = home / rel_dst
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            dst.chmod(0o600)
    adapter.stage_home(home)
    return home


def extract_json(text: str) -> dict | None:
    """First balanced top-level JSON object.

    Models wrap output in fences or prepend a sentence despite the instruction. That is a
    formatting slip, not a content failure, and must not be scored as malformed -- the
    malformed rate is a reported cross-model result and inflating it with fence noise would
    make it measure prose habits instead of instruction-following.
    """
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str, esc = True, False
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def call(
    adapter: Adapter | str,
    kind: str,
    prompt: str,
    scratch: Path,
    *,
    cfg: Config = CONFIG,
    allow_tools: set[str] | None = None,
    extra_argv: list[str] | None = None,
    env_extra: dict[str, str] | None = None,
    timeout_s: int = 900,
) -> CallResult:
    if isinstance(adapter, str):
        adapter = REGISTRY[adapter]()
    cfg.require("scratch_root", "bwrap_bin")
    scratch.mkdir(parents=True, exist_ok=True)
    stage_home(scratch, adapter)

    sha = hashlib.sha256(prompt.encode()).hexdigest()
    prompt_file = scratch / f"prompt_{kind}.txt"
    prompt_file.write_text(prompt)

    env = {k: v for k, v in os.environ.items() if k not in _STRIP_ENV}
    env["CODEX_HOME"] = str(scratch / "home/.codex")
    env.update(env_extra or {})

    argv = [str(_SANDBOX), str(scratch),
            *adapter.argv(cfg, scratch, allow_tools or set(), extra_argv or [])]
    started = time.time()
    try:
        with prompt_file.open("rb") as fh:
            proc = subprocess.run(argv, stdin=fh, capture_output=True, text=True,
                                  timeout=timeout_s, env=env)
        stdout, code = proc.stdout, proc.returncode
        reason = proc.stderr[-2000:] if code != 0 else None
    except subprocess.TimeoutExpired:
        return CallResult(adapter.name, kind, "failed", -1, time.time() - started, started,
                          "", None, f"timeout after {timeout_s}s", prompt_sha256=sha)

    wall = time.time() - started
    text, version, usage = adapter.parse(stdout)

    if code != 0 and not text.strip():
        return CallResult(adapter.name, kind, "failed", code, wall, started, stdout, None,
                          reason, version, usage, sha)

    parsed = extract_json(text)
    status = "ok" if parsed is not None else "malformed"
    return CallResult(adapter.name, kind, status, code, wall, started, stdout, parsed,
                      reason if status == "ok" else "no parseable JSON object in response",
                      version, usage, sha)


def save(result: CallResult, out_dir: Path, name: str) -> None:
    """Raw first, always. A malformed response is evidence; losing it to a later error would
    delete the only record of what actually came back."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.raw.txt").write_text(result.raw)
    (out_dir / f"{name}.json").write_text(
        json.dumps(result.to_meta(), indent=2, ensure_ascii=False))
