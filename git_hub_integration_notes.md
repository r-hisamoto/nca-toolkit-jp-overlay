# GitHub 連携 – 伝達ノート

## 1. 背景

- **目的**: Cloud Run GPU／Kubernetes など複数環境で同じベースイメージを使えるようにし、CI パイプラインを月次で自動再構築する。
- **範囲**: `nca-toolkit-jp-overlay` リポジトリと、ローカル作業ディレクトリ `~/app projects/NCA Tool Kit日本語フォント追加計画/`。

---

## 2. ブランチ & タグ方針

| ブランチ                   | 役割                               |
| ---------------------- | -------------------------------- |
| **main**               | 本番運用。CI ワークフローもここをトリガーに実行        |
| **unified-base-clean** | 今回実装した統一ベースイメージ + CI を取り込む作業ブランチ |

タグ規約は `cpu-YYYYMM` / `gpu-YYYYMM`（月次ビルドで自動作成）。

---

## 3. 開発フロー（ローカル → GitHub）

1. **リポジトリ取得**
   ```bash
   git clone git@github.com:r-hisamoto/nca-toolkit-jp-overlay.git
   cd nca-toolkit-jp-overlay
   ```
2. **バックアップから最新ファイルを反映**
   ```bash
   SRC="$HOME/app projects/NCA Tool Kit日本語フォント追加計画のコピー/"
   DST="$HOME/app projects/NCA Tool Kit日本語フォント追加計画/"
   rsync -avhP --delete --exclude='.git/' --exclude='.DS_Store' "$SRC" "$DST"
   ```
3. **作業ブランチ**
   ```bash
   git switch -c unified-base-clean   # 無ければ新規
   git add .
   git commit -m "feat: unified base & CI"
   git push -u origin unified-base-clean
   ```
4. **プルリクエスト作成（CLI）**
   ```bash
   gh pr create -B main -H unified-base-clean \
     -t "feat: unified base & CI" \
     -b "統一ベースイメージ導入と月次 CI の追加。マージ後タグ切替で本番反映予定。"
   ```
   *GraphQL: no‑history* エラーが出た場合は `main` を merge して履歴を繋げる。
5. **レビュー & マージ**
   - GitHub UI で **Merge pull request** → *Squash and merge* 推奨。
   - マージ後 *Delete branch* で後片付け。
6. **デプロイ反映**
   ```bash
   gcloud run deploy ... --image=gcr.io/PROJECT/nca-toolkit-jp-full:cpu-202506
   # または Kubernetes マニフェストの image タグを書き換えて apply
   ```

---

## 4. トラブルシューティング

| 症状                                    | 原因 / 解決策                                                                      |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| **"branch has no history in common"** | `main` を一度 merge し、共通履歴を作る → `git merge origin/main`                          |
| **Push protection: secret detected**  | SA key などがコミットに混入 → `git filter-repo` や `git rm --cached` で削除し `--force` push |
| **SSH パスフレーズ毎回要求**                    | `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` で macOS キーチェーンに登録            |

---

## 5. よく使うコマンド早見表

```bash
# ブランチ状態
git branch -vv

# 差分確認
git diff --stat main..HEAD

# 無視ファイル確認
git status --ignored -s | head

# CI 手動トリガ (GitHub Actions 内)
gh workflow run monthly-rebuild.yml
```

---

*最終更新 2025‑06‑22*

