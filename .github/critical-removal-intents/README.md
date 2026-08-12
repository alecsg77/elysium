# Critical resource R2 intents

A critical R2 operation is deliberately a two-PR operation:

1. Add an intent file for the resource in this directory. It must declare the
   policy resource ID, `operation: remove` or `operation: change`, and non-empty
   `backup` and `rollback` evidence. The normal PR Gate must merge this
   preparation first. For a resource carrying
   `kustomize.toolkit.fluxcd.io/prune: disabled`, this is also the only PR that
   may remove that annotation.
2. In a later PR, remove the intent file and perform exactly the matching R2
   operation. For `remove`, remove the target resource as well; for `change`,
   modify the intended protected resource. The trusted-base guard reports every
   protected field that changed and permits the operation only when the
   already-merged intent matches its resource and operation.

The guard consumes the intent so it cannot authorize a later unrelated R2
operation. It never permits deletion of the five bootstrap composition files or
any change to `clusters/kyrion/kustomization.yaml`'s fixed resource list.

Examples (replace placeholders with real, non-secret references):

```yaml
resource: tailscale/connector
operation: remove
backup: "Not applicable: Connector has no persistent data; recovery commit <sha>."
rollback: "Restore infrastructure/configs/tailscale/connector.yaml from commit <sha>."
```

```yaml
resource: system-upgrade/plan-crd
operation: change
backup: "Plan inventory and CRD backup reference <id>."
rollback: "Restore the prior pinned CRD artifact from commit <sha>."
```
