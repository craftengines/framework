---
name: craft-database-safety
description: Enforces absolute data persistence and zero data loss for Craft Engine across all environments. Use whenever planning, reviewing, or executing database operations, migrations, seeds, or ORM/SQL updates.
---

# Craft Engine Database Safety & Absolute Data Persistence (Framework Skill)

This skill dictates the database persistence and safety protocols for all Craft Engine components, CLI tools, and application logic.

## Core Principle: Absolute Data Persistence
Never wipe, drop, truncate, or reset database state under any circumstances, across any environment (development, test, demo, staging, or production).

---

## 1. Strictly Banned CLI Commands

The following commands are strictly forbidden in any script, recommendation, or terminal execution:
* `python dev.py migrate:reset`
* `python dev.py migrate:refresh`
* `python dev.py migrate:fresh`
* `python dev.py db:wipe`
* `python dev.py db:drop`
* `python dev.py db:seed --fresh` (or any flag wiping existing tables before seeding)
* `docker compose down -v` / `docker volume rm` (or any destructive container command affecting database volumes)

---

## 2. Forward-Only Database Evolution

* **Incremental Migrations Only**: All schema alterations (adding tables, adding columns, modifying indexes) must be expressed as forward-only migrations executed via `python dev.py migrate`.
* **Non-Destructive Refactoring**: Never remove columns or drop tables in active databases. Deprecate columns gracefully or rename/flag them without dropping history.
* **Demo Tenant Persistence**: The Demo tenant is permanent reference and seed data. Never treat Demo environments as disposable or clearable for testing.

---

## 3. Query & ORM Safety: Mandatory Soft-Deletes

* **Physical Deletes Prohibited**: Do NOT execute raw SQL `DELETE FROM` or `TRUNCATE TABLE`.
* **Soft-Delete Implementation**:
  * Deletions must be represented by setting `deleted_at = now()` (timestamp) or updating boolean status flags (e.g., `is_active = False`).
  * Queries must filter active records (`where_null("deleted_at")` or `where("is_active", True)`).

---

## 4. Abort & Remediation Protocol

When a task, test, or user request requests or implies table drops, data truncation, or database resets:
1. **Immediately Halt**: Do not execute the destructive step.
2. **Explain & Guide**: Inform the user about the Absolute Data Persistence policy.
3. **Propose Non-Destructive Solution**: Provide an additive migration or an incremental soft-delete / seed update strategy.
