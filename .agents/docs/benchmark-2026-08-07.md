# Craft Framework — Benchmark & Stress Report

**Date:** 2026-08-07 · **Version audited:** `v3.11.0-r00001` · **Method:** live load
test against the running container (`framework`, Python 3.11, Postgres 15) +
4 independent specialist audits (security, performance/scalability, CI/CD/DX,
UI/UX), each verifying claims directly against code — not documentation, not
memory. File:line references are preserved from the source audits so every
finding is independently checkable.

This is an audit only. No framework code was changed to produce this report.
Findings below should seed `.agents/docs/backlog.md`, not be treated as done.

---

## 1. Live stress test — the framework's real ceiling

stdlib-only concurrent load test (`ThreadPoolExecutor`, no external tool
required), run from inside the `framework` container against itself
(`http://127.0.0.1:8000`), sweeping concurrency 1 → 10 → 50 → 100 on three
representative routes.

| Route | Concurrency | RPS | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|---|
| `GET /` (rendered view) | 1 | 32.9 | 28ms | 38ms | 66ms | 0 |
| `GET /` | 10 | 32.3 | 292ms | 428ms | 447ms | 0 |
| `GET /` | 50 | 30.0 | 1677ms | 1841ms | 1847ms | 0 |
| `GET /` | 100 | 31.4 | 2996ms | 3430ms | 3444ms | 0 |
| `GET /api/v1/posts` (DB read) | 1 | 30.8 | 30ms | 48ms | 63ms | 0 |
| `GET /api/v1/posts` | 10 | 29.8 | 305ms | 452ms | 559ms | 0 |
| `GET /api/v1/posts` | 50 | 28.7 | 1785ms | 1928ms | 1969ms | 0 |
| `GET /api/v1/posts` | 100 | 30.4 | 3252ms | 3696ms | 3754ms | 0 |
| `GET /docs` (view + markdown render) | 1 | 6.5 | 146ms | 221ms | 324ms | 0 |
| `GET /docs` | 10 | 6.7 | 1400ms | 1998ms | 2131ms | 0 |
| `GET /docs` | 50 | 5.6 | 8679ms | 9643ms | 9791ms | 0 |
| `GET /docs` | 100 | 6.6 | 15012ms | 15017ms | 15020ms | **294/400 (74%)** |

**Reading it:** RPS is flat — statistically the same number at concurrency 1
and concurrency 100, on every route. That is the signature of a server that
processes exactly **one request at a time** regardless of how many arrive
concurrently: latency absorbs 100% of the added load instead of throughput
rising. `/docs` — the heaviest route (markdown render on every hit, no
caching) — breaks outright past 50 concurrent clients, with most requests
timing out at 15s under concurrency 100.

This single test independently confirms, with numbers, what the performance
audit derived from reading the code (§3 below): the app is fully serialized,
today, on a single core, with no connection pool and no worker process
model. It is not a future risk — it is the current, measured behavior of the
container everything else in this session was validated against.

---

## 2. Security — top findings

Full detail: security audit transcript (this session). Severities as rated
by the audit.

| # | Severity | Finding | Location |
|---|---|---|---|
| 13 | **Critical** | CRUD-builder-generated write routes (`store`/`update`/`destroy`) have **no authentication and no authorization** — `AuthenticateApiToken` never rejects a missing/invalid token, it just continues. Any unauthenticated client can create/mutate/delete any record of a generated entity; `update`/`destroy` have no ownership check either (IDOR by design). | `services/cli/crud_builder.py:146`, `services/http/middleware.py:327-351` |
| 1 | High | Mass-assignment protection is **opt-in, inverted from safe-by-default**: an undeclared/empty `fillable` means *zero* filtering, not full protection. | `services/orm/model.py:158,236` |
| 14 | Medium | Generated `FormRequest.authorize()` always returns `True` — the authorization hook exists but is a stubbed no-op. | `services/cli/generators.py:177-178,199-200` |
| 8 | Medium | **No security headers anywhere** — zero CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, no middleware for any of them. | grep across `services/http/middleware.py`, confirmed absent |
| 2 | Medium | CSRF blanket-exempts `api/*` — safe only if every `api/*` route uses token auth, not session cookies; nothing enforces or warns about that assumption. | `services/http/middleware.py:214` |
| 11 | Medium | No `APP_KEY` enforcement at boot — missing key silently falls back to a per-process ephemeral key instead of failing loudly, which will silently break sessions across restarts/workers in production. | `services/http/session.py:322-353` |
| 10 | Low | `docker-compose.prod.yml` still defaults `DB_PASSWORD` to the literal `secretpassword` if unset — a known, public password shipping in a **production** compose file. | `docker-compose.prod.yml:9` |
| — | Informational (verified correct, no action) | Session fixation protection, CSRF timing-safety + fail-closed behavior, password hashing chain, timing-safe login, SQL injection defenses (parameterized + identifier allowlist), rate limiting on `/login`/`/register` (already wired, contradicting a stale claim in `SECURITY.md`) all checked out solid — on par with or better than Laravel/Django defaults. | various, see full transcript |

