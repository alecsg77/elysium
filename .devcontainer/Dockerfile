# This custom Dockerfile selects a minimal Bookworm base and applies the
# upstream buildpack-deps timezone-data workaround. Application tooling stays
# in Dev Container Features; build.options in devcontainer.json still passes
# --network=host while those Features are layered onto this image.
ARG VARIANT="bookworm"
FROM buildpack-deps:${VARIANT}-curl

# Set a UTF-8 locale so Unicode renders correctly in locale-aware tools.
ENV LANG=C.UTF-8

# Work around timezone-data issues in buildpack-deps images.
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y reinstall --no-install-recommends tzdata \
    && echo "Etc/UTC" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*
