# This custom Dockerfile only exists so that build.options (in
# devcontainer.json) can pass --network=host to the buildx run that layers
# devcontainer Features on top of the base image (see the MTU comment there
# for why that matters). All tool installation is done through Features, not
# Dockerfile RUN steps (see the "Features" policy comment in
# devcontainer.json) — this Dockerfile itself stays a single FROM line.
FROM mcr.microsoft.com/devcontainers/base:bookworm
