# K8up controller

K8up provides the shared PVC backup, retention, integrity-check, prune, and
restore API. Restic runs inside K8up's generated Jobs; it is not installed as a
separate cluster component.

The official chart owns the K8up CRDs, ServiceMonitor, and PrometheusRule. The
configured alerts use only operator and kube-state-metrics data, so they do not
require a Pushgateway. Application schedules and repository credentials remain
with the owning application overlay. See the [backup and restore
runbook](../../../docs/runbooks/backup-and-restore.md) for the local-repository
contract and operator-independent Restic recovery.
