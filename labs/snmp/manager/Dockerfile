FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    snmp \
    snmp-mibs-downloader \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN echo "mibs +ALL" >> /etc/snmp/snmp.conf

COPY poll.sh /poll.sh
RUN chmod +x /poll.sh

EXPOSE 161/udp
EXPOSE 162/udp

CMD ["/poll.sh"]
