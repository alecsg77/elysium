# Pull-request-only merge and auto-merge policy

## Purpose

Every normal repository change follows **branch → pull request → applicable user
authorization → native GitHub squash auto-merge**. This is a safety boundary for the
GitOps control plane: a commit must receive automated validation and the applicable
user authorization before Flux can reconcile it.

Opening a PR is allowed after applicable local validation, but it is a request for
review—not authorization to merge by itself. `PR Validate Simple / validate` and
`Flux Bootstrap Guard / guard` prove automated validation; neither replaces the
applicable user authorization described below.

## Authorization scope

User authorization has three deliberately narrow scopes:

1. **Approved plan.** Approval of an implementation plan automatically authorizes
   native squash auto-merge for a PR whose final changes wholly implement that
   plan. Record the plan reference and covered scope in the PR. No redundant
   per-PR or per-SHA approval is required.
2. **Approved PR.** Explicit approval of a PR authorizes that PR and every
   descendant head SHA created solely by a rebase onto, or a merge from, `main`.
   Mechanical branch synchronization does not require disabling auto-merge or
   requesting approval again.
3. **All other changes.** A substantive change outside an approved plan, or a
   substantive change added after PR approval, is not automatically authorized.
   The PR is the user's final opportunity to review that change: keep or return
   auto-merge to disabled until the user explicitly approves the updated PR.

These scopes do not authorize direct updates to `main`, manual merges, force
pushes, or `--admin` merge bypasses.

The rollout uses the existing `@alecsg77` administrative identity for both the
maintainer and coding agents. The server-side ruleset—not identity separation—blocks
direct updates to `main`; agents must still follow this policy even when an
administrative break-glass path exists. Repository settings may be altered only
through the documented break-glass event.

## Required agent flow

1. Create or update a non-`main` branch.
2. Run applicable local validation, commit, and push only that branch.
3. Open or update a PR targeting `main`. Identify in the PR template whether
   its authorization comes from an approved plan, an explicit PR approval, or is
   still pending. Leave auto-merge disabled while authorization is pending.
4. Report the PR URL, head SHA, validation scope, remaining operational risk, and
   authorization source. A PR wholly covered by an approved plan may proceed without
   a separate PR approval; otherwise wait for explicit PR approval after all
   substantive changes are visible in the PR.
5. Record the plan reference or PR approval in the PR template, then enable native
   squash auto-merge with:

   ```bash
   gh pr merge --auto --squash
   ```

6. Preserve approval and auto-merge through a head SHA created solely by rebasing
   onto, or merging from, `main`. For any other substantive post-approval change,
   disable auto-merge, return to step 3, and obtain final PR-level approval.
7. Never use `--admin`, force-push `main`, manually merge, or merge through a
   direct Git push.
8. Observe the PR until every required context succeeds—normally `PR Validate
   Simple / validate` and `Flux Bootstrap Guard / guard`—and auto-merge completes.
   Correct failures; do not bypass the ruleset.

GitHub review approvals remain optional. The agent-facing explicit approval above is
a separate authorization boundary, even when the ruleset requires zero reviews.

## Required validation

`PR Validate Simple / validate` is always present. It runs YAML lint, Gitleaks, and
the plaintext-Secret guard on every PR, then adds GitOps rendering/schema validation,
local-chart tests, Coder Terraform validation, or Actions/script checks only for
relevant paths.

`Flux Bootstrap Guard / guard` is also always present. It runs from trusted `main`
through `pull_request_target` and freezes the Flux root composition, FluxInstance
source files, and the guard workflow itself. A legitimate bootstrap recovery follows
the break-glass procedure rather than weakening the ordinary PR flow.

Do not make a path-filtered workflow required: a PR outside its paths would leave the
check pending. The simple workflow's one `validate` job and the always-run `guard` job
provide stable contexts for all PRs. See [PR validation](pr-validation.md) for the
complete matrix and known limits.

## Bot update policy

Renovate and Dependabot use PR-based auto-merge and are subject to the same ruleset
and required-check results. Broad Renovate auto-merge remains paused
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
