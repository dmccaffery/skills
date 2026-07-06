---
description:
    Run an independent second-pass code review through the Codex CLI (gpt-5.5) following the codex-code-review skill,
    verifying every finding against the code before presenting it.
argument-hint: [uncommitted | base <branch> | commit <sha> | files or areas to focus on]
---

# Codex second-pass review

Apply the `codex-code-review` skill to run Codex as an independent reviewer over: $ARGUMENTS

Follow the skill exactly:

- Identify the review target — uncommitted changes, the current branch against a base branch, a single commit, a PR
  checkout, or specific files. Default to uncommitted changes when no target is given.
- Create the artifact directory with `mktemp -d` under `$TMPDIR`, write the skill's reference review prompt (plus any
  task-specific context), and run the matching `codex review` command shape.
- Read the report and verify every important claim against the cited code or diff; present confirmed issues separately
  from unverified Codex suggestions, and say clearly when Codex found nothing and what target it inspected.
- If `codex` is not installed or the command fails, report the error and offer to review the changes directly instead.