**Correction found along the way:** `SECURITY.md`'s "Known gaps" section
still claims "no rate limiting on authentication endpoints" — false;
`ThrottleRequests` is implemented and wired to `/login`/`/register`. Doc is
stale and should be fixed so it doesn't cause double-counting in future
audits.

---

## 3. Performance & scalability — top findings

Full detail: performance audit transcript. This section explains *why* §1's
numbers look the way they do.

| # | Severity | Finding | Location |
|---|---|---|---|
| 1 | **Critical** | **Sync-over-async mismatch**: Starlette gives Craft an async-capable dispatch path, but sync controller/middleware code runs directly on the event loop with no `run_in_threadpool` offload. Any DB call blocks the *entire process* — not just the request, the whole event loop — for its full duration. This is the direct cause of §1's flat-RPS curve. | `services/http/kernel.py:178-259` |
| 2 | **Critical** | **No connection pool** — one shared `psycopg2` connection per process, cached for the process lifetime, registered as a container singleton (not per-request). Fine only because dispatch is already fully serialized (#1); adding concurrency without fixing this first will corrupt concurrent cursor use. | `services/orm/db.py`, `services/providers/service_providers.py:15` |
| 3 | Critical | **Single process, no multi-worker option** — `dev.py serve` and the Dockerfile's `CMD` both run one uvicorn process with no `--workers` flag exposed anywhere in the CLI. Combined with #1/#2: this container can serve **exactly one request at a time**, full stop. | `services/cli/app.py:451-461`, `Dockerfile:32` |
| — | Medium | Eager loading (`with_()`) is well-designed but entirely opt-in, with zero N+1 detection/warning tooling. | `services/orm/relationships.py` |
| — | Medium | `paginate()` has **no maximum `per_page` cap** — `?per_page=999999` is honored as-is. | `services/orm/query_builder.py:426-436` |
| — | Medium-High | **No HTTP-level response caching** anywhere — no `Cache-Control`, `ETag`, or conditional-GET support on dynamic routes. Every cacheable GET pays full origin cost. | confirmed absent across `services/http/` |
| — | Medium | Every request to a module-gated route does a **live, uncached DB query** (`SELECT enabled FROM modules...`) to check module state. | `services/http/kernel.py:192` |
| — | Medium | Schema migrator has no `CREATE INDEX CONCURRENTLY` / batched-backfill primitive — any index/backfill on a populated table blocks reads/writes for the duration. | `services/migrations/schema.py:390`, `services/migrations/migrator.py:183-191` |

**Top-5, ordered by requests-served-per-dollar-of-infra impact:** (1) offload
sync work off the event loop, (2) run multiple worker processes, (3) add a
real connection pool (must land *with* #1/#2, not before — adding
concurrency without a pool corrupts single-connection cursor state), (4) cap
`per_page`, (5) add HTTP cache headers.

---

## 4. CI/CD & developer experience — top findings

Full detail: DX/CI-CD audit transcript.

| # | Severity | Finding |
|---|---|---|
| Structural | **CI verifies less than `CONTRIBUTING.md` requires of a human.** `deploy.yml` tests only Python 3.11 against SQLite — no PostgreSQL, despite `CONTRIBUTING.md` mandating "all three targets" before merge. That verification today is 100% manual/human-or-agent-run. |
| High | **MySQL is a documented, shipped feature with zero test coverage anywhere** — not in CI, not in any local workflow. The query builder's MySQL grammar branch could be silently broken. |
| High | **No lint, type-check, or dependency-vulnerability scanning in CI** — no ruff, mypy, bandit, or pip-audit. Every competing framework's own contribution pipeline has at least lint. |
| Medium | **`Dockerfile.prod` still has stale "Codepy" branding** (`addgroup codepy`, `USER codepy`) that contradicts `documentation/deployment.md`'s claim of a `dev` user — sign this file wasn't touched during the framework's rename/cleanup pass that fixed the dev `Dockerfile`. |
| Medium | **Production entrypoint has no migration step** — `docker compose -f docker-compose.prod.yml up -d --build`, the exact command `deployment.md` advertises as the deploy flow, boots gunicorn against an unmigrated schema. The doc says to run `migrate` manually first; nothing enforces it. |
| Medium | `APP_KEY` missing degrades silently (same finding as security §2, #11) — contradicts the project's own stated philosophy ("never degrade silently") documented in `CONTRIBUTING.md`. |
| Low | `.agents/docs/dx_and_ai_learning_curve.md` is stale/inaccurate enough to mislead a fresh AI agent session — references a `.ai/` directory that doesn't exist (it's `.agents/`), and has an unfinished comparison table with orphaned placeholder rows. Should get the same "aspirational, not current" banner `CRAFT_DESIGN.md` already has. |
| Low | No coverage tooling (`pytest-cov`) — "627 tests passing" is currently unfalsifiable against actual surface area. |
| Positive, keep | Time-to-first-request is genuinely honest and short (4 real commands, SQLite needs no server). Unknown-middleware-alias failure is a well-designed loud boot-time error. "Every test file passes standalone" + real-migrator `conftest.py` are good, uncommon discipline. The `.agents/skills/` AI-onboarding investment is a real, verified differentiator versus Laravel/Django/Rails, none of which ship anything comparable. |

**Top-5:** (1) match CI to `CONTRIBUTING.md`'s own bar (add Postgres +
3.12/3.13 to the matrix), (2) either test MySQL for real or stop claiming
it, (3) fix `Dockerfile.prod` branding + add a migration step to its boot
sequence, (4) add `ruff` to CI, (5) add `pytest-cov` reporting.

