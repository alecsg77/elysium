FROM ubuntu:24.04@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5 AS unpack
ARG ORCA_VERSION=1.4.248
ARG ORCA_SHA256=c703c986646f4a7c336907bdf159327f997437e4790ee30a415df437b5982e43
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/orca
RUN curl -fsSL "https://github.com/stablyai/orca/releases/download/v${ORCA_VERSION}/orca-linux.AppImage" -o orca.AppImage \
    && printf '%s  orca.AppImage\n' "$ORCA_SHA256" | sha256sum --check --strict \
    && chmod +x orca.AppImage \
    && ./orca.AppImage --appimage-extract >/dev/null

FROM ghcr.io/coder/coder:v2.39.0@sha256:5fb8f624dc0d33be89c72c7b2e384cdc7c2c5ac0d5847348d3aa0edaf058605c AS coder
FROM ubuntu:24.04@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git openssh-client procps tini xauth xvfb \
      libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 \
      libdrm2 libgbm1 libgtk-3-0t64 libnotify4 libnspr4 libnss3 libsecret-1-0 \
      libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 \
      libxrandr2 libxss1 libxtst6 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/* \
    && usermod -l coder -d /home/coder -m ubuntu
COPY --from=unpack /tmp/orca/squashfs-root /opt/orca
COPY --from=coder /opt/coder /usr/local/bin/coder
COPY start.sh /usr/local/bin/start-orca
RUN chmod 0755 /usr/local/bin/start-orca \
    && ln -s /opt/orca/resources/bin/orca-ide /usr/local/bin/orca-ide
ENV HOME=/home/coder \
    ORCA_USER_DATA_PATH=/home/coder/.config/orca \
    ORCA_SERVE_RUNTIME=electron
USER coder
WORKDIR /home/coder
EXPOSE 6768
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/start-orca"]
