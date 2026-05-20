#!/usr/bin/env python3
"""Pack the 9 core AIOS zips into a portable bundle.

Pure-input: reads only from --source. Never opens .env, credentials, or any
other workspace path. The receiving end is driven by INSTALL-PROMPT.md +
manifest.yaml.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"

EXPECTED_ZIPS = [
    "context-os-v1.zip",
    "data-os-v1.zip",
    "infra-os-v1.zip",
    "intel-os-v1.zip",
    "command-os-v1.zip",
    "productivity-os-v1.zip",
    "daily-brief-v1.zip",
    "slash-commands-v1.zip",
    "aios-starter-kit.zip",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source(source: Path) -> list[Path]:
    if not source.is_dir():
        sys.exit(f"ERROR: --source is not a directory: {source}")
    missing = [z for z in EXPECTED_ZIPS if not (source / z).is_file()]
    if missing:
        sys.exit(
            "ERROR: missing required zips in --source:\n  - "
            + "\n  - ".join(missing)
            + f"\n(source: {source})"
        )
    return [source / z for z in EXPECTED_ZIPS]


def render_manifest(version: str, source_dir: Path, zip_meta: list[dict]) -> str:
    template = (TEMPLATES / "manifest.template.yaml").read_text()
    zips_block = yaml.safe_dump(
        zip_meta, sort_keys=False, default_flow_style=False
    ).rstrip()
    indented = "\n".join(("  " + line) if line else line for line in zips_block.splitlines())
    return (
        template.replace("{{VERSION}}", version)
        .replace("{{GENERATED_AT}}", datetime.now(timezone.utc).isoformat())
        .replace("{{SOURCE_DIR}}", str(source_dir))
        .replace("{{ZIPS_BLOCK}}", indented)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack the 9 core AIOS zips into a portable bundle.")
    parser.add_argument(
        "--source",
        default="module-installs/latest-aios/core",
        help="Folder containing the 9 core zips. Default: module-installs/latest-aios/core",
    )
    parser.add_argument(
        "--out",
        default="outputs/aios-bundles",
        help="Parent directory for per-build folders. Default: outputs/aios-bundles",
    )
    parser.add_argument(
        "--version",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Bundle version stamp. Default: today's date YYYY-MM-DD",
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    out_root = Path(args.out).resolve()
    version = args.version

    zip_paths = verify_source(source)

    zip_meta = [
        {"path": p.name, "sha256": sha256_of(p), "bytes": p.stat().st_size}
        for p in zip_paths
    ]
    manifest_text = render_manifest(version, source, zip_meta)

    install_sh = TEMPLATES / "install.sh"
    install_prompt = TEMPLATES / "INSTALL-PROMPT.md"
    for required in (install_sh, install_prompt):
        if not required.is_file():
            sys.exit(f"ERROR: missing skill template: {required}")

    build_dir = out_root / version
    build_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = build_dir / f"aios-bundle-{version}.tar.gz"

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for p in zip_paths:
            shutil.copy2(p, stage / p.name)
        (stage / "manifest.yaml").write_text(manifest_text)
        shutil.copy2(install_sh, stage / "install.sh")
        (stage / "install.sh").chmod(0o755)
        shutil.copy2(install_prompt, stage / "INSTALL-PROMPT.md")

        with tarfile.open(tarball_path, "w:gz") as tar:
            for entry in sorted(stage.iterdir()):
                tar.add(entry, arcname=entry.name)

    tarball_sha = sha256_of(tarball_path)
    file_count = 1 + len(EXPECTED_ZIPS) + 2  # manifest + zips + install.sh + INSTALL-PROMPT.md
    bundle_json = {
        "version": version,
        "tarball": tarball_path.name,
        "sha256_of_tarball": tarball_sha,
        "file_count": file_count,
        "zip_count": len(EXPECTED_ZIPS),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source),
    }
    (build_dir / "BUNDLE.json").write_text(json.dumps(bundle_json, indent=2) + "\n")
    (build_dir / "manifest.yaml").write_text(manifest_text)

    print(f"OK  bundle:   {tarball_path}")
    print(f"    sha256:   {tarball_sha}")
    print(f"    entries:  {file_count}")
    print(f"    sidecar:  {build_dir / 'BUNDLE.json'}")
    print(f"    manifest: {build_dir / 'manifest.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
