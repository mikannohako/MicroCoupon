# MicroCoupon

Django、Nginx、PostgreSQLを利用した小規模電子クーポンの発行・管理・決済システムです。  
店舗での電子クーポン発行、残高管理、商品販売、決済処理をWebアプリケーションで実現します。

## 主な機能

### 電子クーポン管理
- **カード発行**: QRコード付き電子クーポンカードの作成
  - 印刷用PDFデータの生成（QRコード、シリアル番号付き）
  - デジタル形式での発行
- **カードアクティベート**: 発行後のカード有効化処理
  - QRコードスキャンによる有効化
  - シリアル番号入力による有効化
- **残高確認**: カード残高の公開照会機能（認証不要）
  - QRコードスキャンによる残高照会
  - シリアル番号入力による残高照会
  - 取引履歴の表示
- **カード管理**: カードの詳細情報、利用履歴の閲覧・編集

### 商品管理
- 商品の登録・編集・削除
- 商品一覧表示
- 価格・在庫情報の管理

### 販売・決済管理
- レジ機能（POS）での商品選択・決済処理
  - QRコードスキャンによる決済
  - シリアル番号入力による決済
- カード残高からの自動減算
- 取引履歴の記録・閲覧
- 売上データの管理

### ダッシュボード
- 統合管理画面
- カード、商品、売上の総合管理
- 各種操作へのナビゲーション

### QRコード機能
システム全体でQRコードの読み取り機能を利用できます：
- **カード残高照会** (`/cards/`): 公開ページでQRコードをスキャンして残高確認
- **カード有効化** (`/manage/cards/activate/`): QRコードスキャンでカード有効化
- **決済処理** (`/transactions/register/`): レジでQRコードスキャンして決済

