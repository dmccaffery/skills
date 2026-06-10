#!/usr/bin/env python3
# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

"""Tier 0 static checks: skill frontmatter, manifest structure, version sync.

Python port of the old scripts/check-skills.sh, living in tools/eval for a
consistent harness setup. Deliberately stdlib-only with no sibling imports so
single-plugin repositories can vendor this one file.

Three check layers:

- skills      — every skills/*/SKILL.md: frontmatter present; name kebab-case,
                <= 64 chars, equal to its directory; description non-empty,
                <= 1024 chars, with a "Use when/after/before" trigger phrase;
                license MIT; body <= 500 lines.
- plugins     — dual manifests (.claude-plugin/plugin.json and
                .codex-plugin/plugin.json): names agree, versions in sync and
                strict semver, hooks/ forbidden, at least one skill shipped.
- marketplace — repo-level marketplace manifests (.claude-plugin/marketplace.json
                and .agents/plugins/marketplace.json): non-empty plugin lists,
                owner.name (Claude), ./-prefixed sources that resolve, and an
                identical plugin set in both.

Usage:
  python3 tools/eval/run_checks.py [--root PATH] [--single] [--no-marketplace]

  --root PATH       repository to check (default: the repo containing this file)
  --single          the repository IS one plugin: .claude-plugin/, .codex-plugin/
                    and skills/ sit at the repo root with no plugins/ tree and no
                    marketplace. Manifest names must agree and be kebab-case but
                    are not checked against the (arbitrary) checkout dir name.
  --no-marketplace  verify plugins only; skip the marketplace manifests
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TRIGGER_RE = re.compile(r"Use (when|after|before)")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

ROOT = DEFAULT_ROOT
failures = 0


def err(message):
    global failures
    print(f"FAIL: {message}", file=sys.stderr)
    failures += 1


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path):
    """Parsed JSON, or None (reported) when unreadable or invalid."""
    try:
        return json.loads(path.read_text())
    except OSError as exc:
        err(f"{rel(path)}: unreadable ({exc})")
    except json.JSONDecodeError as exc:
        err(f"{rel(path)}: invalid JSON ({exc})")
    return None


def frontmatter(skill_md):
    """Top-level scalar frontmatter fields as a dict, or None when the file
    has no leading --- block (an unterminated block counts as none)."""
    lines = skill_md.read_text(errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            fields[match.group(1)] = value
    return None


def check_skill(skill_md):
    path = rel(skill_md)
    fields = frontmatter(skill_md)
    if fields is None:
        err(f"{path}: no YAML frontmatter")
        return
    name = fields.get("name", "")
    description = fields.get("description", "")
    directory = skill_md.parent.name

    if name != directory:
        err(f"{path}: name '{name}' != directory '{directory}'")
    if not NAME_RE.match(name):
        err(f"{path}: name '{name}' not kebab-case")
    if len(name) > 64:
        err(f"{path}: name longer than 64 chars")

    if not description:
        err(f"{path}: empty description")
    if len(description) > 1024:
        err(f"{path}: description longer than 1024 chars")
    if not TRIGGER_RE.search(description):
        err(f"{path}: description missing a 'Use when/after/before' trigger phrase")

    if fields.get("license") != "MIT":
        err(f"{path}: license must be MIT (got '{fields.get('license', '')}')")

    lines = len(skill_md.read_text(errors="replace").splitlines())
    if lines > 500:
        err(f"{path}: SKILL.md exceeds 500 lines ({lines})")


def check_plugin(plugin_dir, expected_name=None):
    """Check one plugin rooted at plugin_dir. expected_name pins the manifest
    name to the plugin directory; None (--single) skips that, since a checkout
    directory name is arbitrary, and requires the manifests to agree instead."""
    label = rel(plugin_dir) if plugin_dir != ROOT else "repo root"
    claude_pj = plugin_dir / ".claude-plugin" / "plugin.json"
    codex_pj = plugin_dir / ".codex-plugin" / "plugin.json"

    manifests = {}
    for pj in (claude_pj, codex_pj):
        if not pj.is_file():
            err(f"{label}: missing {pj.relative_to(plugin_dir)}")
        else:
            data = read_json(pj)
            if data is not None:
                manifests[pj] = data

    if len(manifests) == 2:
        names = {pj: str(data.get("name", "")) for pj, data in manifests.items()}
        if expected_name is not None:
            for pj, name in names.items():
                if name != expected_name:
                    err(f"{rel(pj)}: name '{name}' != directory '{expected_name}'")
        else:
            if len(set(names.values())) > 1:
                err(f"{label}: manifests disagree on plugin name: {sorted(set(names.values()))}")
            for name in set(names.values()):
                if not NAME_RE.match(name):
                    err(f"{label}: plugin name '{name}' not kebab-case")

        claude_ver = str(manifests[claude_pj].get("version", ""))
        codex_ver = str(manifests[codex_pj].get("version", ""))
        if claude_ver != codex_ver:
            err(f"{label}: version mismatch (claude={claude_ver} codex={codex_ver})")
        if not SEMVER_RE.match(codex_ver):
            err(f"{label}: version '{codex_ver}' is not strict semver")

    # Codex default-discovers hooks/hooks.json with a non-Claude schema — forbid it.
    if (plugin_dir / "hooks").is_dir():
        err(f"{label}: hooks/ directory is forbidden (see AGENTS.md)")

    skills = sorted(plugin_dir.glob("skills/*/SKILL.md"))
    if not skills:
        err(f"{label}: no skills under skills/")
    for skill_md in skills:
        check_skill(skill_md)


def check_marketplace():
    claude_mp = ROOT / ".claude-plugin" / "marketplace.json"
    codex_mp = ROOT / ".agents" / "plugins" / "marketplace.json"

    markets = {}
    for mp in (claude_mp, codex_mp):
        if not mp.is_file():
            err(f"missing {rel(mp)}")
            continue
        data = read_json(mp)
        if data is None:
            continue
        markets[mp] = data
        plugins = data.get("plugins")
        if not data.get("name") or not isinstance(plugins, list) or not plugins:
            err(f"{rel(mp)}: missing name or non-empty plugins array")

    if claude_mp in markets and not (markets[claude_mp].get("owner") or {}).get("name"):
        err(f"{rel(claude_mp)}: missing owner.name")

    # Every marketplace source must be ./-prefixed and resolve to a plugin
    # directory (Codex fallback-reads Claude's manifest against the repo root).
    for data in markets.values():
        for plugin in data.get("plugins") or []:
            source = plugin.get("source")
            if isinstance(source, dict):
                source = source.get("path")
            source = str(source)
            if not source.startswith("./"):
                err(f"marketplace source '{source}' is not ./-prefixed")
            elif not (ROOT / source).is_dir():
                err(f"marketplace source '{source}' does not resolve")

    if len(markets) == 2:
        claude_names = sorted(str(p.get("name")) for p in markets[claude_mp].get("plugins") or [])
        codex_names = sorted(str(p.get("name")) for p in markets[codex_mp].get("plugins") or [])
        if claude_names != codex_names:
            err(f"marketplaces disagree on plugins: claude={claude_names} codex={codex_names}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help="repository to check (default: the repo containing this file)")
    ap.add_argument("--single", action="store_true",
                    help="the repo is one plugin at its root (no plugins/ tree, no marketplace)")
    ap.add_argument("--no-marketplace", action="store_true",
                    help="verify plugins only; skip marketplace manifests")
    args = ap.parse_args()

    global ROOT
    ROOT = args.root.resolve()
    if not ROOT.is_dir():
        sys.exit(f"error: --root {ROOT} is not a directory")

    if args.single:
        check_plugin(ROOT, expected_name=None)
    else:
        if not args.no_marketplace:
            check_marketplace()
        plugins_root = ROOT / "plugins"
        plugin_dirs = sorted(p for p in plugins_root.glob("*") if p.is_dir()) \
            if plugins_root.is_dir() else []
        if not plugin_dirs:
            err("no plugins under plugins/ (for a root-level plugin repo, pass --single)")
        for plugin_dir in plugin_dirs:
            check_plugin(plugin_dir, expected_name=plugin_dir.name)

    if failures:
        sys.exit(1)
    print("run_checks: all checks passed")


if __name__ == "__main__":
    main()
