# Install: aios-bundler

> Drop this share onto an AIOS workspace, then in Claude Code say:
> "Read `shares/aios-bundler/INSTALL.md` and help me set this up."

---

## FOR CLAUDE — How to guide this install

You are walking a human through installing the **aios-bundler** skill into their AIOS workspace. Follow this carefully:

- **Assume non-technical unless told otherwise.** Explain each step in plain English BEFORE running it.
- **Pace yourself.** After each phase, pause and confirm before continuing.
- **Celebrate small wins.** "Skill is in place — nice, that's the structural step done."
- **Never dump raw errors.** If something fails, explain what went wrong in one sentence and suggest the fix.
- **Never skip a `[VERIFY]` block.** They exist because the next step depends on the previous one succeeding.
- **Detect path.** This share lives at `shares/aios-bundler/` relative to the AIOS workspace root. Run commands from the workspace root unless told otherwise.
- **Do not run the packer during install.** Installing the skill and running it are separate steps. Tell the user how to run it at the end.

---

## OVERVIEW

The `aios-bundler` skill turns the 9 core AIOS module zips in your workspace's `module-installs/latest-aios/core/` folder into a single portable `.tar.gz`. A teammate (or a fresh laptop) can extract the tarball, run a bash bootstrap, and then Claude Code walks them through a 9-layer install in locked order with one confirmation gate.

After this install you'll have:
- The `aios-bundler` skill at `.claude/skills/aios-bundler/`.
- Ability to run `.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py` to produce a bundle in `outputs/aios-bundles/<version>/`.

**Setup time:** ~5 minutes if you already have a `.venv`.
**Running cost:** Free. Pure-input — no external APIs.

---

## SCOPING

There is one path. The skill is small (6 files, one dependency). Use the **RECOMMENDED** flow:

1. Verify prerequisites.
2. Copy the skill into `.claude/skills/aios-bundler/`.
3. Install `pyyaml` if missing.
4. Smoke-test by listing skill files and dry-running `pack.py --help`.

Ask the user: "Ready to start? Type 'go' when you are."

---

## PREREQUISITES

Run each check and confirm before proceeding.

### 1. We are inside an AIOS workspace

```bash
test -d module-installs/latest-aios/core && echo "OK: AIOS workspace detected" || echo "MISSING"
```

`[VERIFY]` If `MISSING`, stop and tell the user:
> "I don't see `module-installs/latest-aios/core/` here. The aios-bundler skill expects that folder. Are we in the right directory? Run `pwd` to check, then `cd` to your AIOS workspace root."

### 2. Python 3.10+ is available

```bash
.venv/bin/python --version 2>/dev/null || python3 --version
```

`[VERIFY]` Need Python 3.10 or newer. If a `.venv` exists, prefer it. If not:
> "No `.venv` found. I'll create one for you in the next phase."

### 3. Claude Code is installed

```bash
command -v claude && echo "OK: Claude Code on PATH" || echo "MISSING"
```

`[VERIFY]` If missing, point the user to `https://docs.claude.com/claude-code` — the skill itself works without it, but the bundles it produces are designed to be installed *through* Claude Code on the target machine.

---

## INSTALL

### Phase 1: Foundation — set up the venv (skip if `.venv` already exists)

```bash
test -d .venv || python3 -m venv .venv
```

Tell the user in plain English: "Creating a Python virtual environment so we don't pollute your system Python. One-time setup."

`[VERIFY]`

```bash
test -f .venv/bin/python && echo "OK: venv ready" || echo "FAILED"
```

### Phase 2: Core — copy the skill into place

```bash
mkdir -p .claude/skills/aios-bundler
cp -R shares/aios-bundler/skill/. .claude/skills/aios-bundler/
```

Tell the user: "Copying the skill files into your workspace's `.claude/skills/` folder. That's where Claude Code looks for project skills."

`[VERIFY]`

```bash
ls .claude/skills/aios-bundler/
ls .claude/skills/aios-bundler/scripts/
ls .claude/skills/aios-bundler/templates/
ls .claude/skills/aios-bundler/reference/
```

Expect to see:
- Top-level: `SKILL.md`, `scripts/`, `templates/`, `reference/`
- `scripts/`: `pack.py`
- `templates/`: `INSTALL-PROMPT.md`, `install.sh`, `manifest.template.yaml`
- `reference/`: `install-order.md`

If anything is missing, stop and tell the user which file didn't copy.

### Phase 3: Dependencies — install `pyyaml`

```bash
.venv/bin/pip install -r shares/aios-bundler/requirements.txt
```

Tell the user: "Installing `pyyaml`, which the packer uses to render the manifest. That's the only dependency."

`[VERIFY]`

```bash
.venv/bin/python -c "import yaml; print('OK: pyyaml', yaml.__version__)"
```

### Phase 4: Smoke test — does the packer load?

```bash
.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py --help
```

`[VERIFY]` Should print a `usage:` line with `--source`, `--out`, `--version`. If you get a `ModuleNotFoundError`, the pip step didn't run inside the right venv — re-run Phase 3.

---

## TEST

### Quick test (no bundle produced)

Show the user the skill's frontmatter so they can see it loaded correctly:

```bash
head -20 .claude/skills/aios-bundler/SKILL.md
```

Expect to see `name: aios-bundler` and a `description:` line.

### Full test (actually build a bundle — optional)

Only do this if the user has all 9 core zips in `module-installs/latest-aios/core/`:

```bash
ls module-installs/latest-aios/core/*.zip | wc -l
```

If that prints `9`:

```bash
.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py
```

Expected output (last 5 lines):
```
OK  bundle:   .../outputs/aios-bundles/<today>/aios-bundle-<today>.tar.gz
    sha256:   <64-hex-chars>
    entries:  12
    sidecar:  .../BUNDLE.json
    manifest: .../manifest.yaml
```

If you get `ERROR: missing required zips`, that's fine for now — it means the skill is wired correctly but the user just doesn't have all 9 zips yet. Tell them so.

---

## WHAT'S NEXT

The skill is installed. To use it:

1. **Build a bundle** (defaults to today's date as the version):
   ```bash
   .venv/bin/python .claude/skills/aios-bundler/scripts/pack.py
   ```
   Output lands in `outputs/aios-bundles/<version>/`.

2. **Ship the tarball** at `outputs/aios-bundles/<version>/aios-bundle-<version>.tar.gz` to whoever needs to install AIOS. They run:
   ```bash
   mkdir -p /tmp/aios-fresh
   tar -xzf aios-bundle-<version>.tar.gz -C /tmp/aios-fresh
   bash /tmp/aios-fresh/install.sh ~/aios-target
   cd ~/aios-target && claude .
   # then paste the contents of INSTALL-PROMPT.md into the Claude Code chat
   ```

3. **Read the rationale** for the locked install order at `.claude/skills/aios-bundler/reference/install-order.md` if you want to understand why starter-kit goes first and infra has a gate.

4. **Customize the install order** by editing `.claude/skills/aios-bundler/templates/manifest.template.yaml`. The `gates:` section is the friendliest knob — add a new gate by appending another `{ layer, reason }` entry.

5. **Invoke from Claude Code** by saying "use the aios-bundler skill to build a bundle". Claude reads `SKILL.md` and follows the documented invocation.

---

## Done

Tell the user:
> "All set. Your AIOS workspace now has the `aios-bundler` skill. Run `.venv/bin/python .claude/skills/aios-bundler/scripts/pack.py` whenever you need a fresh portable bundle of your AIOS core."
