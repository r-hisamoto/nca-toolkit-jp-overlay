# 公式イメージは Docker Hub 配信
FROM stephengpope/no-code-architects-toolkit:latest AS base

# --- JP fonts 追加 ---
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-noto-cjk && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*
USER 1000

# 環境変数を設定
ENV API_KEY=dummy-key
