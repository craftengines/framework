# Security Policy

## Supported versions

Codepy is at `0.x`. Only the latest release receives security fixes.

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

The project is developed locally and is not published. Email
**snarthost@gmail.com** with:

- a description of the issue and its impact
- steps to reproduce, or a proof of concept
- the affected version, database driver and Python version

You should get an acknowledgement within a few days. Once a fix is available it
will be released and credited to you, unless you prefer otherwise.

## What the framework guarantees

Understanding these boundaries helps you judge whether something is a
vulnerability or expected behaviour.

**Passwords** are hashed with bcrypt, falling back to PBKDF2-HMAC-SHA256 when
the bcrypt backend is unavailable. Plaintext is never stored, and an unknown
user costs the same time as a wrong password so timing does not reveal which
emails exist.

**Sessions** are signed with HMAC-SHA256 using `APP_KEY`. A tampered cookie, or
one signed with a different key, is rejected.

> Signed is not encrypted. With `SESSION_DRIVER=cookie` the payload is
> base64-encoded JSON: the client cannot change it, but can read it. Do not put
> secrets in the session under that driver — use `SESSION_DRIVER=file`, which
> keeps the payload server-side.

**CSRF** is verified on POST, PUT, PATCH and DELETE via the `_token` field or
the `X-CSRF-TOKEN` header. Routes matching `api/*` are exempt by default. Logging
in rotates the session id, which closes session fixation.

**Authorization** denies by default: an ability with no matching gate or policy
returns `False` rather than allowing the action.

**SQL** goes through parameter binding on every driver. String interpolation of
user input into a query is a bug — please report it.

**Debug output** is controlled by `APP_DEBUG`. Stack traces reach the client
only when it is on. Keep it off in production.

## Before deploying

- Run `python craft.py key:generate`. Without `APP_KEY`, session signing falls
  back to a per-process random key: sessions do not survive a restart and are
  not shared between workers.
- Set `APP_DEBUG=false`.
- Set `SESSION_SECURE_COOKIE=true` so the cookie is HTTPS-only.
- Serve `public/` as the web root. `storage/` and `.env` must never be reachable.

## Known gaps

These are documented rather than hidden. They are tracked in
`.agents/docs/backlog.md`.

- The cookie session driver signs but does not encrypt.
- There is no rate limiting on authentication endpoints.
- There is no password reset or email verification flow yet.
