# Database Safety & Absolute Data Persistence

Craft Engine enforces a strict **Absolute Data Persistence** policy across all environments (development, test, demo, staging, and production). Under no circumstances should database state be wiped, dropped, truncated, or reset.

---

## 1. Core Principles

1. **Absolute Data Persistence**: Every database write and state change represents permanent reference or operational data.
2. **Forward-Only Evolution**: Schema alterations are exclusively incremental. Reversals or structural changes are made via additive forward migrations.
3. **Soft-Deletes by Default**: Physical row removal (`DELETE FROM`, `TRUNCATE`) is replaced by record state mutations (e.g. updating timestamp `deleted_at = now()` or boolean flag `is_active = False`).
4. **Permanent Demo & Seed Records**: Demo tenant data and reference seeds are non-disposable and must never be purged during test cycles.

---

## 2. Banned Commands & Unsafe Operations

In automated agent tasks, deployment pipelines, and operational workflows, the following commands and operations are **strictly prohibited**:

| Prohibited Command / Pattern | Risk | Safe Alternative |
|---|---|---|
| `python dev.py migrate:reset` | Destroys all tables and schemas | Incremental forward migration (`python dev.py migrate`) |
| `python dev.py migrate:refresh` | Drops and rebuilds all tables | Forward migration with non-destructive alterations |
| `python dev.py migrate:fresh` | Drops all tables unconditionally | Forward migration (`python dev.py migrate`) |
| `python dev.py db:wipe` | Purges every database table | Additive schema migrations |
| `python dev.py db:drop` | Drops target database/tables | Targeted non-destructive alter migrations |
| `python dev.py db:seed --fresh` | Purges tables prior to seeding | Non-destructive, idempotent upsert seeding |
| `docker compose down -v` / `docker volume rm` | Destroys persistent storage volumes | Normal container restart (`docker compose restart` or `down` without `-v`) |
| `DELETE FROM <table>` / `TRUNCATE` | Irreversible data loss | Soft-delete `UPDATE <table> SET deleted_at = ...` |

---

## 3. Forward-Only Migrations

All schema modifications must be executed incrementally using:

```bash
# Apply pending migrations forward
python dev.py migrate
```

### Best Practices for Forward-Only Changes
* **Adding Columns**: Use nullable columns or default values (`t.string("bio").nullable()`).
* **Renaming/Deprecating Columns**: Add the new column, synchronize data via an idempotent migration script, and soft-deprecate the old column without dropping it.
* **Adding Indexes**: Add indexes concurrently or incrementally (`t.index(["user_id", "status"])`).

---

## 4. Soft-Delete Query Patterns

Instead of physical deletion, application logic and ORM queries should mutate lifecycle flags:

### Marking Records as Soft-Deleted

```python
from datetime import datetime, timezone
from app.Models.User import User

# Soft delete using timestamp
User.query().where("id", user_id).update({
    "deleted_at": datetime.now(timezone.utc),
    "is_active": False
})
```

### Querying Active Records

```python
# Filter out soft-deleted records
active_users = User.query().where_null("deleted_at").where("is_active", True).get()
```

---

## 5. Automated AI & Agent Guardrails

Craft Engine includes native AI guardrails and agent definitions to enforce data protection:
* **Workspace Rule (`GEMINI.md` / `.agents/rules/database_safety.md`)**: Automatically loaded into LLM / AI developer sessions to abort destructive CLI suggestions.
* **Skill (`craft-database-safety`)**: Guidelines and checklists for safe schema modifications and non-destructive seeding.
* **Craft Data Guardian Agent (`.agents/agents/craft-data-guardian.md`)**: Dedicated AI auditor that intercepts destructive execution requests and proposes safe, additive alternatives.
