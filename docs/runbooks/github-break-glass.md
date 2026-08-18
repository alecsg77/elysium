# GitHub merge-control break-glass

## Purpose

This runbook repairs a broken repository safety control—or performs an approved
Flux-bootstrap recovery—without normalizing direct pushes to `main`.

## When it is allowed

Use break-glass only when a required validation check is defective or unavailable, or
when an approved bootstrap recovery must change a file deliberately frozen by `Flux
Bootstrap Guard / guard`. It is not a response to a failed application deployment,
slow reconciliation, or inconvenient validation result.

## Procedure

1. Record the incident in issue #87 with the failing check or frozen path, commit
   SHA, time, intended repair, and rollback revision. Do not include private network
   identifiers or credentials.
2. In GitHub repository Rules, remove **only** the necessary required context from
   the `Protection` ruleset. For a bootstrap recovery, remove only `guard` and keep
   `PR Validate Simple / validate` required. Keep pull-request-only, deletion, and
   non-fast-forward rules active and do not add a bypass actor.
3. Open a PR that repairs the check or performs the approved recovery. Run every
   applicable validator locally and attach exact commands/results to the PR.
4. Enable native squash auto-merge only after explicit approval of the current head.
   Do not use `--admin` and do not push directly to `main`.
5. Immediately restore the removed required context after the repair is on `main`.
6. Open a harmless follow-up PR to confirm the repaired check runs and succeeds.
7. Update issue #87 with the restoration time and validation result.

## If GitHub itself is unavailable

Use the pre-verified out-of-band server/cluster recovery channel documented outside
this public repository. Restore a known-good Git state through a PR once GitHub access
is back. Do not document private hostnames, addresses, or credentials here.

## Exit criteria

- The ruleset again requires PRs, `PR Validate Simple / validate`, and `Flux
  Bootstrap Guard / guard`.
- The bypass list is unchanged.
- A test PR runs the repaired check from the current default branch.
- The incident record identifies why break-glass was used and when it ended.
