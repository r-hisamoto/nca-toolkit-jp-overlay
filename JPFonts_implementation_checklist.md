# JP フォント拡張 ― 実装計画チェックリスト  
_No-Code Architects Toolkit 日本語フォント収録版_

---

## 0-A. プロジェクト基本情報（参照）

| 項目 | 値 |
|------|----|
| **プロジェクト名** | NCA Toolkit |
| **プロジェクト番号** | 340342563048 |
| **プロジェクト ID** | nca-toolkit-438301 |

---

## 0-B. 前提確認（初回のみ）

| チェック項目 | コマンド / 確認方法 | ✔ |
|--------------|----------------------|---|
| Cloud SDK インストール | `gcloud version` | ✔ |
| Docker 動作確認 | `docker version` | ✔ |
| プロジェクト ID 取得 | `gcloud config get-value project` | ✔ *(nca-toolkit-438301)* |
| Artifact Registry 有効化 | `gcloud services enable artifactregistry.googleapis.com` | ✔ |
| Cloud Run Admin 権限 | `gcloud run services list` | ✔ |

---

## 1. 作業フォルダ作成 ✔

```bash
mkdir ~/nca-font-layer
cd ~/nca-font-layer
```

---

## 2. **確定版 Dockerfile** ✔（“早見表” 全フォント収録）

> ファイル名 **Dockerfile**  
> `curl` 追加・`fonts-kosugi-maru` 条件インストール・`set -eux` など 3 修正点を反映済み。

```dockerfile
# ───────────── Stage 0 ─────────────
FROM stephengpope/no-code-architects-toolkit:latest AS nca-base

# ───────────── Stage 1 ─────────────
FROM nca-base AS nca-jpfonts
SHELL ["/bin/bash", "-ceu", "pipefail", "-o", "errexit"]

# 1) apt フォント & curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fontconfig \
        curl \                    # ① 追加
        fonts-noto-cjk \
        fonts-mplus \
        fonts-kosugi && \
    # bookworm 未満では kosugi-maru 無いのでスキップ可
    (apt-get install -y --no-install-recommends fonts-kosugi-maru || true) && \   # ② 分割＋true
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Google Fonts (.ttf) 取得
RUN install -d -m 0755 /usr/local/share/fonts/jp && cd /usr/local/share/fonts/jp && \
    set -eux; \                  # ③ set -eux
    base="https://github.com/google/fonts/raw/main"; \
    for f in \
      ofl/shipporimincho/ShipporiMincho-Regular.ttf \
      ofl/kaiseidacol/KaiseiDecol-Regular.ttf \
      ofl/kaiseiopti/KaiseiOpti-Regular.ttf \
      ofl/zenkakugothicnew/ZenKakuGothicNew-Regular.ttf \
      ofl/zenmarugothic/ZenMaruGothic-Regular.ttf \
      ofl/delagothicone/DelaGothicOne-Regular.ttf \
      ofl/hachimarupop/HachiMaruPop-Regular.ttf \
      ofl/mochiypopone/MochiyPopOne-Regular.ttf \
      ofl/dotgothic16/DotGothic16-Regular.ttf \
      ofl/reggaeone/ReggaeOne-Regular.ttf \
      ofl/trainone/TrainOne-Regular.ttf \
      ofl/zenkurenaido/ZenKurenaido-Regular.ttf \
      ofl/zenantique/ZenAntique-Regular.ttf \
      ofl/zenantiquesoft/ZenAntiqueSoft-Regular.ttf \
      ofl/yujimai/YujiMai-Regular.ttf \
      ofl/yujisyuku/YujiSyuku-Regular.ttf; do \
        curl -fsSL "${base}/${f}" -O; \
    done

# 3) 権限＆キャッシュ
RUN chmod 644 /usr/local/share/fonts/jp/*.ttf && fc-cache -f -v

ENV LANG=ja_JP.UTF-8 LANGUAGE=ja_JP:ja LC_ALL=ja_JP.UTF-8
# 4) ENTRYPOINT/CMD はベースのまま
```

---

## 3. ビルド & プッシュ

```bash
export PROJECT_ID=$(gcloud config get-value project)

docker build -t gcr.io/${PROJECT_ID}/nca-toolkit-jp-full:latest .
docker push  gcr.io/${PROJECT_ID}/nca-toolkit-jp-full:latest
```

---

## 4. Cloud Run へ差し替えデプロイ

```bash
gcloud run deploy no-code-architects-toolkit \
  --image gcr.io/${PROJECT_ID}/nca-toolkit-jp-full:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --update-env-vars \
    API_KEY=test123,\
    GCP_BUCKET_NAME=nca-toolkit-bucket-erec,\
    STORAGE_PATH=GCP,\
    GCP_SA_CREDENTIALS='(既存値)'
```

---

## 5. 動作確認

```bash
gcloud run exec --region us-central1 no-code-architects-toolkit \
  --command "fc-list | egrep 'Shippori|Kaisei|Zen Kaku|Dela' | head"
```
主要フォント名が表示されれば導入成功。

---

## 6. トラブルシューティング（差分のみ）

| 症状 | 代表的な原因 | 対処 |
|------|--------------|------|
| `curl: command not found` | ベース OS が curl 非搭載 | Dockerfile に curl を追加済み |
| `fonts-kosugi-maru` で BUILD STOP | Debian ≤ buster | `apt-get install … || true` でスキップ |
| `set -e` により RUN で停止 | 個別フォント取得失敗 | 取得 URL を再確認。ログで失敗 URL を特定 |

---

## 7. 参考：現行 Cloud Run Revision スナップショット（READ-ONLY）

```yaml
apiVersion: serving.knative.dev/v1
kind: Revision
metadata:
  name: no-code-architects-toolkit-00005-dw9
  namespace: '340342563048'
  labels:
    serving.knative.dev/service: no-code-architects-toolkit
  annotations:
    run.googleapis.com/execution-environment: gen2
spec:
  containerConcurrency: 1
  timeoutSeconds: 3600
  containers:
  - image: mirror.gcr.io/stephengpope/no-code-architects-toolkit@sha256:2c3d...
    env:
    - name: API_KEY
      value: test123
    # （以下省略）
status:
  conditions:
  - type: Ready
    status: "True"
    message: Deploying revision succeeded …
```

> **目的**: 差し替え前の構成把握・ロールバック時の比較用。  
> 変更は不要、閲覧のみ。

---
