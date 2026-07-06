---
description:
    Run a runtime or UI verification through the Codex CLI (gpt-5.5) following the codex-computer-use skill — a
    verify-only run that drives apps, simulators, or browsers and captures evidence Claude then inspects.
argument-hint: <what to verify — expected behaviour and where it runs (app, simulator, browser, device)>
---

# Codex runtime verification

Apply the `codex-computer-use` skill to independently verify this at runtime: $ARGUMENTS

Follow the skill exactly:

- Confirm a runtime check is actually needed — code reading, typechecking, linting, or tests you can run directly stay
  with you. Launching apps, simulators, or browsers to verify the work needs no permission; ask first only if the run
  could disrupt the user's environment beyond that (closing their apps, changing system settings, touching real accounts
  or data).
- Create the artifact directory with `mktemp -d` under `$TMPDIR` (prompt, last message, screenshots directory), write
  the skill's verify-only prompt (what to verify, how to check, evidence to capture, boundaries), and run
  `codex exec --sandbox danger-full-access`.
- Inspect the evidence before trusting the report: view the screenshots, read the captured logs, and match every
  pass/fail claim to a named artifact; treat unevidenced or contradicted claims as unverified or failed.
- Present pass/fail per item tied to its evidence, note what the run launched and whether it was cleaned up, and if
  `codex` is not installed or fails, report the error and run or describe the check directly instead.
