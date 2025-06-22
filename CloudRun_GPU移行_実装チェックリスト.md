# Cloud Run GPU版移行 実装チェックリスト
_NCA Toolkit Gen 2 → Jobs + GPU版デプロイ計画_

---

## 📋 プロジェクト基本情報

| 項目 | 値 |
|------|-----|
| **プロジェクト ID** | nca-toolkit-438301 |
| **プロジェクト番号** | 340342563048 |
| **リージョン** | us-central1 |
| **既存サービス名** | no-code-architects-toolkit |
| **現在のリビジョン** | no-code-architects-toolkit-00009-gwx |

---

## 🎯 移行目標

### 現在の構成
- **HTTP常駐サービス**: Gen 2, CPU 8コア, メモリ 32GiB
- **同時実行**: 80リクエスト
- **用途**: HTTP API エンドポイント

### 移行後の構成
- **CPU Job**: バッチ処理用（軽量処理）
- **GPU Job**: 重い推論処理用（L4 GPU 1枚）
- **GPU Service**: HTTP API用（GPU必要時）

---

## 📝 Phase 0: 前提確認・準備作業

### 0-A. 現在のRevision情報取得 ✔

| チェック項目 | コマンド | 確認内容 | ✔ |
|--------------|----------|----------|---|
| 実行環境確認 | `gcloud run services describe no-code-architects-toolkit --region=us-central1 --format="value(spec.template.metadata.annotations.run.googleapis.com/execution-environment)"` | gen2 であることを確認 | ✔ |
| 現在のイメージURI取得 | 下記コマンド参照 | イメージURIを控える | ✔ |
| 環境変数確認 | Cloud Console または gcloud describe | 6個の環境変数を確認 | ✔ |
| サービスアカウント確認 | `gcloud run services describe` | SA権限を確認 | ✔ |

```bash
# イメージURI取得コマンド
IMAGE_URI=$(gcloud run services describe no-code-architects-toolkit \
    --region=us-central1 \
    --format="value(status.latestReadyRevisionName)") && \
IMAGE_URI=$(gcloud run revisions describe $IMAGE_URI \
    --region=us-central1 \
    --format="value(spec.containers[0].image)")
echo $IMAGE_URI
```

### 0-B. GPU Quota・権限確認 ✔

| チェック項目 | 確認方法 | 必要な値 | ✔ |
|--------------|----------|----------|---|
| GPU Quota確認 | Cloud Console > IAM > Quotas | L4 GPU: 1枚以上 | ✔ |
| Cloud Run Admin権限 | `gcloud run services list` | 実行可能 | ✔ |
| Beta API有効化 | `gcloud beta run jobs list` | 実行可能 | ✔ |
| Artifact Registry権限 | `gcloud artifacts repositories list` | 読み取り可能 | ✔ |

---

## 📝 Phase 1: 既存サービスのCloud Run Job化

### 1-A. CPU Job作成 ✔

```bash
JOB_NAME=nca-toolkit-cpu-job

gcloud beta run jobs create $JOB_NAME \
    --region=us-central1 \
    --image=$IMAGE_URI \
    --execution-environment=gen2 \
    --cpu=8 --memory=32Gi \
    --tasks=1 --max-retries=3 \
    --timeout=1800 \
    --set-env-vars=API_KEY=test123,GCP_BUCKET_NAME=nca-toolkit-bucket-erec,STORAGE_PATH=GCP,GUNICORN_TIMEOUT=1800,GUNICORN_WORKERS=4 \
    --service-account=nca-toolkit-service-account@nca-toolkit-438301.iam.gserviceaccount.com
```

| チェック項目 | 確認内容 | ✔ |
|--------------|----------|---|
| Job作成成功 | `gcloud beta run jobs describe $JOB_NAME --region=us-central1` | ✔ |
| 環境変数設定確認 | 6個の環境変数が正しく設定されている | ✔ |
| リソース設定確認 | CPU 8コア, メモリ 32GiB | ✔ |
| サービスアカウント確認 | 正しいSAが設定されている | ✔ |

### 1-B. CPU Job実行テスト ✔

```bash
# Job実行
gcloud beta run jobs execute $JOB_NAME --region=us-central1

# 実行状況確認
gcloud beta run jobs executions list --region=us-central1

# ログ確認
gcloud beta run jobs executions describe [EXECUTION_NAME] --region=us-central1
```

