#!/usr/bin/env bash
# Filesystem-namespace isolation for one model call (harness-bench core).
#
# The load-bearing invariant is NEGATIVE and NAMED: the subject repo
# ($HB_REPO_ROOT) is never bound into the namespace, so an absolute-path read of
# anything inside it -- specs, prior findings, the answer key -- cannot resolve --
# regardless of what tool-restricting flags the CLI does or does not honour.
# This exists because `codex -s read-only` PERMITS reads (it is a shell-exec
# sandbox policy, not a tool switch) and codex has no --disallowed-tools.
#
# Applied to BOTH CLIs. Sandboxing only codex would leave read-capability
# asymmetric between the two models and therefore confounded with model
# identity -- the exact defect class ADR-004 exists to remove.
#
# Usage:  sandbox.sh <scratch-dir> <command> [args...]
#         HB_ALLOW_REPO=1 sandbox.sh ...   # positive-control ONLY
#
# HB_ALLOW_REPO=1 binds the repo read-only. It exists so the Phase 0
# canary has a positive control: a probe that returns "I could not read it"
# proves nothing unless the SAME probe demonstrably CAN read it with isolation
# lifted. Never set it for a matrix run; the runner refuses to.
set -euo pipefail

SCRATCH="${1:?usage: sandbox.sh <scratch-dir> <command> [args...]}"
shift
[ -d "$SCRATCH" ] || { echo "sandbox.sh: scratch dir does not exist: $SCRATCH" >&2; exit 2; }
SCRATCH="$(cd "$SCRATCH" && pwd)"

REPO_ROOT="${HB_REPO_ROOT:-${REPO_ROOT:-}}"
[ -n "$REPO_ROOT" ] || { echo "sandbox.sh: HB_REPO_ROOT must be set (the tree to keep OUT)" >&2; exit 2; }
HOME_DIR="${HOME:?HOME unset}"

# Refuse the footgun outright: a scratch dir inside the repo would be bound rw
# and would drag the repo's parent into the namespace.
case "$SCRATCH/" in
  "$REPO_ROOT"/*) echo "sandbox.sh: scratch dir must live OUTSIDE $REPO_ROOT (got $SCRATCH)" >&2; exit 2;;
esac

args=(
  --unshare-all --share-net --die-with-parent --new-session
  --ro-bind /usr /usr
  --ro-bind /etc /etc
  --symlink usr/lib /lib --symlink usr/lib64 /lib64
  --symlink usr/bin /bin --symlink usr/sbin /sbin
  --proc /proc --dev /dev --tmpfs /tmp
  --bind "$SCRATCH" "$SCRATCH"
  --chdir "$SCRATCH"
  --setenv HOME "$SCRATCH/home"
)

# CLI runtimes, read-only. Each is bound INDIVIDUALLY -- never $HOME_DIR itself,
# because $HOME_DIR contains the repo.
for p in \
  "$HOME_DIR/.local/share/claude" \
  "$HOME_DIR/.local/bin" \
  "$HOME_DIR/.nvm"
do
  [ -e "$p" ] && args+=(--ro-bind "$p" "$p")
done

# Auth/config: the CLIs write here, so bind a per-run COPY the caller staged
# under $SCRATCH/home. Nothing writes back to the real profile.
[ -d "$SCRATCH/home" ] || mkdir -p "$SCRATCH/home"

# HB_ALLOW_SUBDIR=1 binds ONLY $REPO_ROOT/$HB_SUBDIR read-only, for experiments that ask
# what changes when the model can check callers and headers.
# Deliberately NOT the whole repo: the repo may hold the answer key (adjudications, prior findings). Mounting either would let the
# subject read the grading. src/ is the production tree at the frozen baseline and nothing
# in it references the experiment.
# HB_SUBDIR_FROM=<dir> binds THAT directory at $REPO_ROOT/$HB_SUBDIR instead of the real tree.
# A loop experiment needs it: the model must see a subtree whose subject file is the CURRENT
# revision, not the frozen original -- in real life the file under review is the file in the
# repo. It also keeps the real subtree out of the namespace entirely, which matters when an
# oracle swaps the subject in place to run the suite; mounting the live tree would race it.
if [ -n "${HB_SUBDIR_FROM:-}" ]; then
  echo "sandbox.sh: NOTE -- HB_SUBDIR_FROM=$HB_SUBDIR_FROM bound at $REPO_ROOT/$HB_SUBDIR (staged subdir)" >&2
  args+=(--ro-bind "$HB_SUBDIR_FROM" "$REPO_ROOT/$HB_SUBDIR")
  args+=(--ro-bind "$HB_SUBDIR_FROM" "$SCRATCH/$HB_SUBDIR")
fi

if [ "${HB_ALLOW_SUBDIR:-0}" = "1" ]; then
  echo "sandbox.sh: NOTE -- HB_ALLOW_SUBDIR=1, $REPO_ROOT/$HB_SUBDIR is visible (subdir grant)" >&2
  args+=(--ro-bind "$REPO_ROOT/$HB_SUBDIR" "$REPO_ROOT/$HB_SUBDIR")
  # Also inside the scratch. codex enforces its OWN sandbox on top of ours and refuses
  # reads outside the workspace root it was given with -C, so the absolute repo path is
  # unreadable to it even when bwrap has mounted it (verified: /bin/head reads the file,
  # codex reports NOT-READABLE). Binding the same tree a second time at $SCRATCH/src gives
  # both CLIs one path that works. Same inode, read-only, no extra reachability.
  args+=(--ro-bind "$REPO_ROOT/$HB_SUBDIR" "$SCRATCH/$HB_SUBDIR")
fi

# HB_ALLOW_TESTS=1 binds ONLY $REPO_ROOT/$HB_TESTS_SUBDIR read-only. Needed when
# an experiment may grant the fixer test READ but not test edit. We cannot mount a
# Zephyr toolchain in here, so we give the next best thing -- the fixer can READ what the tests
# assert, and the bind is read-only so editing is impossible by construction rather than by
# instruction. The oracle still runs outside the sandbox on the real tree.
# This does NOT leak the answer key: tests/ is the oracle, not the adjudication. work-docs/
# (真/오탐 판정) stays out of the namespace exactly as before.
if [ "${HB_ALLOW_TESTS:-0}" = "1" ]; then
  echo "sandbox.sh: NOTE -- HB_ALLOW_TESTS=1, $HB_TESTS_SUBDIR is visible (tests grant)" >&2
  args+=(--ro-bind "$REPO_ROOT/$HB_TESTS_SUBDIR" "$REPO_ROOT/$HB_TESTS_SUBDIR")
  args+=(--ro-bind "$REPO_ROOT/$HB_TESTS_SUBDIR" "$SCRATCH/$HB_TESTS_SUBDIR")
fi

if [ "${HB_ALLOW_REPO:-0}" = "1" ]; then
  echo "sandbox.sh: WARNING -- HB_ALLOW_REPO=1, repo IS visible (positive control only)" >&2
  args+=(--ro-bind "$REPO_ROOT" "$REPO_ROOT")
fi

exec bwrap "${args[@]}" -- "$@"
