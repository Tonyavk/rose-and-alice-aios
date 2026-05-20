# Research Summary - AIOS Repackaging

> Lean synthesis for the 2026-05-11 live build. Refocused 2026-05-10 to match the current concept: pure-input repackager that turns the 9 latest-AIOS core zips into a portable tarball with a 2-stage guided installer. Drift / classification material removed - that's the future `aios-drift-audit` skill, captured in `concept.md` `## Out of Scope`.

---

## 1. Distribution patterns - what others do

| Tool | What ships | Manifest | Lesson for AIOS |
|------|-----------|----------|-----------------|
| **chezmoi** | dotfiles + templates | `chezmoi.toml` per machine | `chezmoi apply` is interactive - it pauses on conflicts and asks; the bundle's `INSTALL-PROMPT.md` borrows that pattern at the layer level |
| **copier** | project template with jinja vars | `copier.yml` + `_tasks` post-gen hooks | Post-gen tasks run *after* extraction - directly the role of stage-2 INSTALL.mds in our bundle |
| **Claude Code skills** | per-skill folder with SKILL.md + scripts | `SKILL.md` frontmatter | AIOS already follows this for skills - `aios-bundler` is the workspace-level extension |
| **Homebrew formula** | binary + deps | Ruby formula (versioned tags) | Date-based versioning is friendlier for a workspace than semver |
| **Helm chart** | k8s manifests + values schema | `Chart.yaml` + `values.schema.json` | Two-file split (shipped defaults + user overrides) - in our case, the manifest is shipped, the operator's `.env` and GitHub creds are local |

**Pick:** **manifest-driven, copier-style two-stage extraction**. The bundle ships zips + manifest + a stage-2 prompt. The operator's machine drives the per-layer install. No mining of the operator's workspace at any point.

---

## 2. Guided post-install walkthrough patterns

The bundle's stage-2 (`INSTALL-PROMPT.md` -> Claude Code) borrows from two places:

- **chezmoi `apply` interactive mode.** chezmoi walks each managed file, shows a diff, and asks "apply / skip / merge?". The bundle does the equivalent at the *layer* level: extract layer N to a tempdir, show the first ~40 lines of its `INSTALL.md`, ask the operator to confirm before running. Confirmation gates (`infra-os-v1.zip`, `aios-starter-kit.zip`) are a stronger version of this same pattern.
- **copier post-generation tasks (`_tasks`).** copier templates declare a `_tasks` block - shell commands run after extraction. The bundle's equivalent is each layer's `INSTALL.md` - extracted to a tempdir, walked by Claude Code, executed step by step. Crucially we keep the *layer's own* INSTALL.md as the source of truth instead of a top-level `_tasks` block. That keeps ownership with the layer, not the bundler.

**What we deliberately did not borrow:** chezmoi's three-way merge / state file. AIOS bundles are install-time artefacts, not continuously-managed dotfile sets. An update flow with three-way merge is a future workshop (`aios-update`), not this one.

---

## 3. Versioning + update flow

- **Versioning:** date-based. `aios-bundle-2026-05-11.tar.gz`. Plus a `BUNDLE.json` with sha256 + generated_at + source_dir + zip_count. Semver doesn't carry meaning for a date-stamped repackage.
- **Update flow:** out of scope today. The bundle is install-time only. A future `aios-update` workshop can add copier-style three-way merge if members ask for it.

---

## 4. Secrets handling at pack time

The pure-input model makes this trivial: `pack.py` only reads from `--source` (the zips folder). It never opens `.env`, `credentials/`, or any other workspace path. There is no scanning, no scrubbing, no allow/deny pattern - because the surface area where a secret could leak doesn't exist. This is the load-bearing reason the skill is shaped this way.

API keys for the *target* machine are owned by each layer's INSTALL.md (e.g. infra-os asks for the GitHub token). The bundler doesn't touch them.

---

## 5. Risks and how the workshop handles them

| Risk | Mitigation |
|------|-----------|
| Member's `module-installs/latest-aios/core/` is missing zips | `pack.py` aborts with a clear list of missing files - no half-built tarball |
| Operator runs `install.sh` against a non-empty target | `install.sh` refuses without `--force` |
| Operator skips a confirmation gate | `INSTALL-PROMPT.md` hard rules: never skip a gate; Claude Code refuses to advance without "confirm" |
| Layer INSTALL.md changes between bundle build and install | sha256 mismatch caught at pre-flight; install aborts before touching anything |
| Cross-platform tar quirks | Default `tar -xzf` works on macOS + Linux; Windows documented as future work in SKILL.md |

---

## 6. What is *not* in scope for this workshop

- **Drift audit** (live workspace vs `module-installs/`) - separate future skill `aios-drift-audit`
- **Modules / sub-modules** - same skill shape, longer manifest, `--include`/`--exclude` flags
- **Three-way merge update flow** - future `aios-update` workshop
- **Auto-detect install order** from each zip's INSTALL.md frontmatter - nice-to-have, not load-bearing
- **Linux / Windows installers** - macOS-tested only
- **Encrypted bundle / signed distribution** - distribution channels (S3, GH Releases, internal share) left to members

---

## Sources

- chezmoi docs - https://www.chezmoi.io (interactive `apply`, age-encrypted secrets)
- copier docs - https://copier.readthedocs.io (templates with `_tasks` post-gen hooks, `copier update`)
- Helm best practices - values-vs-defaults split
- Existing AIOS install material: `module-installs/latest-aios/core/` (the 9 zips)
- SOP: `context/operations/sop-sqlite-migrations.md` (schemas as code - relevant to `data-os-v1`)