| チェック項目 | 確認内容 | ✔ |
|--------------|----------|---|
| Job実行成功 | 正常終了 (exit 0) | ✔ |
| ログ出力確認 | エラーなく処理完了 | ✔ |
| 処理時間確認 | 想定時間内で完了 | ✔ |
| リソース使用量確認 | CPU/メモリ使用率を確認 | ✔ |

---

## 📝 Phase 2: GPU版Job/Service追加デプロイ

### 2-A. GPU Job作成（バッチ処理用） ✔

```bash
GPU_JOB=nca-toolkit-gpu-job

gcloud beta run jobs create $GPU_JOB \
    --region=us-central1 \
    --image=$IMAGE_URI \
    --gpu=1 \
    --cpu=8 --memory=32Gi \
    --execution-environment=gen2 \
    --tasks=1 --timeout=1800 \
    --set-env-vars=API_KEY=test123,GCP_BUCKET_NAME=nca-toolkit-bucket-erec,STORAGE_PATH=GCP,GUNICORN_TIMEOUT=1800,GUNICORN_WORKERS=4 \
    --service-account=nca-toolkit-service-account@nca-toolkit-438301.iam.gserviceaccount.com
```

| チェック項目 | 確認内容 | ✔ |
|--------------|----------|---|
| GPU Job作成成功 | L4 GPU 1枚がアタッチされている | ✔ |
| リソース設定確認 | CPU 8コア, メモリ 32GiB, GPU 1枚 | ✔ |
| 環境変数設定確認 | 6個の環境変数が正しく設定 | ✔ |
| タイムアウト設定確認 | 1800秒に設定されている | ✔ |

### 2-B. GPU Service作成（HTTP API用） ✔

```bash
gcloud run deploy no-code-architects-toolkit-gpu \
    --region=us-central1 \
    --image=$IMAGE_URI \
    --gpu=1 \
    --cpu=8 --memory=32Gi \
    --execution-environment=gen2 \
    --concurrency=1 \
    --timeout=1800 \
    --max-instances=2 \
    --set-env-vars=API_KEY=test123,GCP_BUCKET_NAME=nca-toolkit-bucket-erec,STORAGE_PATH=GCP,GUNICORN_TIMEOUT=1800,GUNICORN_WORKERS=4 \
    --service-account=nca-toolkit-service-account@nca-toolkit-438301.iam.gserviceaccount.com \
    --allow-unauthenticated
```

| チェック項目 | 確認内容 | ✔ |
|--------------|----------|---|
| GPU Service作成成功 | デプロイ完了 | ✔ |
| GPU設定確認 | L4 GPU 1枚がアタッチ | ✔ |
| 同時実行設定確認 | concurrency=1 (GPU独占) | ✔ |
| 最大インスタンス確認 | max-instances=1 | ✔ |
| URL取得 | HTTPSエンドポイントが利用可能 | ✔ |

### 2-C. GPU版動作テスト ✔

| チェック項目 | テスト方法 | 確認内容 | ✔ |
|--------------|------------|----------|---|
| GPU Job実行テスト | `gcloud beta run jobs execute $GPU_JOB` | 正常実行・GPU利用確認 | ✔ |
| GPU Service動作テスト | HTTP リクエスト送信 | レスポンス正常 | ✔ |
| GPU利用率確認 | Cloud Monitoring | GPU使用率が表示される | ⬜ |
| パフォーマンス比較 | CPU版 vs GPU版 | 処理時間の改善確認 | ⬜ |

---

## 📝 Phase 3: トリガー・キュー連携設定

### 3-A. Eventarc (Pub/Sub) 設定 ✔

| 用途 | 設定内容 | コマンド例 | ✔ |
|------|----------|------------|---|
| Cloud Storage イベント | ファイルアップロード検知 | `gcloud eventarc triggers create` | ✔ |
| Pub/Sub トピック作成 | メッセージキュー | `gcloud pubsub topics create` | ✔ |
| Job トリガー設定 | Pub/Sub → GPU Job | Eventarc設定 | ✔ |

### 3-B. Cloud Tasks連携 ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| Cloud Tasks キュー作成 | バッチ処理用キュー | ✔ |
| Job実行トリガー設定 | Tasks → CPU Job | ✔ |
| 並列実行制御 | 適切な並列度設定 | ✔ |

