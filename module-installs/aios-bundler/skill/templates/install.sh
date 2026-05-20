#!/usr/bin/env bash
# install.sh - Stage 1 of the AIOS bundle install.
#
# Usage: bash install.sh <target-dir> [--force]
#
# Stages the 9 core zips + manifest.yaml + INSTALL-PROMPT.md into <target-dir>.
# That is all. No venv, no `.env`, no `gh` calls - those belong to each layer's
# own INSTALL.md, which Claude Code walks during stage 2.
set -euo pipefail

TARGET="${1:-$HOME/aios-new}"
FORCE="${2:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$HERE/manifest.yaml" ]]; then
  echo "ERROR: manifest.yaml not found next to install.sh ($HERE)." >&2
  echo "       Did you extract the tarball first?" >&2
  echo "       tar -xzf aios-bundle-<version>.tar.gz -C /tmp/aios-fresh" >&2
  exit 1
fi

if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null || true)" && "$FORCE" != "--force" ]]; then
  echo "ERROR: $TARGET exists and is not empty. Pass --force as the second arg to override." >&2
  exit 1
fi

mkdir -p "$TARGET"

shopt -s nullglob
zips=("$HERE"/*.zip)
if (( ${#zips[@]} == 0 )); then
  echo "ERROR: no zips found next to install.sh ($HERE)." >&2
  exit 1
fi
cp "${zips[@]}" "$TARGET/"
cp "$HERE/manifest.yaml" "$TARGET/"
cp "$HERE/INSTALL-PROMPT.md" "$TARGET/"

cat <<EOF

  AIOS bundle staged at: $TARGET

  Next steps (stage 2 - Claude Code drives the layer-by-layer install):

    1. cd "$TARGET"
    2. claude .
    3. Paste the contents of INSTALL-PROMPT.md into the chat.
    4. Confirm at each gate.

  The 9 zips + manifest.yaml + INSTALL-PROMPT.md are in place.

EOF
