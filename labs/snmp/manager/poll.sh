#!/bin/bash

echo "[manager] Starting NMS polling loop -> snmp-agent every 5s"
while true; do
    snmpget -v 2c -c public snmp-agent \
        1.3.6.1.2.1.1.1.0 \
        1.3.6.1.2.1.1.3.0 \
        1.3.6.1.2.1.1.5.0 > /dev/null 2>&1
    sleep 5
done
