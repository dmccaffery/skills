#!/usr/bin/env python3
"""Tier 2 behavioral evals.

For every plugins/*/evals/<skill>/cases.json, run each case's prompt through a
headless `claude -p` session in a throwaway fixture workspace (with the plugin's
skills installed), then grade assertions — deterministic first, LLM-judged last.

Case schema:
  {
    "id": "module-scaffold",
    "prompt": "...",
    "files": { "relative/path.tf": "content", ... },        # optional fixture
    "max_turns": 25,                                         # optional
    "assertions": [
      {"type": "file_exists", "path": "modules/x/main.tf"},
      {"type": "file_absent", "path": "modules/x/versions.tf"},
      {"type": "regex", "path": "modules/x/variables.tf", "pattern": "set\\(string\\)"},
      {"type": "not_regex", "pattern": "\\\"this\\\""},      # no path -> final output text
      {"type": "command", "run": "terraform validate", "cwd": "modules/x", "requires": "terraform"},
      {"type": "llm", "text": "The README explains what the module deliberately omits"}
    ]
  }

Usage:
  python3 tools/eval/run_cases.py [--skill NAME] [--case ID] [--timeout SECS]

Requires the `claude` CLI; `requires:`-guarded command assertions skip when the
named binary is missing. Results land in evals-results/cases-<skill>.json.
"""

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO / "evals-results"
DEFAULT_TOOLS = "Read Write Edit Glob Grep Skill Bash(terraform *) Bash(tflint *) Bash(mkdir *)"
JUDGE_PROMPT = """You are grading an AI coding agent's work. Assertion to verify:

{assertion}

The agent's final response was:
---
{output}
---

Files in the agent's workspace are at: {workspace}
Reply with ONLY a JSON object: {{"passed": true|false, "evidence": "<short quote or file fact supporting the verdict>"}}"""


def eval_sets(skill_filter):
    for cases in sorted(REPO.glob("plugins/*/evals/*/cases.json")):
        skill = cases.parent.name
        plugin_dir = cases.parents[2]
        if skill_filter and skill != skill_filter:
            continue
        yield plugin_dir, skill, json.loads(cases.read_text())


def make_workspace(plugin_dir, files):
    ws = Path(tempfile.mkdtemp(prefix="cases.", dir=os.environ.get("TMPDIR")))
    skills_dir = ws / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    for sk in sorted((plugin_dir / "skills").iterdir()):
        if (sk / "SKILL.md").is_file():
            (skills_dir / sk.name).symlink_to(sk)
    for rel, content in (files or {}).items():
        path = ws / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return ws


def run_agent(ws, prompt, max_turns, timeout, allowed_tools):
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--max-turns", str(max_turns),
        "--allowedTools", allowed_tools,
    ]
    proc = subprocess.run(
        cmd, cwd=ws, capture_output=True, text=True, errors="replace", timeout=timeout,
    )
    try:
        return json.loads(proc.stdout).get("result", "")
    except json.JSONDecodeError:
        return proc.stdout


def grade(assertion, ws, output, timeout):
    """Returns (passed: bool|None, evidence: str). None = skipped."""
    kind = assertion["type"]

    if kind in ("file_exists", "file_absent"):
        exists = (ws / assertion["path"]).exists()
        passed = exists if kind == "file_exists" else not exists
        return passed, f"{assertion['path']} {'exists' if exists else 'missing'}"

    if kind in ("regex", "not_regex"):
        if "path" in assertion:
            target = ws / assertion["path"]
            if not target.is_file():
                return False, f"{assertion['path']} missing"
            text = target.read_text(errors="replace")
        else:
            text = output
        match = re.search(assertion["pattern"], text, re.MULTILINE)
        passed = bool(match) if kind == "regex" else not match
        evidence = match.group(0)[:120] if match else "no match"
        return passed, evidence

    if kind == "command":
        binary = assertion.get("requires")
        if binary and not shutil.which(binary):
            return None, f"skipped: {binary} not installed"
        cwd = ws / assertion.get("cwd", ".")
        proc = subprocess.run(
            assertion["run"], shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout,
        )
        expected = assertion.get("expect_exit", 0)
        tail = (proc.stdout + proc.stderr).strip()[-200:]
        return proc.returncode == expected, f"exit {proc.returncode}: {tail}"

    if kind == "llm":
        prompt = JUDGE_PROMPT.format(
            assertion=assertion["text"], output=output[:8000], workspace=ws,
        )
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "4",
             "--allowedTools", "Read Glob Grep"],
            capture_output=True, text=True, errors="replace", timeout=timeout,
        )
        try:
            result = json.loads(proc.stdout).get("result", "")
            verdict = json.loads(re.search(r"\{.*\}", result, re.DOTALL).group(0))
            return bool(verdict.get("passed")), str(verdict.get("evidence", ""))[:200]
        except Exception as exc:  # judge output unparseable -> fail loudly
            return False, f"judge error: {exc}"

    return False, f"unknown assertion type: {kind}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", help="only run evals for this skill")
    ap.add_argument("--case", help="only run the case with this id")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per agent run")
    args = ap.parse_args()

    if not shutil.which("claude"):
        sys.exit("error: `claude` CLI not found on PATH")

    RESULTS_DIR.mkdir(exist_ok=True)
    any_failed = False

    for plugin_dir, skill, cases in eval_sets(args.skill):
        results = []
        print(f"\n=== {skill} ===")
        for case in cases:
            if args.case and case["id"] != args.case:
                continue
            ws = make_workspace(plugin_dir, case.get("files"))
            try:
                output = run_agent(
                    ws, case["prompt"], case.get("max_turns", 25),
                    args.timeout, case.get("allowed_tools", DEFAULT_TOOLS),
                )
                graded = []
                for assertion in case["assertions"]:
                    passed, evidence = grade(assertion, ws, output, args.timeout)
                    graded.append({**assertion, "passed": passed, "evidence": evidence})
                    marker = "SKIP" if passed is None else ("PASS" if passed else "FAIL")
                    label = assertion.get("text") or assertion.get("pattern") \
                        or assertion.get("run") or assertion.get("path")
                    print(f"  [{marker}] {case['id']}: {label}")
                case_passed = all(g["passed"] is not False for g in graded)
                any_failed |= not case_passed
                results.append({"id": case["id"], "passed": case_passed, "assertions": graded})
            finally:
                shutil.rmtree(ws, ignore_errors=True)

        if results:
            out = RESULTS_DIR / f"cases-{skill}.json"
            out.write_text(json.dumps(results, indent=2) + "\n")
            passed_n = sum(r["passed"] for r in results)
            print(f"  {passed_n}/{len(results)} cases passed -> {out.relative_to(REPO)}")

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
