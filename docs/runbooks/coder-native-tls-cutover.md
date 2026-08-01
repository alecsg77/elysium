# Coder Native TLS and Wildcard Cutover

## Overview

Move Coder from the Tailscale Ingress to its native HTTPS listener only after every lower-risk native-TLS migration has been verified. Coder hosts the execution environment used by dependent tooling, so this is a controlled cutover with a tested recovery path, not a routine manifest change.

## Prerequisites

- A recovery shell or devcontainer that does **not** depend on Coder is available.
- cert-manager, ExternalDNS, and the Tailscale Connector are healthy.
- The current Tailnet Coder endpoint remains operational and its OAuth callback remains registered.
- The resolved Coder Helm chart is rendered locally before changing values. Confirm the chart still supports `coder.tls.secretNames` and inspect its generated HTTPS Service port and probes.
- The OAuth provider has been prepared to accept the new primary Coder URL before the GitOps cutover.

## Required DNS and Certificate Shape

Create a `Certificate` in the `coder` namespace using a standard Kubernetes TLS Secret. It must contain both names:

```text
coder.${PRIVATE_DOMAIN}
*.coder.${PRIVATE_DOMAIN}
```

`*.${PRIVATE_DOMAIN}` does not match `app.coder.${PRIVATE_DOMAIN}`. The nested wildcard is required for Coder workspace applications that use subdomains.

Annotate the Coder Service for both DNS records. The Service remains `ClusterIP`; ExternalDNS publishes the records and the Tailscale Connector routes the Service CIDR. Do not add a LoadBalancer or a TLS-terminating reverse proxy for this migration.

## Procedure

1. Add the namespace-local `Certificate` and wait for `Ready=True`. Confirm the Secret contains `tls.crt` and `tls.key`.
2. Configure Coder's chart-native TLS support with `coder.tls.secretNames`. Set `CODER_ACCESS_URL` to the primary private-domain URL and `CODER_WILDCARD_ACCESS_URL` to the nested wildcard URL.
3. Add the ExternalDNS Service annotation and render the chart. Verify the rendered Service exposes HTTPS and the Coder pod mounts the TLS Secret.
4. Before disabling the Tailscale Ingress, test the direct primary URL from a Tailnet client: certificate chain/SNI, login, OAuth callback, workspace list, a workspace build, agent reconnect, provisioner status, and log streaming.
5. Test a representative workspace application with `subdomain = true`. Existing templates that use `subdomain = false` do not exercise the wildcard path.
6. Update the logstream URL and reseal any dependent `CODER_URL` Secret using the repository's sealed-secret workflow. Redeploy each consumer after the Secret changes. Do not rotate session tokens as part of a hostname-only cutover.
7. Only after all tests pass, disable the Coder Tailscale Ingress and confirm the old Tailnet host is no longer required.

## Live Validation Blockers

This repository change can render the native-TLS configuration but cannot prove the cutover without cluster and OAuth-provider access. Before considering the Tailnet host retired, an operator must verify all checklist items below in the reconciled cluster. In particular, the sealed `CODER_URL` in `apps/kyrion/coder/mux-secrets.yaml` cannot be changed from encrypted data alone; update it through the sealed-secret workflow only after the new endpoint is healthy and only if its consumer is deployed.

## Rollback

Immediately restore the previous Coder access URL, logstream URL, and Tailscale Ingress if certificate issuance, DNS, SNI, OAuth redirects, workspace agents, logstream, or the dependent execution environment fails. Revert the affected Git commit and reconcile Flux from the independent recovery path. Keep the new Certificate and DNS records until the known-good Tailnet path has been verified again.

## Checklist

- [ ] Certificate is ready with the primary and nested wildcard SANs.
- [ ] ExternalDNS created both records and retained its TXT ownership markers.
- [ ] Direct HTTPS validates for the primary hostname and a synthetic nested hostname.
- [ ] OAuth callback, login, workspace build, provisioner, agent reconnect, and logstream work.
- [ ] A subdomain workspace app works.
- [ ] Dependent `CODER_URL` consumers were resealed and restarted.
- [ ] An independent recovery path is still available.
- [ ] The Tailscale Ingress was removed only after every prior check passed.

## Related Documentation

- [Cluster Architecture](../architecture/cluster-architecture.md)
- [Adding or Changing an Application](add-application.md)
- [HelmRelease Recovery](helm-release-recovery.md)
