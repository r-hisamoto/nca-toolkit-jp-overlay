# Pattern B ‑ CPU Hub → GPU / Job Fan‑out
**目的**: Cloud Run CPU Service を“受付ハブ”とし，Pub/Sub／Cloud Tasks 経由で GPU Job／CPU Job／GKE Pod へ振り分ける。

---
## 0 前提（完了済チェック）
| ✅ | 項目 | 備考 |
|---|---|---|
| [x] | Cloud Run GPU Service / Job デプロイ完了 | _例: nca‑toolkit‑gpu‑job_ |
| [x] | CPU Job デプロイ完了 | _例: nca‑toolkit‑cpu‑job_ |
| [x] | Secret Manager 移行 (API_KEY / SA_KEY) | `roles/secretmanager.secretAccessor` 付与済み |
| [x] | 監視 Webhook (n8n) 作成／疎通テスト | URL: https://…/webhook/0f46… |

---
## 1 リソース作成 & 権限
| # | タスク | コマンド／設定例 | 担当 | 期日 | Done |
|---|---|---|---|---|---|
| 1‑1 | **Pub/Sub Topic: gpu‑tasks** 作成 | `gcloud pubsub topics create gpu-tasks` | Cline | 2025-06-20 | [x] |
| 1‑2 | **Subscription (push) → GPU Job** | `gcloud pubsub subscriptions create gpu-sub --topic=gpu-tasks --push-endpoint=https://.../jobs/nca-toolkit-gpu-job:run` | Cline | 2025-06-20 | [x] |
| 1‑3 | **Cloud Tasks Queue: cpu‑tasks** | `gcloud tasks queues create cpu-tasks --max-dispatches-per-second=5` | Cline | 2025-06-20 | [x] |
| 1‑4 | CPU Service SA → `roles/pubsub.publisher` |  | Cline | 2025-06-20 | [x] |
| 1‑5 | CPU Job SA → `roles/cloudtasks.enqueuer` |  | Cline | 2025-06-20 | [x] |

---
## 2 CPU Service 改修
| # | 実装内容 | 受入基準 | 担当 | PR # | Done |
|---|---|---|---|---|---|
| 2‑1 | 受信リクエスト検証 & 正規化 | 不正パラメータは HTTP 400 | Cline | 2025-06-20 | [x] |
| 2‑2 | GPU 必須判定 → `gpu‑tasks` Publish | 202 Returned < 1 s | Cline | 2025-06-20 | [x] |
| 2‑3 | 軽量バッチ → Cloud Tasks enqueue (`cpu‑tasks`) | タスク payload に `idempotency-key` 含む | Cline | 2025-06-20 | [x] |
| 2‑4 | エラーハンドリング (Backoff + DLQ) | retry 5回，失敗で DLQ へ | Cline | 2025-06-21 | [x] |

---
## 3 GPU Job / Service 設定
| # | タスク | コマンド／設定 | Done |
|---|---|---|---|
| 3‑1 | Subscription でファイル拡張子フィルタ (`.mp4 .mov .wav`) | Attribute `fileType` で判定 | [x] |
| 3‑2 | `--max-retries=3` `--timeout=900` 確認 |   | [x] |
| 3‑3 | 成功後 Cloud Logging に `processingTime` 出力 |   | [x] |

---
## 4 監視 & アラート
| # | メトリクス | しきい値 | 通知チャネル | Done |
|---|---|---|---|---|
| 4‑1 | GPU 使用率 > 95 % が 5 分 | Webhook + Slack (backup) | [ ] |
| 4‑2 | `gpu‑tasks` Backlog > 100 | 同上 | [x] |
| 4‑3 | Job 失敗率 > 2 連続 | 同上 | [ ] |

---
## 5 テスト計画
1. **単体** – CPU Service publish → Pub/Sub message 確認
2. **統合** – テストファイル (100 MB mp4) を Bucket へアップ → end‑to‑end で GPU Job 完了まで追跡
3. **負荷** – 10 並列アップロード → backlog 処理時間・Alert 発火確認

---
## 6 ロールアウト手順
1. 本番 Topic／Queue を `--labels=env=prod` で作成
2. CPU Service 新 Revision を **traffic = 10 %** でカナリア
3. メトリクス OK なら traffic 100 % 切替
4. 旧 Revision 削除

---
## 7 運用
- 毎週 Monday 10:00 JST – backlog / GPU 利用率 をレビュー
- 月次 – コストレポートを BigQuery → Looker Studio へエクスポート

---
## 8 GKE Autopilot GPU Pods Implementation  
<small>Auto‑provision GPU Pod × 4 を Pattern B に組み込む</small>

### 8‑1 リソース作成 & 権限
| # | タスク | コマンド／設定例 | 担当 | 期日 | Done |
|---|---|---|---|---|---|
| 8‑1‑1 | **Autopilot Cluster 作成** | `gcloud container clusters create-auto nca-auto-gpu --region=asia-northeast1` |  |  | [ ] |
| 8‑1‑2 | **Workload Identity Binding**<br>SA `gke-gpu-sa` → Pub/Sub Subscriber | `gcloud iam service-accounts add-iam-policy-binding` |  |  | [ ] |
| 8‑1‑3 | **K8s Deployment** `gpu-runner`<br>requests/limits: `nvidia.com/gpu:1`, `cpu:4`, `memory:16Gi` | manifest in `k8s/gpu-runner.yaml` |  |  | [ ] |
| 8‑1‑4 | **HPA auto-provision** 0→4 Pod | `autoscaling/v2` CPU 70 % |  |  | [ ] |
| 8‑1‑5 | **ServiceAccount → Pub/Sub Ack** | IAM Role `roles/pubsub.subscriber` |  |  | [ ] |

### 8‑2 CPU Service 改修（追記）
| # | 実装内容 | 受入基準 | Done |
|---|---|---|---|
| 8‑2‑1 | GPU Job がビジーなら payload を **`gpu-tasks-gke`** トピックへ publish | backlog metric < 100 | [ ] |
| 8‑2‑2 | `X-Destination` ヘッダでルート選択（`cloud-run`,`gke`）受入 | HTTP 400 on invalid | [ ] |

### 8‑3 Monitoring / Alert
| # | メトリクス | しきい値 | 通知チャネル | Done |
|---|---|---|---|---|
| 8‑3‑1 | **Pod Pending > 2** が 5 分 | Webhook | [ ] |
| 8‑3‑2 | **Cluster GPU 利用率 < 10 %** が 1 日継続（無駄） | Webhook | [ ] |
| 8‑3‑3 | **Subscription ackAge > 10 min** | Webhook | [ ] |

### 8‑4 テスト計画
1. **k8s Deployment 単体** — Dummy Pub/Sub msg → Pod log 確認  
2. **統合** — CPU Service → gpu-tasks-gke → Pod 完了、処理時間計測  
3. **スケール** — 30 ファイル同時投入、Pod auto‑scale 0→4、全処理 < 30 分

### 8‑5 ロールアウト手順
1. Cluster & Deployment を **stg プロジェクト** で検証  
2. `gpu-tasks-gke` Subscription を **push** → stg Pod  
3. OK 後、本番で Pod Replica 上限 = 4、CPU Service パブリッシュロジックを有効化 (環境変数 `ENABLE_GKE_ROUTE=true`)  
4. 1 週間モニタリング後、Replica 上限を必要に応じて 8 まで拡大

---
最終更新: 2025-06-20
