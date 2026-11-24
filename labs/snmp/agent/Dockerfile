FROM alpine:3.19

RUN apk add --no-cache build-base wget tar perl openssl-dev openssl linux-headers

RUN wget -q https://github.com/net-snmp/net-snmp/archive/refs/tags/v5.9.4.tar.gz -O /tmp/net-snmp.tar.gz \
     && tar -xzf /tmp/net-snmp.tar.gz -C /tmp \
     && cd /tmp/net-snmp-5.9.4 \
     && sed -i 's/#define ENABLE_EXTEND_WRITE_ACCESS 0/#define ENABLE_EXTEND_WRITE_ACCESS 1/' agent/mibgroup/agent/extend.c \
     && grep -n "define ENABLE_EXTEND_WRITE_ACCESS" agent/mibgroup/agent/extend.c \
     && ./configure --build=aarch64-alpine-linux-musl --prefix=/usr/local --with-defaults --disable-embedded-perl --without-perl-modules \
          ac_cv_type_fd_mask="unsigned long" \
     && sed -i 's/#define NETSNMP_FD_MASK_TYPE unknown/#define NETSNMP_FD_MASK_TYPE unsigned long/' include/net-snmp/net-snmp-config.h \
     && make -j"$(nproc)" \
     && make install \
     && cd / && rm -rf /tmp/net-snmp*

COPY snmpd.conf /usr/local/etc/snmp/snmpd.conf

# Add a sample user for the shadow file dump demo
RUN adduser -D admin && echo "admin:admin" | chpasswd

EXPOSE 161/udp

CMD ["/usr/local/sbin/snmpd", "-f", "-Lo", "-C", "-c", "/usr/local/etc/snmp/snmpd.conf"]
