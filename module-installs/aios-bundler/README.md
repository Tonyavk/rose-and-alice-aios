# aios-bundler (share package)

> A Claude Code skill that packages your 9 core AIOS module zips into a single portable `.tar.gz` with a guided installer. Hand the resulting bundle to a teammate (or a fresh laptop) and the recipient walks through a 9-layer install with a single confirmation gate.

## What this does

- Takes 9 named AIOS core zips from `module-installs/latest-aios/core/`.
- Produces `aios-bundle-<version>.tar.gz` + sha256-pinned `BUNDLE.json` + `manifest.yaml` in `outputs/aios-bundles/<version>/`.
- The recipient runs `tar -xzf ... && bash install.sh <target>` (stage 1), then pastes `INSTALL-PROMPT.md` into Claude Code (stage 2). Claude walks them through the 9 layers in the locked order, pauses at the one irreversible step (infra creates a remote), and archives the zips into `module-installs/` at the end.

## What you need

- An AIOS workspace with the 9 core zips present in `module-installs/latest-aios/core/`:
  `aios-starter-kit.zip`, `context-os-v1.zip`, `data-os-v1.zip`, `infra-os-v1.zip`, `intel-os-v1.zip`, `command-os-v1.zip`, `productivity-os-v1.zip`, `daily-brief-v1.zip`, `slash-commands-v1.zip`.
- Python 3.10+ with `pyyaml` available (the installer will set this up if you have a `.venv`).
- Claude Code installed.
- macOS or Linux. Windows is not supported.

## How to install

Drop this folder onto the target machine, then in Claude Code say:

> Read `shares/aios-bundler/INSTALL.md` and help me set this up.

Claude walks you through the install step by step. ~5 minutes if you already have a `.venv`.

## Running cost

Free. The skill is pure-input — it only reads `--source` and writes to `--out`. No external APIs, no API keys, no databases.

## Files in this package

```
shares/aios-bundler/
├── INSTALL.md                                  # Claude-guided install (this is the entry point)
├── README.md                                   # This file
├── requirements.txt                            # Python deps (pyyaml)
└── skill/                                      # The aios-bundler skill — drop into .claude/skills/aios-bundler/
    ├── SKILL.md                                # Skill frontmatter + invocation guide
    ├── scripts/pack.py                         # Packer
    ├── templates/manifest.template.yaml        # Locked install order + gates
    ├── templates/install.sh                    # Stage-1 bootstrap
    ├── templates/INSTALL-PROMPT.md             # Stage-2 prompt for Claude Code on the target
    └── reference/install-order.md              # Rationale for the 9-layer order
```

## Where the bundles end up

After install, run the skill with:

```bash
.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py --version 2026-05-11
```

The tarball lands in `outputs/aios-bundles/2026-05-11/aios-bundle-2026-05-11.tar.gz` alongside `BUNDLE.json` and `manifest.yaml`. Ship that tarball.

## Caveats

- The bundle does **not** include the 9 AIOS core zips themselves — those are your private/licensed core and stay in your workspace. The skill just packages whatever you point `--source` at. The recipient needs to have the same 9 zips available (or you ship the resulting tarball, which embeds them).
- The receiving end needs Claude Code installed and the operator to actually walk the INSTALL-PROMPT.md. There's no fully-headless mode by design — the gates are load-bearing.
