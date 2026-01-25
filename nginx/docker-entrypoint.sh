#!/bin/sh
# nginx entrypoint: 環境変数を参照して nginx.conf をテンプレートから生成

# ADMIN_PATH のデフォルト値
export ADMIN_PATH="${ADMIN_PATH:-/admin/}"

# テンプレートから /etc/nginx/conf.d/default.conf を生成
envsubst '${ADMIN_PATH}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# nginx を前景プロセスで起動
exec nginx -g "daemon off;"
