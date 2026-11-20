FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    snmpd \
    snmp \
    && rm -rf /var/lib/apt/lists/*

RUN find /etc/snmp /usr/share/snmp /usr/lib/snmp -name "snmpd.conf" -delete 2>/dev/null || true

COPY snmpd.conf /etc/snmp/snmpd.conf

EXPOSE 161/udp
EXPOSE 162/udp

CMD ["snmpd", "-f", "-Lo", "-C", "-c", "/etc/snmp/snmpd.conf"]
