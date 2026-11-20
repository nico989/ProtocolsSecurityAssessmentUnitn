FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    snmp \
    snmp-mibs-downloader \
    tcpdump \
    dsniff \
    iputils-ping \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN echo "mibs +ALL" >> /etc/snmp/snmp.conf

EXPOSE 161/udp
EXPOSE 162/udp

CMD ["sleep", "infinity"]