---

## 5. UI/UX — top findings

Full detail: UI/UX audit transcript.

| # | Severity | Finding |
|---|---|---|
| **Critical** | A generated CRUD entity ships **zero admin UI** — only JSON endpoints. "CRUD builder" is, today, a JSON-API scaffold generator, not a CRUD *admin UI* builder like Django Admin/Filament/Nova, which give a full list+edit UI for free on model registration. 100% of admin surface area (list, detail, edit, filters, pagination UI) is unbuilt for anything generated. |
| Critical | **`/admin` doesn't render the admin dashboard that already exists.** `HomeController.admin()` returns a hardcoded `Response("<h1>Admin Dashboard</h1>")` instead of `self.view("admin.dashboard", ...)` — the polished, styled template sits in the repo, unused, as dead code. Anyone clicking Admin after login sees an unstyled placeholder, directly contradicting the polished marketing homepage's "batteries included" promise. |
| Critical | **The one hand-built demo CRUD flow (blog posts) breaks visibly on the first bad input.** `PostController.store()`/`.update()` call `form.validated()` with no fail-and-redisplay handling; a validation failure falls through to the generic exception handler, which renders a raw unstyled `<h1>{status}</h1><p>{message}</p>` fragment — no nav, no stylesheet, no way back, and all typed input is lost (`old()` exists in the view engine but nothing ever populates `_old_input`, so it's dead code). |
| High | CRUD-builder form: adding/removing field rows works, but there's **no reordering**, no client-side validation before submit, and — worse — **entered field rows are not restored on a server-side validation failure**, only the entity name is. Materially worse than Filament/Nova or even a plain Laravel `old()` form. |
| Medium | Two parallel, duplicated design-token systems (`craft-theme.css`/`craft-utilities.css` vs. a separately-declared token block in `public/css/app.css` used only by the homepage) — will confuse anyone theming the app consistently. |
| Positive, keep | Empty states are handled well and consistently across home/posts/dashboard views. The homepage itself is a genuinely polished, non-skeleton "day one" landing page. Labels/focus states are correct on hand-built forms (just not on CRUD-builder's dynamic rows). |

**Top-5:** (1) wire `/admin` to the existing dashboard template — trivial,
highest leverage, (2) fix the posts validation-error path + actually
populate `_old_input`, (3) give the CRUD builder a real list/edit template
generator, not just JSON, (4) preserve field rows + add labels on
CRUD-builder validation failure, (5) unify the two CSS token systems.

---

## 6. Market comparison (qualitative, capability-by-capability)

Craft is compared against what each framework does **by default / out of
the box**, not what's achievable with third-party packages, since Craft's
own pitch is "batteries-included."

| Capability | Craft (verified) | Laravel | Django | Rails | FastAPI |
|---|---|---|---|---|---|
| Async DB path | **None** — sync psycopg2 only | N/A (sync PHP) | N/A (sync, WSGI) | N/A (sync) | Yes, `asyncpg`/`databases` |
| Connection pooling | **None** — single shared connection | Persistent connections via PHP-FPM/Octane | Threaded WSGI + `CONN_MAX_AGE` | Threaded/process WSGI | `asyncpg.create_pool()` common |
| Multi-worker default | **None** — single process, `--workers` not exposed | PHP-FPM/Octane multi-worker | gunicorn/uwsgi multi-worker standard | Puma multi-worker standard | `uvicorn --workers N` standard |
| Admin UI from model | **None** (JSON API only) | Nova/Filament (paid/community) | **Built-in, free** | ActiveAdmin (community, near-universal) | None built-in |
| Security headers by default | **None** | None core, ubiquitous ecosystem package | **Built into default `settings.py`** | Common via `secure_headers` gem | None core |
| Mass-assignment default | Unsafe (empty `fillable` = unrestricted) | Similar footgun, but documented | Allowlist-by-construction (forms/serializers) | **Allowlist-by-default** (Strong Parameters) | N/A |
| CI matrix (DB × Python) | 1 Python × 1 DB (SQLite only) | Typically multi-DB | Canonical multi-DB/multi-Python | Multi-DB common | Varies |
| CSRF | Yes, timing-safe, fail-closed | Yes | Yes | Yes | Manual |
| Rate limiting on auth | Yes, wired | Yes | 3rd party | 3rd party | 3rd party |
| SQL injection defense | Parameterized + identifier allowlist | Parameterized | Parameterized | Parameterized | Depends on ORM |
| AI-agent onboarding artifacts | **Yes — real differentiator**, none of the others ship this | None | None | None | None |

**Bottom line:** Craft's *security primitives* (CSRF, session rotation,
password hashing, SQLi defense, rate limiting) are genuinely competitive —
on par with or better than Laravel/Django in several specific, verified
ways. Its *scalability model* (§3) and *admin/scaffolding UI* (§5) are not
currently competitive with any of the four benchmarks — those are the areas
where "batteries-included" doesn't yet hold up against what the market
expects for free. The AI-agent onboarding investment (`.agents/skills/`,
`Category/Relations/References` headers, mandatory CHANGELOG discipline) is
a real, verified point of differentiation none of the mainstream frameworks
offer at all.

---

## 7. Consolidated top-10 action list (across all dimensions)

Ranked by a mix of severity and how cheap the fix is relative to impact —
not by category, since a Critical UX fix that's one line beats a Medium
performance fix that's a redesign.

1. **[1 line, Critical]** Wire `/admin` to the existing `admin.dashboard` view instead of a hardcoded string. (§5)
2. **[Critical, security]** Require auth + ownership check on CRUD-builder-generated write routes; the current default is a public, unauthenticated read/write/delete API generator. (§2)
3. **[Critical, correctness]** Fix the demo blog's validation-error path and populate `_old_input` — the one hand-built CRUD flow currently breaks visibly on bad input. (§5)
4. **[Critical, architecture]** Offload sync controller/DB work from the event loop (thread pool) — the direct cause of the flat-RPS ceiling measured in §1.
5. **[Critical, architecture]** Expose `--workers` and default the container to multiple processes — cheapest, highest-leverage capacity fix available.
6. **[High, security]** Flip mass-assignment default to fail closed (empty `fillable` = nothing assignable).
7. **[High, process]** Bring CI up to `CONTRIBUTING.md`'s own bar — add PostgreSQL + the claimed Python versions to the matrix; either test MySQL for real or stop claiming it.
8. **[Medium, security]** Add a `SecurityHeaders` middleware to the default stack (CSP/X-Frame-Options/X-Content-Type-Options at minimum).
9. **[Medium, architecture]** Add a connection pool — *only after* #4/#5 land, never before (a shared single connection under new concurrency will corrupt cursor state).
10. **[Medium, UX]** Give the CRUD builder a minimal generic list/edit Forge template, closing the biggest strategic gap versus Django Admin/Filament.

Everything else surfaced in §2–§5 (26 findings total across the four audits,
not all listed above) should be triaged into `.agents/docs/backlog.md` as
its own set of fatias — this report is the seed, not the backlog itself.
