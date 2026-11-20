FROM ubuntu:24.04@sha256:9c7f200c07e3d4a03e7249d2c16bf66a51120fb876aa2242cf31451412543289 AS unpack
ARG ORCA_VERSION=1.4.266
ARG ORCA_SHA256=a45ca96d3c781b78231d5af2cd534149607d05df9c5b9fdcd545fe6c87ee88b5
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/orca
RUN asset=orca-server-linux-x64.tar.gz \
    && curl -fsSL "https://github.com/stablyai/orca/releases/download/v${ORCA_VERSION}/$asset" -o "$asset" \
    && printf '%s  %s\n' "$ORCA_SHA256" "$asset" | sha256sum --check --strict \
    && mkdir server \
    && tar -xzf "$asset" --strip-components=1 -C server \
    && test -x server/bin/orca-ide

FROM ghcr.io/coder/coder:v2.39.0@sha256:5fb8f624dc0d33be89c72c7b2e384cdc7c2c5ac0d5847348d3aa0edaf058605c AS coder
FROM ubuntu:24.04@sha256:9c7f200c07e3d4a03e7249d2c16bf66a51120fb876aa2242cf31451412543289
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git openssh-client procps tini \
    && rm -rf /var/lib/apt/lists/* \
    && usermod -l coder -d /home/coder -m ubuntu
COPY --from=unpack /tmp/orca/server /opt/orca
COPY --from=coder /opt/coder /usr/local/bin/coder
COPY start.sh /usr/local/bin/start-orca
RUN chmod 0755 /usr/local/bin/start-orca \
    && ln -s /opt/orca/bin/orca-ide /usr/local/bin/orca-ide
ENV HOME=/home/coder \
    ORCA_USER_DATA_PATH=/home/coder/.config/orca
USER coder
WORKDIR /home/coder
EXPOSE 6768
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/start-orca"]
