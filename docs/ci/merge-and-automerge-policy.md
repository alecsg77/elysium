# Pull-request-only merge and auto-merge policy

## Purpose

Every normal repository change follows **branch → pull request → native GitHub
squash auto-merge**. This is a safety boundary for the GitOps control plane: a
commit must first receive the applicable automated validation before Flux can
reconcile it.

The initial rollout deliberately uses the existing `@alecsg77` administrative
identity for both the maintainer and coding agents. After the server-side ruleset
migration, the ruleset—not identity separation—blocks direct updates to `main`.
Until then, this remains an unmitigated repository-settings gap and agents must
still follow the PR-only client policy. An administrator can alter repository
settings only through a documented break-glass event.

## Required agent flow

1. Create or update a non-`main` branch.
2. Push only that branch.
3. Open or update a PR targeting `main`.
4. Enable native auto-merge with:

   ```bash
   gh pr merge --auto --squash
   ```

5. Never use `--admin`, force-push `main`, or merge through a direct Git push.
6. Observe the PR until `PR Gate / required` is successful and auto-merge has
   completed. If it fails, correct the PR; do not bypass the ruleset.

`CODEOWNERS` assigns the repository to `@alecsg77` for ownership visibility. No
review approval is required in this first phase; the fail-closed automated gate
is the merge condition.

## Monorepo gate

`PR Gate / required` is the only required status check after the repository
ruleset is migrated. It always runs and:

- performs baseline secret/YAML checks and the trusted critical-resource guard;
- detects which domains changed;
- runs only the GitOps, Helm, Coder, Actions/scripts, and Fission-spec validators
  relevant to the PR;
- fails when any applicable validator fails, is cancelled, or is unexpectedly
  skipped;
- accepts an intentionally skipped validator only when the change detector marked
  that domain as not applicable.

Do not add a separate required check with a generic name such as `gate`:
required status contexts must remain unambiguous. During bootstrap, older
path-filtered workflows remain diagnostic-only; remove them in a later PR only
after the ruleset requires this fan-in context.

## Bot update policy

Renovate and Dependabot use PR-based auto-merge and are subject to the same
ruleset and `PR Gate / required` result. During the rollout, broad Renovate
auto-merge is paused. It may be restored only for demonstrated R0 updates after
the gate is active; major upgrades and changes that affect controllers, CRDs,
stateful workloads, storage, Tailscale, or the protected GitOps control plane
remain outside the automatic R0 category.

## Break-glass

A defective gate may be removed **temporarily** from the ruleset by the
repository owner only. The repair still occurs in a PR, with all applicable
validators run and recorded manually before merge. Restore the rule immediately
and add an incident note to issue #87. Never restore a permanent administrator
bypass or use a direct push as an emergency shortcut.

## Related documentation

- [PR validation](pr-validation.md)
- [Destructive GitOps changes](../runbooks/destructive-gitops-change.md)
- [GitHub break-glass](../runbooks/github-break-glass.md)
