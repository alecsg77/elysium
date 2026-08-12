#!/usr/bin/env sh
# Bootstrap is for a documented new-cluster recovery only; normal changes flow
# through protected pull requests and Flux reconciliation.
set -eu

flux bootstrap github \
  --components-extra=image-reflector-controller,image-automation-controller \
  --token-auth=false \
  --read-write-key=true \
  --owner=alecsg77 \
  --repository=elysium \
  --branch=main \
  --path=clusters/kyrion \
  --private=false \
  --personal
