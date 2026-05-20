# AIOS Install Prompt (Stage 2)

You are Claude Code running inside a freshly staged AIOS target directory. The operator has just pasted this prompt into the chat. The current working directory contains the 9 core AIOS zips, a `manifest.yaml`, and this `INSTALL-PROMPT.md`. Your job is to walk the 9 layers in order, with confirmation gates, and never touch anything outside the target directory or your tempdirs.

## Hard rules

1. **Never read or write outside the target directory and your own tempdirs.** No global config, no SSH keys, no `.env` outside the target.
2. **Never push to a remote** unless a layer's `INSTALL.md` explicitly instructs it.
3. **Never skip a gate.** If a layer appears in `manifest.gates`, you MUST surface the reason and wait for the operator to type "confirm" before continuing.
4. **Trust the manifest.** Install order, gates, sha256s all come from `manifest.yaml`. Do not improvise an order.
5. **One layer at a time.** Extract layer N to a tempdir, follow its `INSTALL.md`, complete it, then move to N+1. Do not parallelize.
6. **Stop on failure.** If any step inside a layer fails, halt and tell the operator. Do not continue to the next layer.

## Phase A - Pre-flight

1. Read `manifest.yaml`. Print a summary to the operator:
   - `version`, `generated_at`, `source_dir`
   - The `install_order` list (9 entries)
   - The `gates` list with reasons
2. Verify each zip is present in the current directory.
3. Compute sha256 of each zip and compare to the manifest. If any mismatch, abort with a clear error and the offending file. Do not continue.
4. Print: `Pre-flight OK. Type "go" to start the per-layer install.`
5. Wait for the operator to type "go".

## Phase B - Per-layer flow

For each `layer` in `manifest.install_order`:

1. Create a fresh tempdir (e.g. `/tmp/aios-layer-<name>-<random>/`).
2. Extract `<layer>.zip` into the tempdir. Do not extract directly into the target.
3. Find the top-level `INSTALL.md` inside the extracted tree. If absent and the layer is NOT `aios-starter-kit.zip`, halt and tell the operator. (Starter-kit legitimately ships without one - see special handling below.)
4. Print the first ~40 lines of that `INSTALL.md` for the operator. (Skip for starter-kit.)
5. **Gate handling:**
   - If `layer` appears in `manifest.gates`, print the gate reason and: `GATE: type "confirm" to proceed, anything else aborts.` Wait for the operator. Abort if input is not exactly `confirm`.
   - For `infra-os-v1.zip`: in addition to the gate, ask the operator to confirm GitHub username, intended repo name, and that a usable token is available. Do NOT call `gh repo create` yourself - infra's own `INSTALL.md` owns that step.
   - For `aios-starter-kit.zip` (first): this layer ships the workspace skeleton (`.claude/`, `context/` stubs, `.env` template, empty `module-installs/`, `plans/`) and has no top-level `INSTALL.md`. Copy its contents into the target directly; do not look for an `INSTALL.md`.
   - For all other layers: `Press enter to install <layer>.`
6. Follow the steps in that layer's `INSTALL.md` exactly. If the file says "run X", run X. If it says "edit Y", edit Y. Do not invent steps. Do not skip steps.
7. When the layer's `INSTALL.md` is complete, report a one-line success and move on.

## Phase C - Post-install

1. **Archive the source zips into `module-installs/`.** After all 9 layers have installed, the zips at the target workspace root are no longer needed inline - relocate them so the resulting workspace matches the canonical AIOS layout (and can re-bundle itself later).
   - Create the directory: `mkdir -p module-installs/latest-aios/core`
   - Move all 9 layer zips from the target root into it:
     `mv aios-starter-kit.zip context-os-v1.zip data-os-v1.zip infra-os-v1.zip intel-os-v1.zip command-os-v1.zip productivity-os-v1.zip daily-brief-v1.zip slash-commands-v1.zip module-installs/latest-aios/core/`
   - Also move `manifest.yaml` alongside them so the operator can see what versions were installed: `mv manifest.yaml module-installs/latest-aios/core/`
   - Leave `INSTALL-PROMPT.md` in place at the workspace root for reference (or delete it - operator's choice).
   - Confirm with `ls module-installs/latest-aios/core/` - expect 9 zips + `manifest.yaml`.
2. If a `/prime` command is available in the resulting workspace, run it.
3. Print a final summary:
   - Bundle `version`
   - Tarball sha256 (from `BUNDLE.json` if it was shipped alongside; otherwise note "unavailable - bundle was extracted from tarball only")
   - The 9 layers, marked installed.
   - Confirm `module-installs/latest-aios/core/` now holds the 9 zips + manifest.
4. Tell the operator: `AIOS install complete. You can close this Claude Code session and run /prime to load context.`

## Recovery

- If extraction fails for a layer: keep the tempdir, report the path, halt.
- If a gate is denied: halt cleanly. Tell the operator what was installed so far and how to resume (re-run this prompt; you will re-verify and skip layers whose INSTALL.md has already produced its expected artifacts only if the operator confirms).
- Never auto-rollback. AIOS layers are additive; leaving partially-installed state is safer than destructive cleanup.
