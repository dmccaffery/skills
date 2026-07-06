---
name: codex-coding-task
description: Shell out to OpenAI's Codex CLI (gpt-5.5) for bulk or mechanical coding work with a clear spec, and verify the result before reporting it. Records the starting tree state, writes a structured task prompt (task, scope, constraints, definition of done) into a mktemp artifact directory under $TMPDIR, runs codex exec (--full-auto for edits, --sandbox read-only for analysis), then reviews the diff against the spec, runs the definition-of-done commands, and spot-checks bulk changes. Use when delegating, offloading, or shelling out mechanical work to Codex or another agent — bulk renames, find-and-replace migrations, config or format conversions, repetitive scaffolding, implementing a written spec, or analyzing data files. Prefer doing the work directly when it is small, ambiguous, or needs design judgment; never delegate just to avoid doing it. Not for code review (see codex-code-review), debugging, design decisions, or installing the Codex CLI.
license: MIT
---

# Bulk and mechanical work with Codex

Delegate to the Codex CLI (gpt-5.5) when a task is **bulk or mechanical with a clear spec**: the kind
of work you could hand to a contractor without them needing to ask questions. Treat what comes back as
**evidence, not authority** — Codex's completion claim is a starting point for your own verification,
never the report itself. This skill is the executor counterpart to the `codex-code-review` skill; use
that one when the user wants Codex to review changes rather than make them.

## 1. Confirm the task is delegable

Good fits — mechanical, rule-based, or exhaustively specified:

- wide renames, find-and-replace migrations, API deprecation shims across many call sites
- config or format conversions (YAML → TOML, v1 → v2 schema) and repetitive scaffolding
- implementation where the spec already pins the behaviour (a written API contract, a filled-in design)
- read-only data analysis over files in the tree (logs, CSVs, fixtures)

Poor fits — do these yourself: small edits (faster to just make), ambiguous requirements, anything
needing design judgment or conversation context Codex does not have, and debugging. If the spec has a
hole, resolve it with the user first or keep the work; never delegate just to avoid doing it.

## 2. Create the artifact directory

Always under `$TMPDIR` — never a bare `/tmp` or the repository:

```sh
ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-task.XXXXXX")"
PROMPT="${ARTIFACT_DIR}/prompt.md"
LAST="${ARTIFACT_DIR}/last-message.md"
```

## 3. Record the starting state

Codex edits the working tree, so make its work isolatable before it runs:

```sh
git status --porcelain > "${ARTIFACT_DIR}/before.txt"
```

Prefer a clean tree (commit or stash unrelated work first). If it must stay dirty, this snapshot is
what lets you attribute changes to Codex afterwards.

## 4. Write the task prompt and run codex exec

Write this reference prompt to `${PROMPT}`, filling every section. A section you cannot fill is a sign
the task is not yet delegable (step 1).

```markdown
Complete this task exactly as specified. It is mechanical: follow the spec, do not redesign, and do
not expand scope.

## Task

<one-paragraph statement of the work>

## Scope

<files, directories, or globs to touch — and anything explicitly out of bounds>

## Constraints

<conventions to preserve, interfaces that must not change, style rules>

## Definition of done

<the observable end state, including commands that must pass, e.g. `make test`>

If any part of the task is ambiguous or impossible as specified, stop and say so in your final
message instead of improvising.
```

Then run the shape that matches the task — `--full-auto` when Codex must edit the workspace,
`--sandbox read-only` when it must only read and report:

```sh
# mechanical edits: implementation, migrations, renames
codex -C "${PWD}" exec --full-auto --output-last-message "${LAST}" - < "${PROMPT}"

# read-only analysis: data analysis, reports, questions about the tree
codex -C "${PWD}" exec --sandbox read-only --output-last-message "${LAST}" - < "${PROMPT}"
```

Bulk tasks can run for several minutes — allow a generous timeout. If `codex` is not installed or the
command fails, stop here: report the error to the user and offer to do the work directly yourself
instead. Never present work that was not actually done.

## 5. Verify the work

Read `${LAST}` for Codex's summary and any ambiguities it flagged, then check the work itself:

- **Diff against scope** — review `git status`/`git diff` (including untracked files) against the
  snapshot from step 3. Everything changed must be inside scope; anything outside it gets reverted or
  flagged.
- **Run the definition of done** — execute the commands the prompt named (tests, linters, `grep` for
  leftovers of the old pattern) rather than trusting the claim that they pass.
- **Spot-check bulk changes** — read a sample of changed files end to end; for analysis tasks, re-derive
  a couple of Codex's numbers or claims from the underlying data.

Fix small misses directly. If the miss is systemic (a whole class of sites skipped or mangled), sharpen
the prompt with what went wrong and rerun rather than hand-patching hundreds of files.

## 6. Present the results

- What changed: files and counts, tied to the spec — and what you verified (commands run, samples read,
  numbers re-derived), with outcomes.
- Discrepancies you found, each marked fixed or flagged; anything from `${LAST}` you did not verify is
  presented as Codex's claim, not yours.
- If Codex declared the task done but the diff is empty or the definition of done fails, say exactly
  that — do not soften it.
