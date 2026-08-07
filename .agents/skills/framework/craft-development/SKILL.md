---
name: craft-framework-development
description: Framework-level guidelines and developer conventions for generating, refactoring, and maintaining the core components of the Craft framework.
---

# Craft Framework Development Guidelines (Framework Skill)

This skill governs modifications to the core framework packages under the `craft/` directory.

## Core Objective
Ensure that core libraries (container, ORM, router, queues, view engine, validation) remain abstract, high-performance, and free of application-specific business logic.

---

## 1. Subsystem Responsibilities

* **`craft.container`**: Manages class binding and dependency resolution. Scoped services must use `contextvars` to ensure thread-safety.
* **`craft.orm`**: Implements Active Record on a **custom query builder** over `sqlite3`/`psycopg2`/`PyMySQL` — no SQLAlchemy, no Pydantic. (`CRAFT_DESIGN.md` describes a SQLAlchemy/asyncpg/Pydantic target vision; it is explicitly marked aspirational, not the current implementation — verify against `services/orm/` before trusting either doc.)
* **`craft.queue`**: Dispatches and runs queued tasks. Payloads must be strictly serialized as **JSON**; never use `pickle`.
* **`craft.view`**: Preprocesses Forge directive syntax into standard Jinja2 syntax and caches compiled templates.

---

## 2. Framework Guidelines

* All code must be in English.
* Enforce strict type hints and docstrings on every public function and class.
* Do not import modules from the `app/` folder into the `craft/` framework package (avoid circular dependencies).
* New files under `services/` (and edits to existing ones) carry the `Category/Relations/References` header docstring — see `services/plugins/manager.py` for the shape.

---

## 3. Every change to the framework gets a CHANGELOG entry

**Non-negotiable, not just at release time.** The same change that fixes a
bug, adds a feature, bumps a dependency, or closes a vulnerability adds its
line to `## [Unreleased]` in `data/CHANGELOG.md`, in the same commit. This is
the mechanism that lets a developer or another agent understand what
happened to the framework without re-deriving it from a diff or `git log` —
and it is how they can help: a change nobody can see in the changelog is a
change nobody can review, build on, or flag a regression against.

Categories (Keep a Changelog): **Added**, **Changed**, **Fixed**,
**Security** (any vulnerability closed or hardening applied — state the
exposure, not just the patch), **Deprecated**, **Removed**. Full policy,
including how a release gets cut and why the release counter (`rNNNNN`)
always increments by exactly 1, is in `data/CONTRIBUTING.md` under
"Versioning and releases" — read it before your first change, not after.
