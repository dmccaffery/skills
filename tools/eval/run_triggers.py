#!/usr/bin/env python3
"""Tier 1 trigger-accuracy evals.

For every plugins/*/evals/<skill>/triggers.json, run each query through a headless
`claude -p` session in a throwaway workspace where the plugin's skills are installed,
and check whether the skill under test activates. A query passes when its observed
trigger rate agrees with `should_trigger` (threshold 0.5).

Usage:
  python3 tools/eval/run_triggers.py [--skill NAME] [--runs N] [--timeout SECS]

Requires the `claude` CLI on PATH and an authenticated session / API key.
Results are written to evals-results/triggers-<skill>.json.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO / "evals-results"


def eval_sets(skill_filter):
    for triggers in sorted(REPO.glob("plugins/*/evals/*/triggers.json")):
        skill = triggers.parent.name
        plugin_dir = triggers.parents[2]
        if skill_filter and skill != skill_filter:
            continue
        yield plugin_dir, skill, json.loads(triggers.read_text())


def make_workspace(plugin_dir):
    """Throwaway project dir with ALL of the plugin's skills installed, so the
    skill under test has to win against its siblings (near-miss negatives)."""
    ws = Path(tempfile.mkdtemp(prefix="triggers.", dir=os.environ.get("TMPDIR")))
    skills_dir = ws / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    for sk in sorted((plugin_dir / "skills").iterdir()):
        if (sk / "SKILL.md").is_file():
            (skills_dir / sk.name).symlink_to(sk)
    return ws


def skill_triggered(ws, query, skill, timeout):
    """Run one headless session; True if a Skill/Read tool_use targets `skill`."""
    cmd = [
        "claude", "-p", query,
        "--output-format", "stream-json", "--verbose",
        "--max-turns", "2",
        "--allowedTools", "Skill Read",
    ]
    proc = subprocess.Popen(
        cmd, cwd=ws, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, errors="replace",
    )
    deadline = time.monotonic() + timeout
    try:
        for line in proc.stdout:
            if time.monotonic() > deadline:
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for block in (event.get("message") or {}).get("content") or []:
                if block.get("type") != "tool_use":
                    continue
                payload = json.dumps(block.get("input") or {})
                if block.get("name") == "Skill" and skill in payload:
                    return True
                if block.get("name") == "Read" and f"skills/{skill}/SKILL.md" in payload:
                    return True
        return False
    finally:
        proc.kill()
        proc.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", help="only run evals for this skill")
    ap.add_argument("--runs", type=int, default=3, help="runs per query (default 3)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per run")
    args = ap.parse_args()

    if not shutil.which("claude"):
        sys.exit("error: `claude` CLI not found on PATH")

    RESULTS_DIR.mkdir(exist_ok=True)
    any_failed = False

    for plugin_dir, skill, cases in eval_sets(args.skill):
        ws = make_workspace(plugin_dir)
        results = []
        print(f"\n=== {skill} ({len(cases)} queries x {args.runs} runs) ===")
        try:
            for case in cases:
                query, expected = case["query"], case["should_trigger"]
                hits = sum(
                    skill_triggered(ws, query, skill, args.timeout)
                    for _ in range(args.runs)
                )
                rate = hits / args.runs
                passed = (rate >= 0.5) if expected else (rate < 0.5)
                any_failed |= not passed
                results.append({
                    "query": query, "should_trigger": expected,
                    "trigger_rate": rate, "passed": passed,
                })
                marker = "PASS" if passed else "FAIL"
                print(f"  [{marker}] rate={rate:.2f} expect={'+' if expected else '-'} {query[:70]}")
        finally:
            shutil.rmtree(ws, ignore_errors=True)

        out = RESULTS_DIR / f"triggers-{skill}.json"
        out.write_text(json.dumps(results, indent=2) + "\n")
        passed_n = sum(r["passed"] for r in results)
        print(f"  {passed_n}/{len(results)} queries passed -> {out.relative_to(REPO)}")

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
