# AIOS Install Order - Rationale

The 9 core layers install in this locked order:

`starter-kit -> context -> data -> infra -> intel -> command -> productivity -> daily-brief -> slash-commands`

One confirmation gate: **infra-os** (creates a remote - irreversible). Starter-kit does not need a gate - it is safe scaffolding into an empty target.

---

## Mental model

The starter-kit is the **substrate**: an empty workspace skeleton (`.claude/commands/`, `.claude/skills/`, `context/` stubs, `.env` template, empty `module-installs/`, empty `plans/`). It is what every other layer is installed *into*.

The 8 OS layers are **fillers**: each writes into the directories the starter-kit shipped, registers commands under `.claude/commands/`, or adds skills under `.claude/skills/`. None of them ship the skeleton; they all assume it.

The earlier draft of this doc had this backwards. Correcting it was the load-bearing fix from the live build.

---

## Why this order

### 1. aios-starter-kit - first

Ships the empty workspace skeleton plus the bootstrap commands `/prime`, `/install`, `/create-plan`, `/implement`, `/share`, `/task-audit`, and the `.env` template. Without this layer there is no `.claude/commands/install.md` to run `/install` against, no `context/` for context-os to fill, no `module-installs/` for `/install` to read.

Notable: the starter-kit zip has no top-level `INSTALL.md` of its own - the guided installer just extracts it into the target. It is the substrate, not a recipe.

### 2. context-os-v1

`context-os`'s own `INSTALL.md` opens with: "This is the very first module they install - it turns a blank template into a workspace that understands them and their business." That "blank template" is the starter-kit. Context-os runs an interview, writes structured files under `context/`, and updates `CLAUDE.md` sections. Every later layer reads from `context/`, so it lands second.

### 3. data-os-v1

Schemas + migrations precede any layer that wants to log into a SQLite database. The migration runner (`scripts/migrate.py`) and the `data/migrations/` discipline live here. Intel, command, productivity, and daily-brief all assume data-os is in place.

### 4. infra-os-v1 - GATE

Operators need a git remote before any layer wants to commit or push artifacts. Infra creates the remote (`gh repo create`) - **irreversible side effect** - so we gate here. The gate confirms GitHub username, repo name, and that a usable token is available. The bundler does NOT call `gh`; infra's own `INSTALL.md` owns that.

Why not first? Because creating a remote without the skeleton + context + data in place wastes a remote on a half-built workspace if the operator aborts later. By the time we hit infra, the operator has already seen three layers succeed - they are committed.

### 5. intel-os-v1

Depends on `data-os` (intel.db migrations) and `context-os` (intel summaries land in context). Order between intel, command, productivity, daily-brief is mostly cosmetic, but intel before the functional layers because they may want to read intel summaries.

### 6. command-os-v1

The Telegram bot. Needs context-os, data-os, and optionally intel-os already present.

### 7. productivity-os-v1

GTD layer (`gtd/` tree, `/process`, `/review`). Needs context-os and data-os.

### 8. daily-brief-v1

The morning brief job reads strategy + GTD next-actions. Needs productivity-os in place.

### 9. slash-commands-v1

Additional workspace-level slash commands. Pure additions to `.claude/commands/`. Last because some commands assume earlier layers exist.

---

## "Why not starter-kit last?"

The intuitive (and wrong) order is "kit last, as a finishing overlay". That assumes the kit is templates *over* the operating layers. It is not - it is the substrate *under* them. The 8 OS layers' install flows expect `.claude/commands/`, `context/`, `module-installs/`, and `.env` to already exist. If the kit lands last, every earlier layer has had to scaffold those directories itself, with the kit then clobbering whatever each layer set up. Foundation first.

---

## Gate reasons (verbatim, mirrored from `manifest.gates`)

- `infra-os-v1.zip` - "Confirm GitHub username + repo name + token before infra creates the remote."

If you add a new gate, edit `templates/manifest.template.yaml` in the skill. The installer (`INSTALL-PROMPT.md`) reads gates from the manifest at install time - no code change required.
