## Change and risk

- [ ] I identified the affected domain(s): GitOps, charts, Coder, Actions/scripts, functions, or docs.
- [ ] I ran the applicable local validation commands and recorded them below.
- [ ] User approval is pending; this PR intentionally has auto-merge disabled.
- [ ] The user explicitly approved head SHA `<sha>` for merge; I then enabled native auto-merge with `gh pr merge --auto --squash`.

## Destructive or bootstrap changes

- [ ] Not applicable.
- [ ] This change removes or alters a runtime-protected data or recovery-access resource. I followed `docs/runbooks/destructive-gitops-change.md`, including the two-PR sequence and real backup/rollback evidence where applicable.
- [ ] This approved recovery changes a file frozen by `Flux Bootstrap Guard / guard`; I followed `docs/runbooks/github-break-glass.md` and recorded the rollback revision below.

## Validation evidence

<!-- Commands run, relevant output, and rollback reference. Never include secrets, private domains, or host details. -->

## Rollback

<!-- Known-good Git revision and, when applicable, tested backup restore reference. -->
