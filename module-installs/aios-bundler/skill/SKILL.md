---
name: aios-bundler
description: Repackage the 9 latest-AIOS core zips from module-installs/ into a single portable bundle (tar.gz + install.sh + guided INSTALL-PROMPT.md). The bundle installs onto any fresh machine via a two-stage process - install.sh extracts and prepares the target, then Claude Code walks the operator through 9 layers in order (starter-kit -> context -> data -> infra -> intel -> command -> productivity -> daily-brief -> slash-commands). After all layers install, the 9 zips + manifest are archived into module-installs/latest-aios/core/ so the target matches the canonical AIOS layout. Use when shipping AIOS to a client or to a new personal machine.
argument-hint: "[--source <zips-dir>] [--out <dist-dir>] [--version <YYYY-MM-DD>]"
flags:
  - name: --source
    description: Path to folder containing the 9 core zips. Default - module-installs/latest-aios/core/
    cost: Free
  - name: --out
    description: Parent directory for per-build folders. Default - outputs/aios-bundles.
    cost: Free
  - name: --version
    description: Bundle version stamp. Default - today's date YYYY-MM-DD.
    cost: Free
---

# aios-bundler

Repackages the 9 core AIOS zips into a single portable tarball with a 2-stage guided installer. Pure-input: reads only from `--source`, never the surrounding workspace.

## When to use

- Shipping AIOS to a client on a fresh machine.
- Setting up AIOS on a new personal machine.
- Producing a reproducible, sha256-pinned snapshot of the current core for archival.

## Prerequisites

- All 9 core zips present in `--source` (defaults to `module-installs/latest-aios/core/`):
  `context-os-v1.zip`, `data-os-v1.zip`, `infra-os-v1.zip`, `intel-os-v1.zip`,
  `command-os-v1.zip`, `productivity-os-v1.zip`, `daily-brief-v1.zip`,
  `slash-commands-v1.zip`, `aios-starter-kit.zip`.
- `pyyaml` available in `.venv` (already in `requirements.txt`).
- macOS or Linux. Windows is out of scope for this version.

## How to invoke

```bash
.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py \
    --source module-installs/latest-aios/core \
    --out outputs/aios-bundles \
    --version 2026-05-11
```

All flags optional. With no flags, `pack.py` uses the defaults above and stamps the version with today's date.

## What the bundle contains

`aios-bundle-<version>.tar.gz` (12 entries at the tarball root):

- 9 core zips, verbatim.
- `manifest.yaml` - version, generated_at, source_dir, install_order, gates, per-zip `{path, sha256, bytes}`.
- `install.sh` - stage-1 bootstrap (extracts staged files into a target dir).
- `INSTALL-PROMPT.md` - stage-2 prompt for Claude Code on the target machine.

Sibling files in the build folder (kept next to the tarball, never inside it):

- `BUNDLE.json` - version, sha256_of_tarball, file_count, generated_at, source_dir, zip_count.
- `manifest.yaml` - the same manifest shipped inside the tarball, copied out for traceability.

## How the operator runs the bundle on the target

1. `tar -xzf aios-bundle-<version>.tar.gz -C /tmp/aios-fresh`
2. `bash /tmp/aios-fresh/install.sh ~/aios-target`
3. `cd ~/aios-target && claude .`
4. Paste the contents of `INSTALL-PROMPT.md`. Claude Code drives the 9-layer install with a gate at infra.

## Install order (locked)

`starter-kit -> context -> data -> infra -> intel -> command -> productivity -> daily-brief -> slash-commands`

Rationale lives in `reference/install-order.md`. Confirmation gate at `infra-os-v1.zip` (creates a remote - irreversible).

## Post-install archive

After all 9 layers install, `INSTALL-PROMPT.md` instructs Claude Code to move the 9 zips + `manifest.yaml` from the target workspace root into `module-installs/latest-aios/core/` (creating the directory if needed). This leaves the installed workspace matching the canonical AIOS layout and able to re-bundle itself later via this same skill. `INSTALL-PROMPT.md` stays at the workspace root for reference.

## Out of scope

- Modules and sub-modules. Same shape, longer manifest, future workshop.
- Drift audit (workspace vs. modules). Future skill `aios-drift-audit`.
- Three-way merge update flow. Future workshop `aios-update`.
- Windows installer.
- Bundle distribution (S3 / GH Release / share) - left to the operator.

## Why pure-input

`pack.py` only reads from `--source`. It never opens `.env`, `credentials/`, or any other workspace path. There is no scanning or scrubbing because the surface area where a secret could leak does not exist. This is load-bearing: members can build a bundle inside their personal AIOS without risk of leaking client work.
