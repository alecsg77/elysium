# Pull-request-only merge and auto-merge policy

## Purpose

Every normal repository change follows **branch → pull request → explicit user
approval → native GitHub squash auto-merge**. This is a safety boundary for the
GitOps control plane: a commit must receive automated validation and approval of its
current diff before Flux can reconcile it.

Opening a PR is allowed after applicable local validation, but it is a request for
review—not authorization to merge. `PR Validate Simple / validate` proves automated
source validation; it never replaces explicit user approval of the current proposed
head SHA.

The rollout uses the existing `@alecsg77` administrative identity for both the
maintainer and coding agents. The server-side ruleset—not identity separation—blocks
direct updates to `main`; agents must still follow this policy even when an
administrative break-glass path exists. Repository settings may be altered only
through the documented break-glass event.

## Required agent flow

1. Create or update a non-`main` branch.
2. Run applicable local validation, commit, and push only that branch.
3. Open or update a PR targeting `main`. If the user has not explicitly approved
   the current diff, leave auto-merge disabled and mark approval as pending in the
   PR template.
4. Report the PR URL, head SHA, validation scope, and remaining operational risk.
   Wait for explicit approval of this **current head SHA**.
5. Record the approved SHA in the PR template and enable native squash auto-merge:

   ```bash
   gh pr merge --auto --squash
   ```

6. A pushed commit invalidates approval. Disable auto-merge if necessary, report the
   new SHA, and obtain fresh approval.
7. Never use `--admin`, force-push `main`, manually merge, or merge through a
   direct Git push.
8. Observe the PR until `PR Validate Simple / validate` succeeds and auto-merge
   completes. Correct failures; do not bypass the ruleset.

GitHub review approvals remain optional. The agent-facing explicit approval above is
a separate authorization boundary, even when the ruleset requires zero reviews.

## Required validation

`PR Validate Simple / validate` is always present. It runs YAML lint, Gitleaks, and
the plaintext-Secret guard on every PR, then adds GitOps rendering/schema validation,
local-chart tests, Coder Terraform validation, or Actions/script checks only for
relevant paths. See [PR validation](pr-validation.md) for the complete matrix and
known limits.

Do not make a path-filtered workflow required: a PR outside its paths would leave the
check pending. The simple workflow's one `validate` job exists specifically to provide
a stable required context for all PRs.

## Bot update policy

Renovate and Dependabot use PR-based auto-merge and are subject to the same ruleset
and `PR Validate Simple / validate` result. Broad Renovate auto-merge remains paused
until R0 update rules are demonstrated. Major upgrades and changes affecting
controllers, CRDs, stateful workloads, storage, Tailscale, or the GitOps control plane
remain outside the automatic R0 category.

## Break-glass

A defective required check may be removed **temporarily** from the ruleset by the
repository owner only. Repair still occurs through a PR with the applicable local
validation recorded manually. Restore the check immediately and add an incident note
to issue #87. Never restore a permanent administrator bypass or use a direct push as
an emergency shortcut.

## Related documentation

- [PR validation](pr-validation.md)
- [Destructive GitOps changes](../runbooks/destructive-gitops-change.md)
- [GitHub break-glass](../runbooks/github-break-glass.md)
