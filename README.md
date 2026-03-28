# MicroCoupon (English)

日本語版は下にあります。

MicroCoupon is a small-scale digital coupon issuing, management, and payment system built with Django, Nginx, and PostgreSQL.  
It enables stores to issue electronic coupons, manage balances, sell products, and process payments via a web application.

## Main Features

### Digital Coupon Management
- **Card Issuance**: Create digital coupon cards with QR codes
  - Generate printable PDF data (with QR code and serial number)
  - Issue cards in digital format
- **Card Activation**: Activate cards after issuance
  - Activation by QR code scan
  - Activation by 4-digit temporary code (or serial number)
- **Balance Check**: Public balance lookup (no authentication required)
  - Check balance by scanning QR code
  - Check balance by entering serial number
  - Issue 4-digit temporary code when QR cannot be scanned (valid for 5 minutes)
  - Countdown display for remaining temporary code time
  - Error message for non-existent serial numbers (returns to lookup screen)
  - Display transaction history
- **Card Management**: View and edit card details and usage history

### Product Management
- Create, edit, and delete products
- Edit and delete from product list via the "Edit Products" button on the register screen
- Product list view
- Price and inventory management

### Sales and Payment Management
- Product selection and checkout in POS register
  - Payment by QR code scan
  - Payment by 4-digit temporary code (or serial number)
- One-time use temporary code (invalidated after successful payment/activation)
- Automatic deduction from card balance
- Transaction history recording and viewing
- Sales data management

### Dashboard
- Integrated management screen
- Centralized management for cards, products, and sales
- Navigation to each operation

### QR Code Features
The system supports QR code scanning in multiple workflows:
- **Card Balance Lookup** (`/cards/`): Public page for QR-based balance checks
- **Card Activation** (`/manage/cards/activate/`): Activate cards with QR scan
- **Payment Processing** (`/transactions/register/`): Scan QR at register for payment

