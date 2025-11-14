# Known Issues and Resolutions

This knowledge base is automatically updated from resolved GitHub Issues. It provides quick reference for common cluster problems and their solutions.

**Last Updated**: 2025-11-13

## How to Use

1. **Search** for your issue by component, error message, or resource type
2. **Check symptoms** to confirm it matches your situation
3. **Try the documented resolution** before creating a new issue
4. **Create troubleshooting request** if resolution doesn't work or issue is different

## Quick Search

| Component | Common Issues |
|-----------|---------------|
| [Flux CD](#component-flux-cd) | HelmRelease timeouts, variable substitution, source sync |
| [Kubernetes](#component-kubernetes) | Pod crashes, ImagePull errors, resource constraints |
| [Helm](#component-helm) | Chart installation failures, values validation |
| [Networking](#component-networking) | Ingress configuration, service connectivity |
| [Storage](#component-storage) | PVC issues, mount problems |
| [Monitoring](#component-monitoring) | Prometheus, Grafana, Loki issues |
| [Security](#component-security) | Sealed Secrets, certificates |
| [Applications](#component-applications) | App-specific issues |

---

## Component: Flux CD

### Issue: HelmRelease Install Timeout

**Symptoms**:
```
HelmRelease install retries exhausted
Status: InstallFailed
Message: "install retries exhausted"
Pods stuck in ImagePullBackOff
```

**Root Cause**: Default timeout (5m) insufficient for large container images (> 5GB)

**Resolution**:
1. Identify actual deployment time (check pod events for image pull duration)
2. Update HelmRelease `spec.timeout` to actual time + 50% buffer
3. Example: 8min actual → set timeout to `15m`

**Files Modified**: `apps/base/<app>/<app>.yaml` or `apps/kyrion/<app>-values.yaml`

**Validation**:
```bash
flux get hr <release-name> -n <namespace>  # Should show Ready=True
kubectl get pods -n <namespace>  # Should show Running
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:flux, root-cause:timeout

---

### Issue: Variable Substitution Failed

**Symptoms**:
```
Kustomization reconciliation failed
Error: "failed to substitute variables"
Message: "variable ${VAR_NAME} not found"
```

**Root Cause**: Referenced ConfigMap or Secret doesn't exist, or key name mismatch

**Resolution**:
1. Check Kustomization `postBuild.substituteFrom` references
2. Verify ConfigMap/Secret exists: `kubectl get cm,secret -n flux-system`
3. Check key names match exactly (case-sensitive)
4. If missing, create ConfigMap: `kubectl create cm cluster-vars --from-literal=VAR_NAME=value -n flux-system`
5. For secrets, use SealedSecret with `kubeseal`

**Files Modified**: `clusters/kyrion/config-map.yaml` or `clusters/kyrion/sealed-secrets.yaml`

**Validation**:
```bash
flux get kustomization <name>  # Should show Ready=True
kubectl get cm cluster-vars -n flux-system -o yaml  # Verify variable exists
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:flux, root-cause:configuration

---

### Issue: GitRepository Not Syncing

**Symptoms**:
```
GitRepository stuck on old commit SHA
Status: Failed
Message: "failed to checkout"
```

**Root Cause**: Network connectivity issues, SSH key problems, or branch doesn't exist

**Resolution**:
1. Check SSH key secret: `kubectl get secret flux-system -n flux-system`
2. Verify branch exists in repository
3. Test network from cluster: Try manual git clone from debug pod
4. Force reconciliation: `flux reconcile source git flux-system`
5. If SSH key expired, regenerate and update secret

**Files Modified**: `clusters/kyrion/flux-system/gotk-sync.yaml` (if branch changed)

**Validation**:
```bash
flux get sources git  # Should show Ready=True with recent commit
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:flux, root-cause:network, root-cause:authentication

---

## Component: Kubernetes

### Issue: Pod CrashLoopBackOff - Missing ConfigMap

**Symptoms**:
```
Pod in CrashLoopBackOff state
Container exit code: 1
Logs show: "configmap not found" or "file not found: /config/..."
```

**Root Cause**: Pod references ConfigMap that doesn't exist or isn't mounted correctly

**Resolution**:
1. Check pod spec for `configMapRef` or `volumes` referencing ConfigMap
2. Verify ConfigMap exists: `kubectl get cm -n <namespace>`
3. If missing, create ConfigMap in `apps/base/<app>/` directory
4. Add ConfigMap to `kustomization.yaml` resources list
5. Commit and wait for Flux reconciliation

**Files Modified**: `apps/base/<app>/config-map.yaml`, `apps/base/<app>/kustomization.yaml`

**Validation**:
```bash
kubectl get cm -n <namespace>  # ConfigMap should exist
kubectl get pods -n <namespace>  # Pods should be Running
kubectl logs -n <namespace> <pod-name>  # No config errors
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:kubernetes, root-cause:configuration

---

### Issue: ImagePullBackOff Error

**Symptoms**:
```
Pod stuck in ImagePullBackOff
Events show: "Failed to pull image" or "image not found"
```

**Root Cause**: Image doesn't exist, wrong tag, or registry authentication failure

**Resolution**:
1. Verify image exists: Check container registry
2. Check image tag in HelmRelease or deployment
3. If private registry, ensure imagePullSecret configured
4. Check ImagePolicy if using Flux image automation
5. Update image tag to valid version

**Files Modified**: `apps/base/<app>/release.yaml` or `apps/kyrion/<app>-values.yaml`

**Validation**:
```bash
kubectl describe pod -n <namespace> <pod-name>  # Check events
kubectl get pods -n <namespace>  # Should show Running
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:kubernetes, root-cause:image, root-cause:authentication

---

### Issue: Pod OOMKilled - Insufficient Memory

**Symptoms**:
```
Pod restarts frequently
Last termination reason: OOMKilled
Events show: "memory limit exceeded"
```

**Root Cause**: Pod memory usage exceeds resource limits

**Resolution**:
1. Check actual memory usage: `kubectl top pods -n <namespace>`
2. Review pod resource limits in spec
3. Increase memory limit if application legitimately needs more
4. OR optimize application if memory leak suspected
5. Consider node capacity when setting limits

**Files Modified**: `apps/base/<app>/release.yaml` (HelmRelease values.resources)

**Validation**:
```bash
kubectl top pods -n <namespace>  # Memory below limit
kubectl get pods -n <namespace>  # No restarts
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:kubernetes, root-cause:resources

---

## Component: Security

### Issue: SealedSecret Not Decrypting

**Symptoms**:
```
SealedSecret exists but corresponding Secret not created
Pod references secret but "secret not found" error
```

**Root Cause**: SealedSecret encrypted for wrong namespace, wrong certificate, or sealed-secrets controller issue

**Resolution**:
1. Check sealed-secrets controller: `kubectl get pods -n sealed-secrets-system`
2. Verify SealedSecret namespace matches target: `kubectl get sealedsecret -n <namespace>`
3. Check controller logs: `kubectl logs -n sealed-secrets-system -l app.kubernetes.io/name=sealed-secrets`
4. If wrong namespace, recreate with correct `--namespace` flag
5. Ensure using current certificate: `etc/certs/pub-sealed-secrets.pem`

**Recreate command**:
```bash
echo -n "value" | kubectl create secret generic <name> \
  --namespace=<namespace> \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

**Files Modified**: `apps/base/<app>/*-sealed-secret.yaml`

**Validation**:
```bash
kubectl get secret <name> -n <namespace>  # Secret should exist
kubectl describe sealedsecret <name> -n <namespace>  # Check status
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:security, root-cause:configuration

---

## Component: Applications

### Issue: LibreChat MongoDB Verification Error

**Symptoms**:
```
LibreChat MongoDB pod CrashLoopBackOff
Logs show: "container verification failed"
PVC exists but pod won't start
```

**Root Cause**: MongoDB PVC corruption or permission issues

**Resolution**:
1. Check PVC status: `kubectl get pvc -n ai`
2. Delete pod to force restart: `kubectl delete pod -n ai <mongodb-pod>`
3. If persists, delete PVC (data loss warning): `kubectl delete pvc -n ai <mongodb-pvc>`
4. HelmRelease will recreate PVC automatically
5. Restore data from backup if available

**Files Modified**: None (operational fix)

**Validation**:
```bash
kubectl get pods -n ai  # MongoDB pod Running
kubectl logs -n ai <mongodb-pod>  # No verification errors
```

**Related Issues**: N/A (seed entry - known LibreChat issue)

**Last Seen**: 2025-11-13

**Labels**: component:application, root-cause:storage

---

### Issue: AI Apps GPU Allocation Failure

**Symptoms**:
```
Pods stuck in Pending state
Events show: "insufficient gpu.intel.com/i915"
```

**Root Cause**: Intel GPU device plugin not running or GPUs not available

**Resolution**:
1. Check device plugin: `kubectl get pods -n intel-device-plugins-system`
2. Verify GPU resources: `kubectl describe node | grep gpu.intel.com`
3. If device plugin down, check HelmRelease: `flux get hr -n intel-device-plugins-system`
4. Restart device plugin if needed
5. Check GPU is not already allocated to max pods

**Files Modified**: None (operational fix) or `infrastructure/controllers/inteldeviceplugins.yaml`

**Validation**:
```bash
kubectl describe node | grep -A 5 "Allocatable"  # Should show GPU
kubectl get pods -n ai  # Pods should be Running
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:application, root-cause:resources, root-cause:hardware

---

## Component: Networking

### Issue: Tailscale Ingress Not Accessible

**Symptoms**:
```
Tailscale ingress created but service not reachable via *.ts.net
DNS resolution fails
```

**Root Cause**: Tailscale operator not configured correctly or DNS not propagated

**Resolution**:
1. Check Tailscale operator: `kubectl get pods -n tailscale`
2. Verify ingress resource: `kubectl get ingress -n <namespace> --show-labels`
3. Check Tailscale ProxyClass: `kubectl get proxyclass ts-default-proxy-class`
4. Verify DNS configuration: `kubectl get dnsconfig ts-dns -n tailscale`
5. Wait 2-5 minutes for DNS propagation
6. Check Tailscale admin console for device

**Files Modified**: `infrastructure/configs/ts-default-proxy-class.yaml` or `infrastructure/configs/ts-dns.yaml`

**Validation**:
```bash
kubectl get ingress -n <namespace>  # Should show ADDRESS assigned
nslookup <app>.ts.net  # Should resolve
curl https://<app>.ts.net  # Should respond
```

**Related Issues**: N/A (seed entry)

**Last Seen**: 2025-11-13

**Labels**: component:networking, root-cause:configuration

---

## Contributing to Knowledge Base

This knowledge base is **automatically updated** when issues are resolved:

1. Investigation issue created with troubleshooting request
2. Root causes identified and child bug issues created
3. Resolution implemented via PR
4. Issue closed with `status:resolved` label
5. Automated workflow extracts learnings and creates PR to update this file
6. PR merged → Knowledge base updated

**Manual additions**: Feel free to add entries for issues resolved outside this workflow. Follow the format above.

---

## Search Tips

**By Error Message**:
```bash
grep -i "error message" .github/KNOWN_ISSUES.md
```

**By Component**:
```bash
awk '/## Component: Flux CD/,/## Component:/' .github/KNOWN_ISSUES.md
```

**By Resource Type**:
```bash
grep -B 5 -A 20 "HelmRelease" .github/KNOWN_ISSUES.md
```

---

## Related Documentation

- [Troubleshooting Guide](.github/TROUBLESHOOTING.md) - Step-by-step workflow
- [Copilot Instructions](.github/copilot-instructions.md) - Complete system documentation
- [Flux Instructions](.github/instructions/flux.instructions.md) - Flux-specific patterns
- [Kubernetes Instructions](.github/instructions/kubernetes.instructions.md) - K8s best practices

---

**Note**: This is a living document. As more issues are resolved, patterns will emerge and this knowledge base will grow richer and more helpful.
