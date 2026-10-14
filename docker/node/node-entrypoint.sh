#!/bin/sh
set -eu

# Уникальные ключи хоста для каждого контейнера
ssh-keygen -A

# Ждём публичный ключ приложения (его создаёт контейнер netpulse при первом запуске)
for _ in $(seq 1 60); do
  [ -f /keys/id_ed25519.pub ] && break
  sleep 1
done
if [ -f /keys/id_ed25519.pub ]; then
  install -m 600 /keys/id_ed25519.pub /root/.ssh/authorized_keys
else
  echo "WARNING: /keys/id_ed25519.pub not found, SSH login will not work" >&2
fi

# Статические маршруты. Пример: ROUTES="10.30.0.0/24 via 10.10.0.4;default via 10.20.0.2"
if [ -n "${ROUTES:-}" ]; then
  echo "$ROUTES" | tr ';' '\n' | while read -r route; do
    if [ -n "$route" ]; then
      # shellcheck disable=SC2086
      ip route replace $route || echo "WARNING: route failed: $route" >&2
    fi
  done
fi

# Поддерживаем ARP-таблицу «живой»: периодически пингуем соседей по сегментам
if [ -n "${PEERS:-}" ]; then
  (
    while true; do
      for peer in $PEERS; do
        ping -c1 -W1 "$peer" >/dev/null 2>&1 || true
      done
      sleep 15
    done
  ) &
fi

exec /usr/sbin/sshd -D -e