### 3-C. n8n HTTP呼び出し設定 ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| GPU Service URL確認 | HTTPSエンドポイント取得 | ⬜ |
| 認証設定 | API_KEY設定 | ⬜ |
| JSON ペイロード設計 | リクエスト形式定義 | ⬜ |
| レスポンス処理設計 | 結果取得方法定義 | ⬜ |

---

## 📝 Phase 4: 監視・運用設定

### 4-A. Cloud Logging設定 ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| CPU Job ログ確認 | 実行ログが正常に出力 | ✔ |
| GPU Job ログ確認 | GPU使用ログが出力 | ✔ |
| GPU Service ログ確認 | HTTPリクエストログ確認 | ✔ |
| エラーログ監視 | アラート設定 | ✔ |

### 4-B. Cloud Monitoring アラート ✔

| 監視項目 | 閾値 | アラート設定 | ✔ |
|----------|------|--------------|---|
| GPU使用率 | 95%以上 (5分継続) | Webhook通知 | ✔ |
| CPU使用率 | 90%以上 | メール通知 | ⬜ |
| メモリ使用率 | 90%以上 | メール通知 | ⬜ |
| Job実行失敗 | 連続3回 | Webhook通知 | ✔ |
| レスポンス時間 | 30秒以上 | メール通知 | ⬜ |
| Cloud Tasks Backlog | 100件超 (10分継続) | Webhook通知 | ✔ |

### 4-C. コスト監視設定 ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| GPU課金監視 | 日次コストアラート | ⬜ |
| 予算アラート設定 | 月次予算上限設定 | ⬜ |
| リソース使用率レポート | 週次レポート設定 | ⬜ |
| 不要リソース検出 | 自動検出設定 | ⬜ |

---

## 📝 Phase 5: セキュリティ強化

### 5-A. Secret Manager移行 ✔

| チェック項目 | 移行内容 | ✔ |
|--------------|----------|---|
| GCP_SA_CREDENTIALS | Secret Manager保存 | ✔ |
| API_KEY | Secret Manager保存 | ✔ |
| Job設定更新 | `--set-secrets` 使用 | ✔ |
| Service設定更新 | `--set-secrets` 使用 | ✔ |

### 5-B. サービスアカウント最適化 ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| 最小権限の原則 | 必要最小限の権限のみ付与 | ⬜ |
| Job専用SA作成 | バッチ処理用SA | ⬜ |
| Service専用SA作成 | HTTP API用SA | ⬜ |
| 権限監査 | 不要な権限の削除 | ⬜ |

### 5-C. ネットワークセキュリティ ✔

| チェック項目 | 設定内容 | ✔ |
|--------------|----------|---|
| VPC Connector設定 | プライベートネットワーク | ⬜ |
| Ingress制御 | 内部トラフィックのみ | ⬜ |
| Egress制御 | 必要な外部接続のみ | ⬜ |
| Cloud Armor設定 | DDoS保護 | ⬜ |

---

## 📝 Phase 6: テスト・検証

### 6-A. 機能テスト ✔

| テスト項目 | テスト内容 | 期待結果 | ✔ |
|------------|------------|----------|---|
| CPU Job基本機能 | 軽量処理実行 | 正常完了 | ⬜ |
| GPU Job基本機能 | 重い推論処理実行 | 正常完了・GPU利用 | ⬜ |
| GPU Service API | HTTP リクエスト処理 | 正常レスポンス | ⬜ |
| 日本語フォント | フォント表示確認 | 文字化けなし | ⬜ |
| 環境変数 | 全設定値確認 | 正しく読み込み | ⬜ |

### 6-B. パフォーマンステスト ✔

| テスト項目 | 測定内容 | 目標値 | 実測値 | ✔ |
|------------|----------|--------|--------|---|
| CPU Job実行時間 | 標準処理時間 | < 60秒 | ___秒 | ⬜ |
| GPU Job実行時間 | 推論処理時間 | < 30秒 | ___秒 | ⬜ |
| GPU Service応答時間 | HTTP レスポンス | < 10秒 | ___秒 | ⬜ |
| 同時実行性能 | 並列処理能力 | 設計値通り | ___ | ⬜ |
| リソース使用率 | CPU/GPU/メモリ | < 80% | ___% | ⬜ |

### 6-C. 負荷テスト ✔

