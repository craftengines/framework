---
name: craft-project-management
description: Project-specific instructions for running Docker containers, executing test suites, running migrations, and managing the development environment.
---

# Craft Project Scaffolding Guidelines (Project Skill)

This skill governs local execution, testing, and container management for this repository.

---

## 1. Commands and CLI Tools

Always use `dev.py` to trigger local operations. Since command signatures are hyphenated, refer to this reference:

| Action | Command |
|---|---|
| Generate App Key | `python dev.py key:generate` |
| Refresh Migrations | `python dev.py migrate fresh` |
| Run Test Suite | `pytest` or `python dev.py test` |
| Start Server | `python dev.py serve` |

---

## 2. Docker Environments

* **Compose Service:** `craft-app` (built using `Dockerfile` in the root).
* **Port Binding:** Mapped to host port **`8300`** to prevent collisions.
* **Environment Variables:** Set in `docker-compose.yml` (`DB_CONNECTION=sqlite`, `APP_ENV=local`).
* **Test Command:** `docker compose exec craft-app pytest` runs the automated validation suite in the container.
