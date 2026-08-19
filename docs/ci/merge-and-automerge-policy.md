# Pull-request-only merge and auto-merge policy

## Purpose

Every normal repository change follows **branch → pull request → explicit user
approval → native GitHub squash auto-merge**. This is a safety boundary for the
GitOps control plane: a commit must first receive both the applicable automated
validation and user approval before Flux can reconcile it.

Opening a PR is allowed after the agent has completed applicable local validation,
but it is a request for review—not authorization to merge by itself. `PR Gate /
required` proves automated policy compliance; it does not replace the applicable
user authorization described below.

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

The rollout deliberately uses the existing `@alecsg77` administrative identity
for both the maintainer and coding agents. The server-side ruleset—not identity
separation—blocks direct updates to `main`; agents must still follow this PR-only
policy even when an administrative break-glass path exists. Repository settings
may be altered only through a documented break-glass event.

## Required agent flow

1. Create or update a non-`main` branch.
2. Run the applicable local validation, commit, and push only that branch.
3. Open or update a PR targeting `main`. Identify in the PR template whether
   its authorization comes from an approved plan, an explicit PR approval, or is
   still pending. Leave auto-merge disabled while authorization is pending.
4. Report the PR URL, head SHA, validated scope, remaining risk, and authorization
   source. A PR wholly covered by an approved plan may proceed without a separate
   PR approval; otherwise wait for explicit PR approval after all substantive
   changes are visible in the PR.
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
8. Observe the PR until `PR Gate / required` is successful and auto-merge has
   completed. If it fails, correct the PR; do not bypass the ruleset.

`CODEOWNERS` assigns the repository to `@alecsg77` for ownership visibility.
GitHub review approvals remain optional in this phase. The agent-facing explicit
user approval above is a separate merge authorization and is required even when
the ruleset requires zero GitHub approvals.

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


During the quality-ratchet transition, `required` additionally means the PR added no
yamllint, kubeconform, or Kubernetes Checkov debt relative to the trusted PR base.
It can still be green with explicitly reported historical debt while releases and
debt-remediation PRs proceed in parallel. A new finding, warning, schema skip, or
validator integrity failure blocks the gate. See [PR validation](pr-validation.md)
for the transitional report states and change-separation rule.

Do not add a separate required check with a generic name such as `gate`:
required status contexts must remain unambiguous. Older path-filtered workflows
remain diagnostic-only; remove them in a later PR only after confirming the PR Gate
continues to cover each validation domain.

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