| テスト項目 | 負荷条件 | 確認内容 | ✔ |
|------------|----------|----------|---|
| CPU Job並列実行 | 10Job同時実行 | 正常処理・リソース監視 | ⬜ |
| GPU Service負荷 | 連続リクエスト | レスポンス安定性 | ⬜ |
| スケーリング動作 | 負荷増減 | 自動スケール確認 | ⬜ |
| タイムアウト動作 | 長時間処理 | 適切なタイムアウト | ⬜ |

---

## 📝 Phase 7: 運用移行

### 7-A. 段階的移行 ✔

| 移行段階 | 内容 | トラフィック配分 | ✔ |
|----------|------|------------------|---|
| Phase 1 | GPU版テスト運用 | 既存100% + GPU版テスト | ⬜ |
| Phase 2 | 部分移行 | 既存80% + GPU版20% | ⬜ |
| Phase 3 | 本格移行 | 既存20% + GPU版80% | ⬜ |
| Phase 4 | 完全移行 | GPU版100% | ⬜ |

### 7-B. 監視・アラート確認 ✔

| チェック項目 | 確認内容 | ✔ |
|--------------|----------|---|
| 全アラート動作確認 | テストアラート送信 | ⬜ |
| ダッシュボード確認 | 監視画面表示 | ⬜ |
| ログ集約確認 | 全ログが正常収集 | ⬜ |
| 障害検知確認 | 障害シミュレーション | ⬜ |

---

## 📝 Phase 8: 後片付け・ロールバック準備

### 8-A. 不要リソース削除 ✔

```bash
# テスト完了後の削除コマンド（必要に応じて実行）
gcloud beta run jobs delete $GPU_JOB --region=us-central1
gcloud beta run jobs delete $JOB_NAME --region=us-central1
gcloud run services delete no-code-architects-toolkit-gpu --region=us-central1
```

| チェック項目 | 削除対象 | ✔ |
|--------------|----------|---|
| テスト用Job削除 | 不要なJob削除 | ⬜ |
| 旧Revision削除 | 古いRevision削除 | ⬜ |
| 未使用イメージ削除 | Artifact Registry清理 | ⬜ |
| 一時的リソース削除 | テスト用リソース削除 | ⬜ |

### 8-B. ロールバック手順 ✔

| 緊急時対応 | 手順 | ✔ |
|------------|------|---|
| GPU版→既存版切り戻し | トラフィック100%を既存版に戻す | ⬜ |
| Job停止 | 実行中Jobの緊急停止 | ⬜ |
| アラート停止 | 誤報アラートの一時停止 | ⬜ |
| 設定復旧 | 元の設定への復旧 | ⬜ |

---

## 📊 コスト見積もり

### GPU版追加コスト（月額概算）

| リソース | 使用量 | 単価 | 月額コスト |
|----------|--------|------|------------|
| L4 GPU (Job) | 100時間/月 | $0.35/時間 | $35 |
| L4 GPU (Service) | 50時間/月 | $0.35/時間 | $17.5 |
| CPU (追加分) | 常時稼働 | 既存と同等 | $0 |
| ストレージ | 既存と同じ | 既存と同等 | $0 |
| **合計** | | | **約$52.5/月** |

### コスト最適化ポイント
- GPU使用時間の最小化（必要な処理のみ）
- アイドル時間の削減
- 適切なタイムアウト設定
- 不要なインスタンスの自動停止

---

## 📋 実装完了チェック

### 最終確認項目

| 大項目 | 完了率 | 備考 |
|--------|--------|------|
| Phase 0: 前提確認 | ⬜ ___% | |
| Phase 1: CPU Job化 | ⬜ ___% | |
| Phase 2: GPU版デプロイ | ⬜ ___% | |
| Phase 3: トリガー連携 | ⬜ ___% | |
| Phase 4: 監視設定 | ⬜ ___% | |
| Phase 5: セキュリティ | ⬜ ___% | |
| Phase 6: テスト検証 | ⬜ ___% | |
| Phase 7: 運用移行 | ⬜ ___% | |
| Phase 8: 後片付け | ⬜ ___% | |

### 実装責任者

| 役割 | 担当者 | 連絡先 |
|------|--------|--------|
| **プロジェクトマネージャー** | | |
| **インフラエンジニア** | | |
| **アプリケーションエンジニア** | | |
| **運用エンジニア** | | |

---

**作成日**: 2025年6月20日  
**最終更新**: 2025年6月20日  
**バージョン**: 1.0  
**ドキュメント管理**: NCA Toolkit GPU移行プロジェクト
