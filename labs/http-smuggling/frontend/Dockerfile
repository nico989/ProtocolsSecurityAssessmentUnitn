FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    git autoconf automake libtool libssl-dev gcc make perl texinfo \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/graygnuorg/pound.git /build/pound \
 && cd /build/pound \
 && git checkout 8d86d52d0bc65534c33018b0a01996081d23b89e \
 && ./bootstrap \
 && ./configure \
 && make -j"$(nproc)" \
 && make install \
 && rm -rf /build

COPY pound.cfg /usr/local/etc/pound.cfg

CMD ["pound", "-e"]
