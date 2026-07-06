---
description:
    Delegate a bulk or mechanical coding task to the Codex CLI (gpt-5.5) following the codex-coding-task skill, then
    verify the work against the spec before reporting it.
argument-hint: <the task to delegate — spec, scope, and definition of done>
---

# Codex coding task

Apply the `codex-coding-task` skill to delegate this work to Codex: $ARGUMENTS

Follow the skill exactly:

- Confirm the task is delegable — bulk or mechanical with a clear spec (renames, migrations, format conversions,
  written-spec implementation, read-only data analysis). If it is small, ambiguous, or needs design judgment, say so and
  do it directly instead.
- Create the artifact directory with `mktemp -d` under `$TMPDIR`, snapshot `git status` so Codex's changes are
  attributable, write the skill's structured task prompt (task, scope, constraints, definition of done), and run the
  matching `codex exec` shape (`--full-auto` for edits, `--sandbox read-only` for analysis).
- Verify before reporting: diff the tree against the snapshot and the scope, run the definition-of-done commands, and
  spot-check bulk changes; separate what you verified from Codex's unverified claims.
- If `codex` is not installed or the command fails, report the error and offer to do the work directly instead.
