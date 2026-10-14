FROM debian:stable-slim

# Узел лабораторной сети: SSH-сервер и утилиты, которые использует сканер (ip, arp, ping)
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server net-tools iproute2 iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd /root/.ssh \
    && printf 'PermitRootLogin prohibit-password\nPasswordAuthentication no\n' > /etc/ssh/sshd_config.d/lab.conf

COPY node-entrypoint.sh /usr/local/bin/node-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/node-entrypoint.sh && chmod +x /usr/local/bin/node-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/node-entrypoint.sh"]