All QR scanning features use [html5-qrcode](https://github.com/mebjas/html5-qrcode) and work with smartphone/tablet cameras.

## Tech Stack

### Backend
- **Django 5.x**: Web application framework
- **PostgreSQL 16**: Database
- **Python 3.x**: Programming language

### Frontend
- HTML/CSS/JavaScript
- **qrcode**: QR code generation library
- **html5-qrcode**: QR code scanning library (camera access)

### Infrastructure
- **Nginx**: Reverse proxy and web server
- **Docker & Docker Compose**: Containerization and orchestration
- **Gunicorn**: WSGI server (production)

### Key Libraries
- `psycopg`: PostgreSQL adapter
- `qrcode`: QR code generation
- `Pillow`: Image processing
- `reportlab`: PDF generation
- `python-dotenv`: Environment variable management

## Project Structure

```text
MicroCoupon/
|- django/                     # Django application
|  |- account/                 # User authentication
|  |- microcoupon/             # Coupon card management
|  |- products/                # Product management
|  |- dashboard/               # Admin dashboard
|  |- transactions/            # Transactions and payments
|  |- config/                  # Django settings
|  |- static/                  # Static files
|  |- staticfiles/             # Collected static files
|  |- templates/               # Global templates
|  |- requirements.txt         # Python dependencies
|  `- Dockerfile               # Django container definition
|- nginx/                      # Nginx configuration
|  `- default.conf             # Nginx config
|- docker-compose.yml          # Docker Compose config
`- .env                        # Environment variables (to be created)
```

## Setup

### Prerequisites
- Docker and Docker Compose installed
- Python 3.x installed
- Git installed

---

### Common Setup

These steps are required regardless of whether you use the startup script.

1. **Nginx configuration**

Configure `nginx/MicroCoupon.conf` like this:

```nginx
# Redirect HTTP to HTTPS
server {
  listen 80;
  lisete [::]:80;
  server_name your_servername;

  location / {
    return 301 https://$host$request_uri;
  }

# Redirect to MicroCoupon using HTTPS
server {
  listen 80;
  listen [::]:80;
  server_name your_servername;

  ssl_certificate your_ssl_certificate.pem;
  ssl_certificate_key /etc/letsencrypt/live/mikannohako.dev/privkey.pem;

  location / {
    return http://localhost:8080;
  }
}
}
```

As long as requests are ultimately redirected to `localhost:8080`, any equivalent setup is fine.
The sample above uses HTTPS, but HTTP-only should also work.

2. **Reload Nginx config**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If `sudo nginx -t` returns errors, fix them first and then run `sudo systemctl reload nginx`.

---

### One-Command Initial Setup for Linux

Right after cloning the repository, run:

```bash
chmod +x setup.sh
./setup.sh
```

Because setup is interactive, initial configuration is straightforward.

Recommended production settings:

```env
DEBUG=False
SECRET_KEY=<long-random-string>
DOMAIN_NAME=<your-domain>
BASE_URL=https://<your-domain>
```

When using `setup.sh`, `BASE_URL` and `SECRET_KEY` are automatically configured.

What this script does:
- Generates `.env` from `.env.template` when `.env` does not exist (`SECRET_KEY` auto-generated)
- Creates `.htpasswd` for Basic Auth
- Automatically removes conflicting existing containers (`microcoupon-django` / `microcoupon-postgres` / `microcoupon-nginx`)
- Starts Docker containers (including build)
- Runs DB migrations
- Collects static files
- Creates/updates Django admin user (`user_type=admin`)

Default admin credentials:
- Username: `admin`
- Password: `admin1234`

To disable automatic removal of conflicting containers:

```bash
AUTO_REMOVE_CONFLICTING_CONTAINERS=0 ./setup.sh
```

---

### Manual Setup

1. **Clone repository**:
```bash
git clone https://github.com/mikannohako/MicroCoupon.git
cd MicroCoupon
```

2. **Set environment variables**:

Create `.env` in the project root:

```env
# Database
POSTGRES_DB=microcoupon_db
POSTGRES_USER=microcoupon_user
POSTGRES_PASSWORD=your_secure_password

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
DOMAIN_NAME=localhost:8080
BASE_URL=http://localhost:8080

# Basic Authentication option
BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
```

3. **Start with Docker Compose**:
```bash
docker compose up -d
```

4. **Run database migrations**:
```bash
docker compose exec django python manage.py migrate
```

5. **Create admin user**:
```bash
docker compose exec django python manage.py createsuperuser
```

6. **Collect static files**:
```bash
docker compose exec django python manage.py collectstatic --noinput
```

7. **Access**:
- Application: http://localhost:8080
- Admin: http://localhost:8080/admin

Values may vary depending on `.env` configuration.

## Development

### Create and Apply Migrations

```bash
# Generate migration files
docker compose exec django python manage.py makemigrations

# Apply migrations
docker compose exec django python manage.py migrate
```

### Check Logs

```bash
# All container logs
docker compose logs -f

# Specific services
docker compose logs -f django
docker compose logs -f nginx
docker compose logs -f db
```

## Contribution

Please report bugs and feature requests via Issues.  
Pull requests are also welcome.

## Support

If you encounter problems, see [ERROR_PAGES.md](ERROR_PAGES.md).  
If you still need help, contact the author.

## License and Copyright

This project is released under the MIT License. For details, see [LICENSE](LICENSE).

&copy; 2026 mikannohako All Rights Reserved.

---

# MicroCoupon (日本語)

Django、Nginx、PostgreSQLを利用した小規模電子クーポンの発行・管理・決済システムです。  
店舗での電子クーポン発行、残高管理、商品販売、決済処理をWebアプリケーションで実現します。

## 主な機能

### 電子クーポン管理
- **カード発行**: QRコード付き電子クーポンカードの作成
  - 印刷用PDFデータの生成（QRコード、シリアル番号付き）
  - デジタル形式での発行
- **カードアクティベート**: 発行後のカード有効化処理
  - QRコードスキャンによる有効化
  - 4桁一時コード（またはシリアル番号）入力による有効化
- **残高確認**: カード残高の公開照会機能（認証不要）
  - QRコードスキャンによる残高照会
  - シリアル番号入力による残高照会
  - QRが読めない場合の4桁一時コード発行（有効期限5分）
  - 4桁一時コードの残り時間カウントダウン表示
  - 存在しないシリアル番号入力時のエラーメッセージ表示（照会画面に戻る）
  - 取引履歴の表示
- **カード管理**: カードの詳細情報、利用履歴の閲覧・編集

### 商品管理
- 商品の登録・編集・削除
- レジ画面の「商品を修正」ボタンから一覧表示で編集・削除
- 商品一覧表示
- 価格・在庫情報の管理

### 販売・決済管理
- レジ機能（POS）での商品選択・決済処理
  - QRコードスキャンによる決済
  - 4桁一時コード（またはシリアル番号）入力による決済
- 4桁一時コードのワンタイム利用（決済・有効化成功時に無効化）
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
- Docker及びDocker Composeがインストール済み
- Python 3.xがインストール済み
- Gitがインストール済み

---

### 共通セットアップ

スタートアップスクリプトの使用にかかわらずに行わなければならないセットアップです。

1. **Nginx の設定**

`nginx/MicroCoupon.conf` では以下のような設定を行ってください：

```nginx
# HTTPからHTTPSにリダイレクト
server {
  listen 80;
  lisete [::]:80;
  server_name your_servername;

  location / {
    return 301 https://$host$request_uri;
  }

# HTTPSを利用したMicroCouponへのリダイレクト
server {
  listen 80;
  listen [::]:80;
  server_name your_servername;

  ssl_certificate your_ssl_certificate.pem;
  ssl_certificate_key /etc/letsencrypt/live/mikannohako.dev/privkey.pem;

  location / {
    return http://localhost:8080;
  }
}
}
```

最終的に「localhost:8080」にリダイレクトできれば正直何でもいいです。
上記ではHTTPSを利用していますが、HTTPでも動くはずです。

2. **Nginxの設定を更新**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

※`sudo nginx -t`でエラーが発生した場合は修正してから`sudo systemctl reload nginx`を実行してください。

---

### Linux向けワンコマンド初期セットアップ

リポジトリをcloneした直後に、以下を実行すると初期設定を一括実行できます。
初期設定は対話型で行われるため簡単に設定できます。

```bash
chmod +x setup.sh
./setup.sh
```

本番環境の推奨設定：

```env
DEBUG=False
SECRET_KEY=<長くランダムな文字列>
DOMAIN_NAME=<実際のドメイン名>
BASE_URL=https://<実際のドメイン名>
```
※セットアップスクリプトを利用した場合`BASE_URL`と`SECRET_KEY`は自動で設定されます。

このスクリプトが実施する内容:
- `.env` 未作成時に `.env.template` から生成（`SECRET_KEY` 自動生成）
- Basic認証用 `.htpasswd` の作成
- 既存の同名コンテナ（`microcoupon-django` / `microcoupon-postgres` / `microcoupon-nginx`）があれば自動削除して衝突回避
- Dockerコンテナ起動（build含む）
- DBマイグレーション
- 静的ファイル収集
- Django管理者ユーザーの作成/更新（`user_type=admin`）

管理者ユーザーの既定値:
- ユーザー名: `admin`
- パスワード: `admin1234`


同名コンテナの自動削除を無効化したい場合:

```bash
AUTO_REMOVE_CONFLICTING_CONTAINERS=0 ./setup.sh
```

---

### 手動で行う場合

1. **リポジトリのクローン**:
```bash
git clone https://github.com/mikannohako/MicroCoupon.git
cd MicroCoupon
```

2. **環境変数の設定**:

プロジェクトルートに`.env`ファイルを作成してください：

```env
# データベース設定
POSTGRES_DB=microcoupon_db
POSTGRES_USER=microcoupon_user
POSTGRES_PASSWORD=your_secure_password

# Django設定
SECRET_KEY=your-secret-key-here
DEBUG=True
DOMAIN_NAME=localhost:8080
BASE_URL=http://localhost:8080

# Django管理画面に追加でBasic認証を設ける場合（オプション）
BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
```

3. **Docker Composeで起動**:
```bash
docker compose up -d
```

4. **データベースのマイグレーション**:
```bash
docker compose exec django python manage.py migrate
```

5. **管理者ユーザーの作成**:
```bash
docker compose exec django python manage.py createsuperuser
```

6. **静的ファイルの収集**:
```bash
docker compose exec django python manage.py collectstatic --noinput
```

7. **アクセス**:
- アプリケーション: http://localhost:8080
- 管理画面: http://localhost:8080/admin

※.envファイルの設定により変動します。

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

## コントリビューション

バグ報告や機能リクエストはIssuesにてお願いします。  
プルリクエストも歓迎します。

## サポート

問題が発生した場合は、[ERROR_PAGES.md](ERROR_PAGES.md)を参照してください。
それでもわからなければ制作者にお問い合わせください。気付き次第返信します。

## ライセンス・著作権

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルをご確認ください。

&copy; 2026 mikannohako All Rights Reserved.