# Container images

Build contexts for images maintained by Elysium, independently of Coder templates
and Kubernetes deployments. Each `images/<name>/` directory contains:

- `context/`: tracked image inputs, including `Dockerfile` and runtime files.
- `VERSION`: the image's stable SemVer release (`MAJOR.MINOR.PATCH`).
- `README.md`: usage and upstream update notes, outside the build context.

Keep documentation outside `context/`; all tracked files and executable modes in
that directory participate in change detection. Base/source images are digest-pinned
so an upstream tag changing in place cannot silently change a release's inputs.

| Image | Image release | Bundled application | Platform |
| --- | --- | --- | --- |
| [orca-hub](orca-hub/README.md) | 1.0.0 | Orca 1.4.248 | Linux amd64 |

## Build and publication

From the repository root:

```bash
docker build --platform linux/amd64 -t elysium/orca-hub:$(cat images/orca-hub/VERSION) images/orca-hub/context
```

The required PR validation compares image inputs with the PR base and builds only
new or changed images. Documentation-only changes produce an empty build matrix.
New directories are discovered automatically; no workflow matrix needs editing.
PRs do not publish images or receive registry write credentials.

After a merge to `main`, `Build Images` compares against the push's previous commit.
No input changes means the publish job is skipped. Changed inputs require a version
increase. Publication uses `ghcr.io/<owner>/<repository>/<name>:<VERSION>` with OCI
version/revision labels and an input fingerprint. Git SHA tags are not published.

A tag already published with identical inputs is skipped, including on reruns. A
version already associated with other or unknown inputs is rejected; it is never
overwritten. Authentication, network and unexpected registry failures stop the job
rather than being treated as missing images. The check reads remote config metadata
without pulling the image layers.

A manual run on `main` checks the entire catalog and publishes only missing releases.
Use this to recover a missed/failed publication; it does not force a rebuild of an
existing release. Registry visibility and pull credentials follow the application's
runbook.

## Versioning and updates

Image versions follow [Semantic Versioning](https://semver.org/), independently of
bundled application versions. The compatibility contract covers documented runtime
environment variables, volume paths, ports and available tools:

- Increase MAJOR for incompatible contract changes.
- Increase MINOR for compatible features.
- Increase PATCH for compatible fixes and dependency/security updates.

For example, fixing the wrapper around Orca 1.4.248 advances the image from `1.0.0`
to `1.0.1`; adding a compatible capability advances it to `1.1.0`. Stable numeric
SemVer tags are supported; prerelease tags and build metadata are not used by this
catalog. `VERSION` is written into the image's OCI metadata, so changing it is itself
an image input change.

Renovate opens reviewed PRs for Dockerfile source/base tags and digests. Such PRs
must also increment `VERSION` before merging. Upstream binary versions and their
checksums are updated together following the image README. Orca's version and
AppImage SHA-256 remain a manual pair.

Build the image and repeat runtime acceptance checks before promoting an update.
Do not put credentials, SSH keys or runtime profiles in a build context. Publishing
does not deploy an image: consumers remain in `apps/` or `coder/templates/` and
change through GitOps. Roll back a consumer to a previous SemVer release or digest.
Builds still download distribution packages; digest pinning and input comparison
are not a guarantee of bit-for-bit reproducible rebuilds of an unpublished version.
