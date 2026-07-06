---
name: codex-code-review
description: Run OpenAI's Codex CLI (gpt-5.5) as an independent second-pass code reviewer and verify its findings before presenting them. Identifies the review target (uncommitted changes, base branch, commit SHA, PR checkout, or specific files), runs codex review with a focused prompt into a mktemp artifact directory under $TMPDIR, then checks every important claim against the cited code, separating confirmed issues from unverified Codex suggestions. Use when the user asks for a second opinion or second-pass review, an independent or Codex/GPT review of changes, cross-checking a review with another model, or when a change is broad enough that another agent's perspective is useful. Prefer the normal review process for small local checks; never delegate review just to avoid reading the code. Not for using Codex to write or fix code, installing or configuring the Codex CLI, CI review automation, or reviews Claude can do directly.
license: MIT
---

# Second-pass code review with Codex

Use the Codex CLI (gpt-5.5) as an **independent reviewer** when the user wants a second-pass review, or
when a change is broad enough that another agent's perspective is genuinely useful. Prefer your normal
review process for small, local checks — a single function or file rarely needs a second model. Never
delegate review just to avoid reading the code yourself, and treat Codex's output as **evidence, not
authority**: every finding you present must survive your own verification against the code.

## 1. Identify the review target

Pick exactly one target and note it — it appears in your final summary:

- **Uncommitted changes** — staged, unstaged, and untracked work (`--uncommitted`). The default when the
  user says "my changes".
- **Base branch** — the current branch's diff against its base (`--base <branch>`).
- **Single commit** — one commit by SHA (`--commit <sha>`).
- **PR checkout** — check the PR out first (`gh pr checkout <number>`), then review with
  `--base <the PR's base branch>`.
- **Specific files** — use whichever of the above contains them, and name the files in the prompt so
  Codex focuses there.

## 2. Create the artifact directory

Always under `$TMPDIR` — never a bare `/tmp` or the repository:

```sh
ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-review.XXXXXX")"
REPORT="${ARTIFACT_DIR}/report.md"
PROMPT="${ARTIFACT_DIR}/prompt.md"
```

## 3. Write the prompt and run the review

Write this reference prompt to `${PROMPT}`. It is largely consistent from run to run — append
task-specific context only when it earns its place: requirements the change must meet, risky areas,
expected behaviour, relevant tests, or files you are unsure about.

```markdown
Review these changes as an independent second reviewer.

Focus on:

- correctness: logic errors, broken edge cases, race conditions, resource leaks
- security: injection, authn/authz gaps, unsafe handling of untrusted input
- breaking changes to public interfaces or behaviour that callers rely on

For each finding, cite the file and function or line, describe the concrete failure scenario, and rate
severity (high/medium/low). Skip style and formatting. If you find nothing significant, say so
explicitly.
```

Then run the shape that matches the target from step 1:

```sh
# staged, unstaged, and untracked changes
codex -C "${PWD}" review --uncommitted - < "${PROMPT}" > "${REPORT}"

# current branch against its base branch
codex -C "${PWD}" review --base main - < "${PROMPT}" > "${REPORT}"

# a single commit
codex -C "${PWD}" review --commit <SHA> - < "${PROMPT}" > "${REPORT}"
```

If `codex` is not installed or the command fails, stop here: report the error to the user and offer to
review the changes directly yourself instead. Never fabricate or paraphrase a report that was not
produced.

## 4. Verify the report against the code

Read `${REPORT}`. For every finding that would change what the user does next, open the cited code or
diff and decide for yourself:

- **Confirmed** — you read the code and the failure scenario is real.
- **Not confirmed** — the code already handles the case, the cited line does not exist, or the claim
  misreads the diff. Say why in one sentence; do not silently drop it.
- **Unverified** — plausible but you did not check it (say so explicitly).

Codex reviews the diff, not your conversation — it may flag things the user already decided are fine.
Filter those out rather than re-litigating them.

## 5. Present the results

Structure the user-facing summary so verification status is unmistakable:

- **Confirmed issues** — findings you verified, cited as `file:line`, most severe first.
- **Unverified Codex suggestions** — anything you did not (or could not) check, clearly labelled as
  Codex's claim rather than yours, including findings Codex raised that you judged wrong (with your
  reason).
- If Codex found nothing significant, say that plainly and name the review target it inspected (e.g.
  "Codex reviewed the uncommitted changes and reported no significant issues") — do not pad the summary
  with invented concerns.