すべてのQRコード読み取り機能は [html5-qrcode](https://github.com/mebjas/html5-qrcode) ライブラリを使用しており、スマートフォンやタブレットのカメラで動作します。

## 技術スタック

### バックエンド
- **Django 5.x**: Webアプリケーションフレームワーク
- **PostgreSQL 16**: データベース
- **Python 3.x**: プログラミング言語

### フロントエンド
- HTML/CSS/JavaScript
- **qrcode**: QRコード生成ライブラリ
- **html5-qrcode**: QRコード読み取りライブラリ（カメラアクセス対応）

### インフラ
- **Nginx**: リバースプロキシ・Webサーバー
- **Docker & Docker Compose**: コンテナ化とオーケストレーション
- **Gunicorn**: WSGIサーバー（本番環境用）

### 主要ライブラリ
- `psycopg`: PostgreSQLアダプタ
- `qrcode`: QRコード生成
- `Pillow`: 画像処理
- `reportlab`: PDF生成
- `python-dotenv`: 環境変数管理

## プロジェクト構成

```
MicroCoupon/
├── django/                     # Djangoアプリケーション
│   ├── account/               # ユーザー認証
│   ├── microcoupon/           # クーポンカード管理
│   ├── products/              # 商品管理
│   ├── dashboard/             # 管理ダッシュボード
│   ├── transactions/          # 取引・決済管理
│   ├── config/                # Django設定
│   ├── static/                # 静的ファイル
│   ├── staticfiles/           # 収集された静的ファイル
│   ├── templates/             # グローバルテンプレート
│   ├── requirements.txt       # Python依存パッケージ
│   └── Dockerfile             # Djangoコンテナ定義
├── nginx/                     # Nginx設定
│   └── default.conf           # Nginx設定ファイル
├── docker-compose.yml         # Docker Compose設定
└── .env                       # 環境変数（要作成）
```

## セットアップ

### 前提条件
- Docker及びDocker Composeのインストール
- Git

### 環境変数の設定

プロジェクトルートに`.env`ファイルを作成してください：

**方法1: テンプレートをコピーして作成（推奨）**
```bash
cp .env.template .env
```

**方法2: 手動で作成**
```env
# Django設定
DEBUG=True
SECRET_KEY=your-secret-key-here
ADMIN_PATH=admin

# ドメイン設定
DOMAIN_NAME=localhost:8080
BASE_URL=http://localhost:8080

# データベース設定
POSTGRES_DB=microcoupon
POSTGRES_USER=microcoupon_user
POSTGRES_PASSWORD=microcoupon_pass

# Nginx Basic Auth（本番環境のみ、開発環境ではコメントアウト）
# BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
```

**重要な注意事項:**
- `SECRET_KEY`は必ず変更してください（50文字以上のランダムな文字列を推奨）
- `BASIC_AUTH_FILE_HOST`は開発環境ではコメントアウトまたは削除してください
- 本番環境では`DEBUG=False`に設定し、強力な`SECRET_KEY`を使用してください

### ローカル開発環境での起動

1. **リポジトリのクローン**:
```bash
git clone <repository-url>
cd MicroCoupon
```

2. **Docker Composeで起動**:
```bash
docker compose up -d
```

3. **データベースのマイグレーション**:
```bash
docker compose exec django python manage.py migrate
```

4. **管理者ユーザーの作成**:
```bash
docker compose exec django python manage.py createsuperuser
```

5. **静的ファイルの収集**:
```bash
docker compose exec django python manage.py collectstatic --noinput
```

6. **アクセス**:
- アプリケーション: http://localhost:8080
- 管理画面: http://localhost:8080/admin

## VPS デプロイメント

### Basic認証の設定

本番環境でBasic認証を有効にする場合：

1. **htpasswdファイルの作成**:
```bash
mkdir -p /home/deploy
docker run --rm httpd:2.4-alpine htpasswd -nbB admin YOUR_PASSWORD > /home/deploy/.htpasswd
chmod 644 /home/deploy/.htpasswd
```

2. **.envファイルに追加**:
```env
BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
```

3. **Nginxコンテナでの確認**:
```bash
# staticfilesの確認
docker compose exec nginx ls -la /app/staticfiles/error-pages/

# htpasswdファイルの確認  
docker compose exec nginx cat /etc/nginx/.htpasswd
```

### 本番環境設定

本番環境では以下を変更してください：

```env
DEBUG=False
SECRET_KEY=<長くランダムな文字列>
DOMAIN_NAME=<実際のドメイン名>
BASE_URL=https://<実際のドメイン名>
```

## 開発

### マイグレーションの作成と適用

```bash
# マイグレーションファイルの生成
docker compose exec django python manage.py makemigrations

# マイグレーションの適用
docker compose exec django python manage.py migrate
```

### ログの確認

```bash
# すべてのコンテナのログ
docker compose logs -f

# 特定のサービスのログ
docker compose logs -f django
docker compose logs -f nginx
docker compose logs -f db
```

## トラブルシューティング

### システムにアクセスできない場合

**症状**: Docker Composeが起動しない、またはエラーが発生する

**原因と解決方法**:

1. **`.env`ファイルが存在しない**
   ```bash
   # テンプレートから作成
   cp .env.template .env
   ```

2. **`BASIC_AUTH_FILE_HOST`が設定されているが、ファイルが存在しない**
   - 開発環境では`.env`ファイル内の`BASIC_AUTH_FILE_HOST`行をコメントアウトしてください
   ```env
   # BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
   ```

3. **環境変数が正しく読み込まれない**
   ```bash
   # docker-composeの設定を確認
   docker compose config
   
   # サービスを再起動
   docker compose down
   docker compose up -d
   ```

4. **データベースのマイグレーションが適用されていない**
   ```bash
   docker compose exec django python manage.py migrate
   ```

5. **静的ファイルが収集されていない**
   ```bash
   docker compose exec django python manage.py collectstatic --noinput
   ```

### 管理画面（/admin/）にアクセスできない場合

開発環境では、管理画面はBasic認証で保護されています。

**開発環境で管理画面のBasic認証を無効にする場合:**

1. `nginx/default.conf`を編集して、`/admin/`のBasic認証部分をコメントアウト
2. または、本番用の`.htpasswd`ファイルを作成:
   ```bash
   # htpasswdファイルを作成（ユーザー名: admin, パスワード: admin）
   docker run --rm httpd:2.4-alpine htpasswd -nbB admin admin > nginx/.htpasswd.local
   ```
3. `.env`ファイルを更新:
   ```env
   BASIC_AUTH_FILE_HOST=./nginx/.htpasswd.local
   ```
4. Docker Composeを再起動:
   ```bash
   docker compose down
   docker compose up -d
   ```

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルをご確認ください。

## コントリビューション

バグ報告や機能リクエストはIssuesにてお願いします。  
プルリクエストも歓迎します。

## サポート

問題が発生した場合は、[ERROR_PAGES.md](ERROR_PAGES.md)を参照してください。
