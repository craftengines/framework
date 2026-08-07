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
* **`craft.orm`**: Implements Active Record query building wrapping SQLAlchemy 2.0 Core. Must support both sync (CLI) and async (HTTP) execution engines.
* **`craft.queue`**: Dispatches and runs queued tasks. Payloads must be strictly serialized as **JSON**; never use `pickle`.
* **`craft.view`**: Preprocesses Forge directive syntax into standard Jinja2 syntax and caches compiled templates.

---

## 2. Framework Guidelines

* All code must be in English.
* Enforce strict type hints and docstrings on every public function and class.
* Do not import modules from the `app/` folder into the `craft/` framework package (avoid circular dependencies).
