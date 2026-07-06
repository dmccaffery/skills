---
name: codex-computer-use
description: Use OpenAI's Codex CLI (gpt-5.5) as a separate local verification agent when checking work requires real runtime interaction — driving a UI, taking screenshots, exercising a simulator, browser, or device, or an independent runtime check outside the current context. Writes a verify-only prompt (expected behaviour, steps, evidence to capture, boundaries) into a mktemp artifact directory under $TMPDIR, runs codex exec with the sandbox off, then inspects the returned screenshots and logs before trusting any pass/fail claim. Use when verifying UI changes end to end, checking what an app, web page, or simulator actually renders or does, capturing screenshots, or reproducing runtime behaviour. Launching apps, simulators, or browsers to verify requested work needs no permission; ask first only when a run could disrupt the user's environment — closing their apps, changing system settings, or touching real accounts or data. Not for code reading, typechecking, linting, or tests Claude can run directly.
license: MIT
---

# Runtime and UI verification with Codex

Use the Codex CLI (gpt-5.5) as a **separate local verification agent** when confirming work requires
observing a real runtime: interacting with a UI, taking screenshots, exercising a simulator, browser,
or device, or independently reproducing behaviour outside your current context. It completes the Codex
trio — `codex-code-review` reviews changes, `codex-coding-task` makes them, this skill **watches them
run**. As with both siblings, what comes back is **evidence, not authority**: a "pass" you have not
seen the evidence for is a claim.

Do not reach for this when a static check answers the question — code reading, typechecking, linting,
or tests you can run directly stay with you.

## 1. Decide whether the run needs consent

Launching apps, simulators, or browsers to verify the requested work is fine **without asking**. Ask
the user first only when the run could disrupt their environment beyond that:

- closing or restarting applications they may be using
- changing system settings (display, network, permissions, default apps)
- acting on real accounts, real user data, or anything sent to an external service

When in doubt about which side a step falls on, ask.

## 2. Create the artifact directory

Always under `$TMPDIR` — never a bare `/tmp` or the repository:

```sh
ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-verify.XXXXXX")"
PROMPT="${ARTIFACT_DIR}/prompt.md"
LAST="${ARTIFACT_DIR}/last-message.md"
SHOTS="${ARTIFACT_DIR}/screenshots"
mkdir -p "${SHOTS}"
```

## 3. Write the verification prompt and run codex

Write this reference prompt to `${PROMPT}`, substituting the real `${SHOTS}` path and filling every
section. The framing is strictly **verify-only** — Codex observes and reports; it never fixes.

```markdown
You are a verification agent. Observe and report — do not fix, refactor, or modify the code or
configuration under test.

## What to verify

<the expected behaviour, stated so each item is checkably true or false>

## How to check

<the concrete steps: what to build or launch, where to navigate, what to interact with>

## Evidence to capture

Save screenshots and captured logs under <the SHOTS path>. For each item report pass or fail with
the exact observed behaviour — values, on-screen text, error messages — not a paraphrase, and name
the screenshot or log that shows it.

## Boundaries

Interact only with <the named apps, simulators, or pages>. Use test accounts and fixture data only —
never real accounts or user data. Do not change system settings. When finished, close what you
opened and leave the environment as you found it.
```

UI automation cannot run inside Codex's own sandbox, so this skill runs with it off — which is exactly
why the Boundaries section above is not optional:

```sh
codex -C "${PWD}" exec --sandbox danger-full-access --output-last-message "${LAST}" - < "${PROMPT}"
```

Runtime checks can take several minutes (booting simulators, building apps) — allow a generous
timeout. If `codex` is not installed or the command fails, stop here: report the error, then either
run whatever parts you can directly (build, launch, capture logs) or tell the user exactly what to
check by hand. Never report a verification that did not run.

## 4. Inspect the evidence

Read `${LAST}`, then check its claims against what was actually captured:

- **Look at the screenshots yourself** — confirm each one shows the screen and state the report says
  it shows. If you cannot view an image, treat whatever it supposedly proves as unverified.
- **Read the captured logs** — a "no errors" claim is checked against the log, not accepted from the
  summary.
- **Match evidence to claims** — a pass with no named screenshot or log entry is a claim, not a
  result; a claim the evidence contradicts is a failure, whatever the summary says.

If the evidence is missing or contradicts the report, rerun with sharper instructions or check the
disputed item directly — do not paper over the gap.

## 5. Present the results

- Pass/fail per verified item, each tied to its evidence (reference the screenshot or log path under
  `${ARTIFACT_DIR}` so the user can look too).
- Separate items you verified from Codex claims whose evidence you could not confirm, and say which.
- Note what the run touched: what was launched, and whether it was closed and the environment left as
  found.
- If verification failed or the evidence is inconclusive, say exactly that — an inconclusive run is
  not a pass.
