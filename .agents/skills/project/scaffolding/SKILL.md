---
name: craft-project-management
description: Project-specific instructions for running Docker containers, executing test suites, running migrations, and managing the development environment.
---

# Craft Project Scaffolding Guidelines (Project Skill)

This skill governs local execution, testing, and container management for this
repository. All commands below run **from inside `data/`** — that directory is
the deployable unit and the Compose project root; see
`craft-workspace-architecture` for why. `pytest` alone has no `test` subcommand
on `dev.py`; use the bare command.

---

## 1. Commands and CLI Tools

Always use `dev.py` to trigger local operations. Both `command:sub` and
`command sub` spellings work (e.g. `migrate:status` == `migrate status`).

| Action | Command |
|---|---|
| Generate App Key | `python dev.py key:generate` |
| Run Migrations | `python dev.py migrate` |
| Reset + Reseed | `python dev.py migrate fresh --seed` |
| Run Test Suite | `python -m pytest` |
| Start Server | `python dev.py serve` |
| Route List | `python dev.py route list` |
| Generate Model + Migration | `python dev.py make model <Name> -m` |

---

## 2. Docker Environment

* **Compose services:** `app` (container name `framework`, built from
  `data/Dockerfile`) and `db` (container name `framework-db`, `postgres:15-alpine`).
* **Compose project name:** pinned to `name: framework` in `docker-compose.yml`
  — the workspace directory has a space in it, which Compose cannot derive a
  project name from.
* **Port binding:** app on host **`8300`** → container `8000`; Postgres on
  host **`5499`** (both host and container side, non-default, to avoid
  colliding with other local Postgres instances).
* **Environment variables:** set in `docker-compose.yml` — `DB_CONNECTION=pgsql`,
  `APP_ENV=local`, `APP_DEBUG=true`. The default *outside* Docker (via
  `.env.example`) is SQLite; Docker Compose always brings up Postgres.
* **Bind mount:** `.:/app`, relative to `data/` — editing any file under
  `data/` is live in the running container immediately, no rebuild needed.
* **Test command:** `docker exec framework python -m pytest` runs the suite
  on the container's Python (currently the framework's minimum supported
  version), independent of whatever interpreter is on the host.
