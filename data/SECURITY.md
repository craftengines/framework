# Security Policy

## Supported versions

Only the latest release receives security fixes.

| Version | Supported |
|---------|-----------|
| 3.17.x  | Yes       |

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
> keeps the payload server-side and destroys the old file when the session id
> is regenerated or invalidated.

**CSRF** is verified on POST, PUT, PATCH and DELETE via the `_token` field in
the parsed body or the `X-CSRF-TOKEN` header. A token in the query string is
ignored — a crafted cross-site link could plant one. Routes matching `api/*`
are exempt by default. Logging in rotates the session id, which closes session
fixation.

**Authorization** denies by default: an ability with no matching gate or policy
returns `False` rather than allowing the action.

**SQL** goes through parameter binding on every driver, and the query builder
validates identifiers and whitelists operators. String interpolation of user
input into a query is a bug — please report it.

**Mass assignment** is blocked by default and fails closed: `Model.create()`
and `update_attributes()` drop any attribute outside `fillable`, and an
empty/undeclared `fillable` means *nothing* is mass-assignable. A model
opts into unrestricted mass assignment explicitly with `guarded = False`.
`force_create()` is the explicit bypass for trusted, internal input.

**Debug output** is controlled by `APP_DEBUG`, which defaults to off. Stack
traces reach the client only when it is on, and the exception page HTML-escapes
everything it prints. Keep it off in production.

## Before deploying

- Run `python dev.py key:generate`. With `APP_ENV=production`, an empty
  `APP_KEY` now fails loudly at boot instead of degrading silently. Outside
  production, session signing falls back to a per-process random key:
  sessions do not survive a restart and are not shared between workers.
- Leave `APP_DEBUG` unset or `false` — it defaults to off; `.env.example`
  enables it for local development only.
- Set `SESSION_SECURE_COOKIE=true` so the cookie is HTTPS-only.
- Serve `public/` as the web root. `storage/` and `.env` must never be reachable.

## Known gaps

These are documented rather than hidden. They are tracked in
`.agents/docs/backlog.md` (workspace root, outside this repository).

- The cookie session driver signs but does not encrypt.
- There is no password reset or email verification flow yet.
