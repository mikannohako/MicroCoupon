#!/bin/sh
set -e
ADMIN_PATH="${ADMIN_PATH:-admin/}"
case "$ADMIN_PATH" in */) ;; *) ADMIN_PATH="${ADMIN_PATH}/" ;; esac
NGINX_ADMIN_PATH="/${ADMIN_PATH#/}"
sed "s|\${NGINX_ADMIN_PATH}|$NGINX_ADMIN_PATH|g" /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'