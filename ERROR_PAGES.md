# MicroCoupon 環境設定ガイド

## 開発環境での実行

### 1. 環境変数の設定

`.env` ファイルを作成してください：

```env
DEBUG=true
SECRET_KEY=django-insecure-@&j6v3y16l3v55_9qffm(u^qep#zx1yk=e0tb#(ne^b4p3s97_
ADMIN_PATH=admin/
DOMAIN_NAME=localhost:8080
BASE_URL=http://localhost:8080

# Database
POSTGRES_DB=microcoupon
POSTGRES_USER=microcoupon_user
POSTGRES_PASSWORD=microcoupon_pass
```

### 2. エラーページのテスト

開発環境では、以下の URL でエラーページをテストできます：

- 404 エラーページ: `http://localhost:8080/test/404/`
- 500 エラーページ: `http://localhost:8080/test/500/`

## 本番環境での設定

### 重要: エラーページの表示

本番環境で Django エラーページが Nginx に正しく表示されるようにするには、以下の設定が必要です：

#### 1. `.env` の設定

```env
DEBUG=false
SECRET_KEY=your-secret-key-here
```

`DEBUG=false` に設定すると、Django がエラーテンプレート（404.html、500.html）を使用します。

#### 2. Nginx の設定

`nginx/default.conf` では以下のような設定を行ってください：

```nginx
# エラーページの設定
error_page 404 /404.html;
error_page 500 502 503 504 /500.html;

# エラーページの配信
location = /404.html {
    alias /app/staticfiles/404.html;
    internal;
}

location = /500.html {
    alias /app/staticfiles/500.html;
    internal;
}
```

#### 3. Docker イメージのビルド

Dockerfile でエラーテンプレートを staticfiles にコピーします：

```dockerfile
# エラーテンプレートを staticfiles にコピー
RUN mkdir -p /app/staticfiles && \
    cp /app/templates/404.html /app/staticfiles/404.html && \
    cp /app/templates/500.html /app/staticfiles/500.html
```

#### 4. docker-compose の実行

```bash
docker-compose up -d
```

### エラーページのデザイン

エラーテンプレートは以下の機能を備えています：

- **404.html**: ページが見つからないエラー（紫色のグラデーション）
- **500.html**: サーバーエラー（ピンク色のグラデーション、アニメーション付き）

両ページとも以下の要素を含みます：

- Material Icons を使用したアイコン
- レスポンシブデザイン（モバイル対応）
- ホームへ戻るボタン
- 前のページに戻るボタン
- ユーザーフレンドリーなエラーメッセージ

## VPS でのデプロイ

1. GitHub Actions により自動的にデプロイされます
2. エラーテンプレートはコンテナビルド時に staticfiles にコピーされます
3. Nginx が自動的にエラーページを表示します

## トラブルシューティング

### エラーページが表示されない場合

1. `DEBUG=false` に設定しているか確認
2. `/app/staticfiles/404.html` と `/app/staticfiles/500.html` がコンテナ内に存在するか確認
3. Nginx の error_page ディレクティブが正しく設定されているか確認
4. ボリュームマウントが正しいか確認（`/app/staticfiles:/app/staticfiles`）
