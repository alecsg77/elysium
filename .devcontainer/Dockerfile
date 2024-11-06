FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN curl -L https://github.com/kubernetes/kompose/releases/download/v1.34.0/kompose-linux-amd64 -o kompose && \
    chmod +x kompose && \
    mv ./kompose /usr/local/bin/kompose