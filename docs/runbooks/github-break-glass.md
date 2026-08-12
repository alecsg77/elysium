# GitHub merge-control break-glass

## Purpose

This runbook repairs a broken repository safety control without normalizing direct
pushes to `main`.

## When it is allowed

Use break-glass only when `PR Gate / required` is itself defective or unavailable
and blocks the repair PR. It is not a response to a failed application deployment,
a slow reconciliation, or an inconvenient validation result.

## Procedure

1. Record the incident in issue #87 with the failing check, commit SHA, time, and
   intended repair. Do not include private network identifiers or credentials.
2. In GitHub repository Rules, remove **only** `PR Gate / required` from the
   `Protection` ruleset. Keep pull-request-only, deletion, and non-fast-forward
   rules active and do not add a bypass actor.
3. Open a PR that repairs the gate. Run every applicable validator locally and
   attach the exact commands/results to the PR.
4. Enable native squash auto-merge. Do not use `--admin` and do not push directly
   to `main`.
5. Immediately restore `PR Gate / required` in the ruleset after the repair is on
   `main`.
6. Open a harmless follow-up PR to confirm the repaired gate runs and succeeds.
7. Update issue #87 with the restoration time and validation result.

## If GitHub itself is unavailable

Use the pre-verified out-of-band server/cluster recovery channel documented
outside this public repository. Restore a known-good Git state through a PR once
GitHub access is back. Do not document private hostnames, addresses, or credentials
in this runbook.

## Exit criteria

- The ruleset again requires PRs and `PR Gate / required`.
- The bypass list is empty.
- A test PR runs the gate from the current default branch.
- The incident record identifies why break-glass was used and when it ended.
