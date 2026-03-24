# MicroCoupon トラブルシューティング

このドキュメントは、セットアップや運用中によく発生する問題と対処方法をまとめたものです。

## 1. セットアップが途中で止まる

### 症状
- `setup.sh` 実行時に `Docker daemon is not running` が表示される
- `Required command not found: docker` または `python3` が表示される

### 対処
1. Docker Desktop を起動し、`docker info` が成功することを確認する
2. `docker compose version` または `docker-compose --version` を確認する
3. `python3 --version` が使えることを確認する
4. プロジェクトルートで `bash ./setup.sh` を再実行する

## 2. .env が反映されない

### 症状
- `setup.sh` を実行しても入力した値が変わらない
- `.env already exists. Skip creating .env` と表示される

### 原因
- `setup.sh` は既存の `.env` がある場合、再生成を行わない仕様

### 対処
1. 現在の `.env` をバックアップする
2. `.env` を削除する
3. `bash ./setup.sh` を再実行して、再入力する

## 3. DB接続エラーが出る

### 症状
- Django コンテナ起動後に DB 接続エラー
- `FATAL: password authentication failed` が表示される

### 確認ポイント
1. `.env` の `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`
2. `docker-compose.yml` の `django` と `db` が同じ環境変数を参照しているか
3. DB の既存ボリュームに古い認証情報が残っていないか

### 対処
1. `.env` の DB 設定を見直す
2. 必要なら以下で DB ボリュームを初期化する

```bash
docker compose down -v
docker compose up -d --build
```

注意: `-v` は DB データを削除します。

## 4. ポート 8080 が使えない

### 症状
- `Ports are not available` などが出て Nginx が起動しない

### 対処
1. 8080 を使用中のプロセスを停止する
2. もしくは `docker-compose.yml` の `nginx.ports` を変更する
3. 変更後に `docker compose up -d --build` を再実行する

## 5. Basic認証で 401 になる

### 症状
- `/admin` にアクセスすると認証に失敗する

### 確認ポイント
1. `.env` の `BASIC_AUTH_FILE_HOST` が正しいパスか
2. そのパスに `.htpasswd` が存在するか
3. コンテナ側で `/etc/nginx/.htpasswd` がマウントされているか

### 対処
1. `.env` の `BASIC_AUTH_FILE_HOST` を修正する
2. `bash ./setup.sh` で `.htpasswd` を再作成する
3. `docker compose restart nginx` を実行する

## 6. 404 / 500 ページが期待通りに出ない

### 症状
- Django のデフォルトエラーページが表示される
- カスタムページが反映されない

### 確認ポイント
1. `DEBUG=False` になっているか
2. Django 側テンプレート (`django/templates/404.html`, `django/templates/500.html`) が存在するか
3. 静的ファイルを更新後に `collectstatic` したか

### 対処
1. `.env` で `DEBUG=False` にする
2. 以下を実行する

```bash
docker compose exec django python manage.py collectstatic --noinput
docker compose restart django nginx
```

## 7. コンテナ名衝突エラー

### 症状
- 既存コンテナと名前が衝突して起動できない

### 対処
1. 通常は `setup.sh` が自動削除する（`AUTO_REMOVE_CONFLICTING_CONTAINERS=1`）
2. 手動で削除する場合

```bash
docker rm -f microcoupon-django microcoupon-postgres microcoupon-nginx
```

## 8. ログ確認コマンド

問題の切り分けには、まず以下のログを確認してください。

```bash
docker compose logs -f
docker compose logs -f django
docker compose logs -f db
docker compose logs -f nginx
```

## 9. それでも解決しない場合

以下をまとめると調査がスムーズです。

1. 実行したコマンド
2. エラーメッセージ全文
3. `docker compose ps` の結果
4. `docker compose logs --tail=200` の結果
5. `.env` のうち機密情報を伏せた設定値
