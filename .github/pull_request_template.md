## Change and risk

- [ ] I identified the affected domain(s): GitOps, charts, Coder, Actions/scripts, functions, or docs.
- [ ] I ran the applicable local validation commands and recorded them below.
- [ ] Merge authorization is pending; this PR intentionally has auto-merge disabled.
- [ ] This PR is wholly within approved plan `<plan reference>`; plan approval authorizes native squash auto-merge.
- [ ] The user explicitly approved this PR; authorization also covers head SHAs derived solely by rebase onto or merge from `main`.
- [ ] This PR contains substantive changes outside its approved plan or after prior PR approval; the user explicitly approved the updated PR.
- [ ] I enabled native auto-merge with `gh pr merge --auto --squash` after recording the applicable authorization above.

## Destructive or bootstrap changes

- [ ] Not applicable.
- [ ] This change removes or alters a runtime-protected data or recovery-access resource. I followed `docs/runbooks/destructive-gitops-change.md`, including the two-PR sequence and real backup/rollback evidence where applicable.
- [ ] This approved recovery changes a file frozen by `Flux Bootstrap Guard / guard`; I followed `docs/runbooks/github-break-glass.md` and recorded the rollback revision below.

## Validation evidence

<!-- Commands run, relevant output, and rollback reference. Never include secrets, private domains, or host details. -->

## Rollback

<!-- Known-good Git revision and, when applicable, tested backup restore reference. -->
