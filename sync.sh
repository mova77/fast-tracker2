#!/usr/bin/env bash
# Sync this tree with 8bitbubsy/ft2-clone (one-way pull).
# Prefer rebase / fast-forward — never create a merge commit.
#
# Usage:
#   ./sync.sh              # fetch + rebase current branch onto upstream/master
#   ./sync.sh --ff-only    # refuse to rewrite; only allow fast-forward
#   ./sync.sh --push       # after successful sync, push current branch to origin
#   ./sync.sh --status     # show ahead/behind only (no rebase)
#   ./sync.sh --dry-run    # fetch + show what would happen, do not rebase

set -euo pipefail

UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-upstream}"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/8bitbubsy/ft2-clone.git}"
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-master}"
ORIGIN_REMOTE="${ORIGIN_REMOTE:-origin}"

DO_PUSH=0
FF_ONLY=0
STATUS_ONLY=0
DRY_RUN=0

usage() {
  # Print the leading "# Usage:" comment block from this file.
  awk '
    NR == 1 { next }
    /^#/ {
      line = $0
      sub(/^# ?/, "", line)
      print line
      next
    }
    { exit }
  ' "$0"
  exit "${1:-0}"
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage 0 ;;
    --push) DO_PUSH=1 ;;
    --ff-only) FF_ONLY=1 ;;
    --status) STATUS_ONLY=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *)
      echo "unknown option: $arg" >&2
      usage 1
      ;;
  esac
done

# Resolve repo root (script may live at root or under scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
else
  REPO_ROOT="$(git rev-parse --show-toplevel)"
fi
cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not a git repository" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "error: working tree has local modifications; commit or stash first" >&2
  git status -sb
  exit 1
fi

# Ensure upstream remote points at ft2-clone
if git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
  current_url="$(git remote get-url "$UPSTREAM_REMOTE")"
  if [[ "$current_url" != *"8bitbubsy/ft2-clone"* ]]; then
    echo "warning: $UPSTREAM_REMOTE currently is: $current_url" >&2
    echo "         expected ft2-clone; updating to $UPSTREAM_URL" >&2
    git remote set-url "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
  fi
else
  echo "adding remote $UPSTREAM_REMOTE -> $UPSTREAM_URL"
  git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
fi

echo "fetching $UPSTREAM_REMOTE..."
git fetch "$UPSTREAM_REMOTE"

UP_REF="${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}"
if ! git rev-parse --verify "$UP_REF" >/dev/null 2>&1; then
  echo "error: missing $UP_REF after fetch" >&2
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" ]]; then
  echo "error: detached HEAD; checkout a branch first" >&2
  exit 1
fi

# left = commits on HEAD not in upstream; right = commits on upstream not in HEAD
read -r AHEAD BEHIND < <(git rev-list --left-right --count "HEAD...${UP_REF}")

echo
echo "branch:   $BRANCH"
echo "upstream: $UP_REF ($(git rev-parse --short "$UP_REF"))"
echo "tip:      $(git rev-parse --short HEAD)"
echo "vs upstream: ${AHEAD} ahead, ${BEHIND} behind"
echo

if (( STATUS_ONLY )); then
  if (( BEHIND > 0 )); then
    echo "commits to bring in:"
    git log --oneline "HEAD..${UP_REF}"
  else
    echo "already up to date with upstream."
  fi
  exit 0
fi

if (( BEHIND == 0 )); then
  echo "already up to date with upstream (nothing to rebase)."
else
  if (( DRY_RUN )); then
    echo "[dry-run] would apply these commits onto $BRANCH:"
    git log --oneline "HEAD..${UP_REF}"
    echo
    if (( FF_ONLY )); then
      echo "[dry-run] mode: --ff-only (git merge --ff-only $UP_REF)"
    else
      echo "[dry-run] mode: rebase onto $UP_REF"
    fi
    exit 0
  fi

  echo "bringing in ${BEHIND} upstream commit(s):"
  git log --oneline "HEAD..${UP_REF}"
  echo

  if (( FF_ONLY )); then
    # Only succeeds if our tip is an ancestor of upstream (no unique local commits).
    git merge --ff-only "$UP_REF"
  else
    # Linear history: replay our commits on top of upstream.
    git rebase "$UP_REF"
  fi
  echo
  echo "synced. new tip: $(git rev-parse --short HEAD)"
  read -r AHEAD BEHIND < <(git rev-list --left-right --count "HEAD...${UP_REF}")
  echo "vs upstream: ${AHEAD} ahead, ${BEHIND} behind"
fi

if (( DO_PUSH )); then
  echo
  echo "pushing $BRANCH to $ORIGIN_REMOTE..."
  # After rebase, force-with-lease is required if the branch was already published
  # with different SHAs. Try a plain push first, then lease-protected force.
  if git rev-parse --verify "${ORIGIN_REMOTE}/${BRANCH}" >/dev/null 2>&1; then
    if git push "$ORIGIN_REMOTE" "$BRANCH" 2>/tmp/sync-push.err; then
      echo "pushed."
    else
      if grep -qE 'non-fast-forward|fetch first|rejected' /tmp/sync-push.err 2>/dev/null; then
        echo "plain push rejected (history rewritten); using --force-with-lease"
        git push --force-with-lease "$ORIGIN_REMOTE" "$BRANCH"
        echo "pushed (--force-with-lease)."
      else
        cat /tmp/sync-push.err >&2
        exit 1
      fi
    fi
  else
    git push -u "$ORIGIN_REMOTE" "$BRANCH"
    echo "pushed (new upstream branch)."
  fi
  rm -f /tmp/sync-push.err
fi
