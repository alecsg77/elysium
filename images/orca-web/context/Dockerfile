FROM node:26.13.1-bookworm@sha256:b7087bc4d973034b30854b378ba107f9fab622b47514cb7e2592e41b8bab8d49 AS extract
ARG ORCA_VERSION=1.4.265
ARG ORCA_SHA256=8a51a08e241899d86775ad33f3af3a9e114b9cb300b79de1e764c922a0337026
WORKDIR /build
RUN curl --fail --silent --show-error --location --retry 2 \
      "https://github.com/stablyai/orca/releases/download/v${ORCA_VERSION}/orca-linux.AppImage" -o orca.AppImage \
    && printf '%s  %s\n' "$ORCA_SHA256" orca.AppImage | sha256sum --check --strict \
    && chmod 0755 orca.AppImage \
    && ./orca.AppImage --appimage-extract >/dev/null
COPY extract-web.cjs .
RUN node extract-web.cjs

FROM nginxinc/nginx-unprivileged:alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY LICENSE.orca /srv/orca-web/LICENSE.orca
COPY --from=extract /web/ /srv/orca-web/
EXPOSE 8080
