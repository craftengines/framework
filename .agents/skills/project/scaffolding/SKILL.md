---
name: codepy-project-management
description: Project-specific instructions for running Docker containers, executing test suites, running migrations, and managing the development environment.
---

# Codepy Project Scaffolding Guidelines (Project Skill)

This skill governs local execution, testing, and container management for this repository.

---

## 1. Commands and CLI Tools

Always use `craft.py` to trigger local operations. Since command signatures are hyphenated, refer to this reference:

| Action | Command |
|---|---|
| Generate App Key | `python craft.py key:generate` |
| Refresh Migrations | `python craft.py migrate fresh` |
| Run Test Suite | `pytest` or `python craft.py test` |
| Start Server | `python craft.py serve` |

---

## 2. Docker Environments

* **Compose Service:** `codepy-app` (built using `Dockerfile` in the root).
* **Port Binding:** Mapped to host port **`8300`** to prevent collisions.
* **Environment Variables:** Set in `docker-compose.yml` (`DB_CONNECTION=sqlite`, `APP_ENV=local`).
* **Test Command:** `docker compose exec codepy-app pytest` runs the automated validation suite in the container.
