# Protocols Security Assessment

Repository for the UniTn guest lecture on network protocol security assessment. The presentation covers threat modelling for application-layer protocols, common vulnerability classes, and live exploitation demos. Each lab is fully self-contained with Docker and can be run locally.

---

## Presentation

`ProtocolsSecurityAssessmentUnitn.pptx` is the slide deck used during the lecture.

Topics covered:
- Introduction to information security and security assessment methodology for network protocols.
- HTTP request smuggling (CL.TE): how frontend/backend disagreements on body framing can be exploited to bypass WAFs and hijack victim requests.
- SNMP: community strings, information disclosure, write-permission abuse, and RCE via NET-SNMP-EXTEND-MIB.

---

## Repository structure

```
.
├── ProtocolsSecurityAssessmentUnitn.pptx
└── labs/
    ├── snmp/                   # SNMP vulnerability lab
    │   ├── docker-compose.yml
    │   ├── agent/              # Net-SNMP snmpd (vulnerable config)
    │   ├── manager/            # Legitimate NMS, polls every 5 s
    │   ├── attacker/           # snmpPoC + tcpdump + arpspoof
    │   ├── snmpPoC/            # Bash PoC scripts and community wordlist
    │   └── README.md
    └── http-smuggling/         # HTTP CL.TE smuggling lab
        ├── docker-compose.yml
        ├── attack.py           # CL.TE attack script (run from host)
        ├── frontend/           # Pound 4.11.90 (pre-fix, vulnerable)
        ├── backend/            # Gunicorn 19.9.0 + Flask
        └── README.md
```

---

## Labs

### SNMP (`labs/snmp/`)

Three-container lab (agent, manager, attacker) demonstrating the most common SNMPv1/v2c weaknesses:

- Community string brute-force with a realistic wordlist
- Unauthenticated MIB walk leaking OS info, processes, users, and open ports
- Write-permission abuse via the `private` community string (config tampering)
- RCE detection and exploitation through NET-SNMP-EXTEND-MIB

The attacker container runs [snmpPoC](https://github.com/nico989/snmpPoC) against the agent. A passive sniffing section shows how to intercept manager-agent UDP traffic on a Docker bridge with ARP spoofing.

See [`labs/snmp/README.md`](labs/snmp/README.md) for setup and exercise walkthroughs.

### HTTP Request Smuggling (`labs/http-smuggling/`)

CL.TE smuggling lab exploiting a real, dated vulnerability in Pound 4.11.90 (pre-fix commit `d9a983fe`) paired with Gunicorn 19.9.0:

- Pound parses `Transfer-Encoding: chunked ` as unknown and falls back to Content-Length, forwarding both headers to the backend.
- Gunicorn accepts `chunked ` as chunked encoding (substring match), consumes only the chunked body, and leaves the smuggled prefix in the TCP buffer.
- The attack smuggles a `GET /admin` prefix past Pound's WAF rule which blocks direct requests to `/admin`. Pound never sees `/admin` in what it forwards, but Gunicorn reassembles the smuggled request and serves the admin endpoint.

See [`labs/http-smuggling/README.md`](labs/http-smuggling/README.md) for a full walkthrough including the fix applied in Pound.

---

## Requirements

- Docker Desktop (or Docker Engine + Compose plugin)
- Python 3 for `attack.py` in the HTTP smuggling lab
- macOS or Linux host recommended
