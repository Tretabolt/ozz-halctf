FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    samba \
    smbclient \
    net-tools \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 139 445

ENTRYPOINT ["/entrypoint.sh"]
