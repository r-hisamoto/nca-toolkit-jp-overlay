# NCA Toolkit 運用指針 (2025-06-21改定)

このドキュメントは、`no-code-architects-toolkit` Cloud Run サービスの運用方針と手順を定めたものです。

## 1. 基本方針

**「安定版の固定」** と **「月次での手動パッチ適用」** を基本方針とします。
これにより、予期せぬ変更による本番環境の不安定化を防ぎつつ、セキュリティパッチを定期的に取り込む体制を維持します。

*   **本番環境:** 常に特定の安定版イメージタグを指し、手動承認なしでの更新は行わない。
*   **パッチ適用:** 月に一度、CIが自動ビルドした最新イメージを、手動テストを経てから本番に適用する。
*   **ステージング:** 常設のステージング環境は廃止し、都度 `--no-traffic` でデプロイしたリビジョンをテスト対象とする。

---

## 2. イメージとリポジトリ

### 2.1. 安定版イメージ (本番用)

*   **タグ:** `gcr.io/nca-toolkit-438301/nca-toolkit-jp-full:stable-20250621`
*   **内容:** 日本語フォントを追加した `rev-009` 相当の動作が確認されているバージョン。
*   **役割:** 本番サービス `no-code-architects-toolkit` が常に参照する、固定された安定版。

### 2.2. CIビルドイメージ (パッチ適用候補)

*   **タグ形式:** `gcr.io/nca-toolkit-438301/nca-toolkit-jp-full:ci-YYYYMMDD`
*   **生成元:** GitHub Actions の月次ビルドによって自動生成される。
*   **役割:** 最新のOSパッチなどが適用されたリリース候補。手動テストを経て、問題がなければ新しい安定版のベースとなる。

### 2.3. GitHubリポジトリ

*   **リポジトリ名:** `r-hisamoto/nca-toolkit-ja-overlay`
*   **役割:** ベースイメージに日本語フォントのオーバーレイを適用する `Dockerfile` と、月次ビルド用の GitHub Actions ワークフロー (`monthly-rebuild.yml`) を管理する。

---

## 3. 運用フロー

### 3.1. 月次アップデートフロー

1.  **自動ビルド (毎月1日):**
    *   GitHub Actions が `monthly-rebuild.yml` に基づき、最新のベースイメージとフォントインストールを実行し、`:ci-YYYYMMDD` タグを付けて Artifact Registry に push します。

2.  **手動デプロイとテスト (開発者):**
    *   CIの成功後、開発者は新しい `ci-YYYYMMDD` イメージを、`--no-traffic` オプションを付けて本番サービスにデプロイします。
      ```bash
      gcloud run deploy no-code-architects-toolkit \
        --image gcr.io/nca-toolkit-438301/nca-toolkit-jp-full:ci-YYYYMMDD \
        --region us-central1 --allow-unauthenticated --no-traffic
      ```
    *   発行されたリビジョンURLにアクセスし、主要機能（例: `/v1/media/convert/mp3` が422を返すこと）が正常に動作するかを確認します。

3.  **カナリアリリース (開発者):**
    *   テストで問題がなければ、まずトラフィックの10%を新しいリビジョンに振り向け、ログにエラーが出ていないか監視します。
      ```bash
      gcloud run services update-traffic no-code-architects-toolkit --region us-central1 \
        --to-revisions LATEST=10
      ```

4.  **本番反映 (開発者):**
    *   カナリアリリースで問題がなければ、トラフィックを100%新しいリビジョンに向けます。
      ```bash
      gcloud run services update-traffic no-code-architects-toolkit --region us-central1 \
        --to-latest
      ```
    *   **(重要)** 新しいリビジョンが安定稼働したことを確認後、そのイメージダイジェストを元に新しい安定版タグ（例: `stable-YYYYMMDD`）を付与し、このドキュメントを更新します。

### 3.2. 緊急ロールバック

万が一、アップデート後に問題が発生した場合は、以下のコマンドで即座に安定版に戻します。

```bash
# 安定版イメージに100%トラフィックを戻す
gcloud run services update-traffic no-code-architects-toolkit --region us-central1 \
  --to-revisions no-code-architects-toolkit-XXXXX=100 # 安定版のリビジョン名に置き換える
```
または、安定版タグを指定して再デプロイします。
```bash
gcloud run deploy no-code-architects-toolkit \
  --image gcr.io/nca-toolkit-438301/nca-toolkit-jp-full:stable-20250621 \
  --region us-central1 --allow-unauthenticated
```

---
## 4. 実施済み作業 (2025-06-21)

*   旧ステージングサービス `no-code-architects-toolkit-stg` を削除。
*   `rev-009` 相当のイメージに `stable-20250621` タグを付与。
*   本番サービスが `stable-20250621` を参照するように更新。
*   `nca-toolkit-ja-overlay` リポジトリに月次ビルド用の `Dockerfile` と GitHub Actions ワークフローを設置。
