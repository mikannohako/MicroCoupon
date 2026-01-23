# MicroCoupon

これはDjango、Nginx、Postgresqlを利用した小規模電子クーポンの発行、減算、管理システムです。
このプロジェクトは以下の要件で運用することを想定しています。
このプロジェクトには以下の機能があります。

- 電子クーポンの発行
  - 印刷用PDFデータの出力
  - 電子データとしての発行
- 電子クーポンの減算
  - レジページから商品を選んで支払いをすることで電子クーポンの減算ができます。
- 電子クーポン残高の確認
- 電子クーポンのアクティベート

## VPS デプロイメント設定

### Basic認証の設定

VPS上でデプロイする場合、以下の手順を実行してください：

1. **htpasswdファイルの作成**:
```bash
mkdir -p /home/deploy
docker run --rm httpd:2.4-alpine htpasswd -nbB admin YOUR_PASSWORD > /home/deploy/.htpasswd
chmod 644 /home/deploy/.htpasswd
```

2. **.env ファイルの設定**:
```env
# VPS上のホスト側のhtpasswdファイルパス
BASIC_AUTH_FILE_HOST=/home/deploy/.htpasswd
```

### エラーページ CSS の確認

VPSデプロイ後、Nginxコンテナ内で以下を確認してください：

```bash
# staticfiles の確認
docker compose exec nginx ls -la /app/staticfiles/error-pages/

# htpasswd ファイルの確認  
docker compose exec nginx cat /etc/nginx/.htpasswd
```

両方のファイルが正しくマウントされている必要があります。
