# Envbuilder ignores Feature installation dependencies, so npm-based Features
# need Node before any Feature runs. Keep the runtime in the official base image.
FROM node:26.13.1-bookworm@sha256:b7087bc4d973034b30854b378ba107f9fab622b47514cb7e2592e41b8bab8d49

ENV LANG=C.UTF-8

# Reuse the base image's UID/GID 1000 for the persistent Coder home.
RUN usermod --login coder --home /home/coder node \
    && groupmod --new-name coder node

# Work around timezone-data issues in the underlying buildpack-deps image.
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y reinstall --no-install-recommends tzdata \
    && echo "Etc/UTC" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*
