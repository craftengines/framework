# Codepy: The AI-Native Framework of the Future

**Codepy** is a Python backend framework built on Starlette, designed to be **AI-Native** rather than just AI-friendly. It pairs clean conventions, a complete CLI and an Active Record ORM with the performance, async model and type safety of modern Python.

Our ultimate mission is to enable developers (and AI agents) to build everything from a simple blog to a large-scale, high-availability enterprise system with zero friction.

---

## 1. Architectural Architecture Pillars

```
                     ┌────────────────────────────────┐
                     │         AI Agents / Dev        │
                     └───────────────┬────────────────┘
                                     │ (Scaffolding / Prompting)
                                     ▼
                     ┌────────────────────────────────┐
                     │       .ai/ Orchestrator        │
                     └───────────────┬────────────────┘
                                     │ (Reads blueprints & skills)
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                             Codepy Framework                               │
├───────────────────────┬──────────────────────────┬─────────────────────────┤
│    Immutable Core     │  Dynamic Modules (Hot)   │  Dynamic Plugins (Hot)  │
│  Container, ORM,      │  Auth, Users, CRM, ERP,  │  SMTP, S3, Payments,    │
│  Router, Queues, View │  Inventory (Start/Stop)  │  Cache, Notifications   │
└───────────────────────┴──────────────────────────┴─────────────────────────┘
```

### A. Immutable Core
The framework engine is strictly isolated. Application developers and AI agents do not modify the core files, protecting the framework from breaking changes.

### B. Isolated, Hot-Swappable Modules & Plugins
Business modules (e.g., Auth, Users, Billing) and plugins (e.g., S3, Payment gateways) are decoupled packages. They support dynamic **start/stop** behavior toggled via database states at runtime, preventing system crashes.

### C. Database-Driven & Zero Hardcoding
All localized translations, business rules, RBAC permissions, and active configurations are loaded dynamically from the database. A change in requirements does not require redeploying code—it only requires updating a database row.

---

## 2. Technical Evolution Roadmap

### Phase 1: Foundation Stability (Completed)
* Request-scoped DI container (`contextvars`).
* Class-level Facade caching isolation.
* Secure JSON queue serialization (replacing pickle).
* Forge template engine with dot-notation and default values.
* Custom CLI tool (`craft.py`).

### Phase 2: AI-Native Capabilities (Completed)
* `.ai/` directory structured for AI memory: `agents/`, `plan/`, `skills/`, `docs/`, `scripts/`.
* Dynamic bilinguality (`__` helper querying database translations).
* Start/Stop module routing based on database-driven flags.
* Sanitized database validator against SQL Injection.

### Phase 3: Scale & Enterprise Integrations (Planned)
* **ActiveRecord Multi-Tenancy:** Automated connection and schema routing based on request subdomains or headers.
* **Microservices Engine:** Native integration with gRPC, RabbitMQ, and Apache Kafka for event-driven decoupled systems.
* **Frontend Scaffold Bridge:** CLI commands in `craft.py` to automatically generate Next.js/React dashboard pages mapping to the backend modules.
* **OpenTelemetry Observability:** Fully integrated trace, metric, and log collection for enterprise Kubernetes deployments.
