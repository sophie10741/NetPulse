#!/bin/sh
set -eu

# Секретный ключ Django: если не задан, создаём случайный на время работы контейнера
if [ -z "${SECRET_KEY:-}" ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
  export SECRET_KEY
fi

# SSH-ключ приложения для входа на узлы стенда (лежит в общем томе /keys)
if [ ! -f /keys/id_ed25519 ]; then
  ssh-keygen -q -t ed25519 -N "" -f /keys/id_ed25519 -C "netpulse-lab"
fi
chmod 600 /keys/id_ed25519

python manage.py migrate --noinput
python manage.py create_demo_admin

exec "$@"
