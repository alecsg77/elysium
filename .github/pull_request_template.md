## Change and risk

- [ ] I identified the affected domain(s): GitOps, charts, Coder, Actions/scripts, functions, or docs.
- [ ] I ran the applicable local validation commands and recorded them below.
- [ ] User approval is pending; this PR intentionally has auto-merge disabled.
- [ ] The user explicitly approved head SHA `<sha>` for merge; I then enabled native auto-merge with `gh pr merge --auto --squash`.

## Quality ratchet

- [ ] No new yamllint, kubeconform, or Kubernetes Checkov debt was introduced; I reviewed the PR Gate quality-ratchet summary.
- [ ] This PR reduces inherited quality debt; I recorded the validator/report result below. *(Optional.)*
- [ ] This is a quality-policy change only; it does not also change manifests or functions evaluated by that policy.

## Critical / destructive changes

- [ ] Not applicable.
- [ ] This is R1: I described the affected critical resource or ownership/access-plane field below.
- [ ] This is R2: I followed `docs/runbooks/destructive-gitops-change.md`, including the required two-PR intent/consumption sequence and backup/rollback evidence.

## Validation evidence

<!-- Commands run, relevant output, and rollback reference. Never include secrets, private domains, or host details. -->

## Rollback

<!-- Git revert/known-good commit and, when applicable, tested backup restore reference. -->
