# Strategic Guidelines: Scaling, Performance, and Security

This document outlines the core architecture and strategic guidelines for **Craft** to guarantee high scalability, maintainability, peak performance, and enterprise-grade security.

---

## 1. Horizontal & Vertical Scaling (Escalabilidade)

```
                    ┌────────────────────────┐
                    │     Load Balancer      │
                    └───────────┬────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Craft Node 1  │  │   Craft Node 2  │  │   Craft Node 3  │
│    (Stateless)   │  │    (Stateless)   │  │    (Stateless)   │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────┬───┴─────────────────────┘
                           ▼
                 ┌──────────────────┐
                 │  Shared Services │
                 │  Redis (Session) │
                 │  Postgres (Repl) │
                 └──────────────────┘
```

### Stateless Execution
* **Rule:** All Craft nodes must be completely stateless. Session data, cached variables, and file uploads must live in centralized stores (Redis, AWS S3, or PostgreSQL).
* **Benefit:** Allows spinning up hundreds of backend containers behind an Nginx/Traefik load balancer instantly.

### Query Splitting (Read/Write Replicas)
* **Goal:** Route database reads to read-replicas while sending all inserts, updates, and deletes to the primary database.
* **Implementation:** Configure the dynamic ActiveRecord connection resolver to switch connection pools automatically based on whether the active query builder statement is a read query (`SELECT`) or write query (`INSERT/UPDATE/DELETE`).

---

## 2. Maintainability & Code Consistency (Manutenibilidade)

### Clean Dependency Injection
* **Rule:** Bind all service interfaces to concrete implementations in the `Container` using service providers.
* **Benefit:** Changing system adapters (e.g. switching mail provider from SMTP to Mailgun or database queues to Celery/RabbitMQ) only requires updating a single binding in the container, keeping business controllers untouched.

### Convention Over Configuration (AI Scaffolding)
* **Rule:** Always generate code structures via the CLI (`dev.py`).
* **Benefit:** Prevents "architectural style drift". Whether a human or an AI agent writes a model or controller, the code looks exactly the same, reducing technical debt and context parsing overhead.

---

## 3. High Performance (Alta Performance)

### Non-Blocking Asyncio I/O
* **Rule:** All database, Redis, mail, and external API integrations must run asynchronously.
* **Benefit:** Python's `asyncio` event loop can process thousands of concurrent connections on a single CPU core without waiting for blocking thread pools.

### Prevent N+1 Query Traps
* **Rule:** The ActiveRecord ORM must prioritize Eager Loading. Developers and AI agents must be trained to use `.with_('relationship')` when querying records.
* **Benefit:** Consolidates multiple queries into a single database join query, reducing latency.

---

## 4. Industrial-Grade Security (Segurança)

### Sanitized Database Identifiers
* **Rule:** The Validator must never trust raw request input for database identifiers (tables and columns).
* **Implementation:** Standardize the regex format check (`^[a-zA-Z0-9_]+$`) for dynamic checks, completely eliminating SQL injection vectors.

### JSON-only Queue Serialization
* **Rule:** Never use Python's native `pickle` library for queues or cache serialization.
* **Benefit:** Prevents Remote Code Execution (RCE) vulnerabilities. All payloads are signed and serialized using standard JSON strings.

### Dynamic, Centralized RBAC
* **Rule:** Check user permissions at the middleware layer using database-driven role mappings.
* **Benefit:** Avoids hardcoding permission checks inside controllers. Permissions can be revoked or granted dynamically at runtime.
