# Security Policy — Craft Engine

## Supported versions

Only the latest release receives security fixes.

| Version | Supported |
|---------|-----------|
| 3.17.x  | Yes       |

## Reporting a vulnerability

Email **snarthost@gmail.com** with:

- A description of the issue and its security impact
- Steps to reproduce, or a proof of concept
- The affected version, database driver, and Python version

You should receive an acknowledgement within a few business days. Once a fix is available it will be released and credited to you.

## Security Guarantees

Understanding these boundaries helps assess whether a behavior is an intended protection or an issue:

- **Passwords**: Hashed with bcrypt (with PBKDF2-HMAC-SHA256 fallback if bcrypt is unavailable). Plaintext is never stored, and timing attacks are mitigated.
- **Sessions**: Signed with HMAC-SHA256 using `APP_KEY`. Cookie tampering is prevented. `SESSION_DRIVER=file` or `redis` is recommended for high-sensitivity session data.
- **CSRF Protection**: Automatically verified on mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) via `_token` or `X-CSRF-TOKEN`.
- **Authorization**: Denies by default (RBAC + ABAC Gate & Policies).
- **SQL Injection Prevention**: Parameterized queries across all database drivers (SQLite, PostgreSQL, MySQL).
- **Mass Assignment Protection**: Guarded attributes and strict `fillable` enforcement.
- **WAF & Rate Limiting**: Built-in IDS/firewall, Honeypots, and request throttling.

## Deployment Checklist

- Generate a strong key: `python dev.py key:generate`.
- Ensure `APP_DEBUG=false` in production.
- Enable `SESSION_SECURE_COOKIE=true` for HTTPS.
- Serve only `public/` directory as the document root; never expose root `.env` or `storage/`.
