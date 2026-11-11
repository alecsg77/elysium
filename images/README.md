# Container images

Build contexts for images maintained by Elysium, independently of Coder templates
and Kubernetes deployments. Each `images/<name>/` directory owns its `Dockerfile`,
runtime files, `.dockerignore`, `VERSION` tag, and component README.

| Image | Purpose | Platform |
| --- | --- | --- |
| [orca-hub](orca-hub/README.md) | Central Orca runtime with Coder CLI and SSH access to project workers. | Linux amd64 |

## Build and publication

From the repository root, build a single image with Docker:

```bash
docker build --platform linux/amd64 -t elysium/orca-hub:$(cat images/orca-hub/VERSION) images/orca-hub
```

The required PR validation builds all catalog images when `images/` or the image
publication workflow changes. PRs do not publish images and receive no registry
write credentials. The `Build Images` workflow publishes the catalog to
`ghcr.io/<owner>/<repository>/<name>` after changes merge to `main`, or when manually
dispatched on `main`. Its matrix currently contains `orca-hub`; add each new image
there as well as in this catalog. All catalog images are rebuilt on each matching
push; this small catalog does not need a separate change-selection helper.

Published tags are the image's `VERSION` and `sha-<full-git-commit>`. A version tag
can be rebuilt as the recipe or base image changes; use the commit tag or an image
digest when a deployment must retain a specific build. Registry visibility and pull
credentials follow the consuming application's runbook.

## Updates

Renovate opens reviewed PRs for Dockerfile base/source image tags under `images/`.
Upstream binaries with checksums are updated together by a reviewed change following
the image README; Orca's version and AppImage SHA-256 remain a manual pair.
`VERSION` describes the resulting image and can include a recipe revision such as
`1.4.248-r1` when its wrapper changes without an upstream application release.

Build the image and repeat its runtime acceptance checks before promoting an
update. Never include runtime credentials, SSH keys, or profiles in the build
context. Adding or publishing an image does not deploy it: consumers remain in
`apps/` or `coder/templates/`, and deployment changes follow the normal GitOps PR
flow. Roll back consumers to a previously published commit tag or digest.
