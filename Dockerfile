FROM ghcr.io/stephengpope/no-code-architects-toolkit:latest AS base

# JP fonts 追加
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-noto-cjk fonts-noto-sans-cjk && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*
USER 1000
