# Codepy Architectural Design Review Report

This report captures the critical review and resolutions implemented for the Codepy framework's design.

## 1. Security Mitigations

### Pickle vs. JSON Serialization in Queues
* **Risk:** The framework design originally stored base64-encoded python `pickle` dumps of `Job` classes in the database `jobs` table and Redis queues. If a malicious database insertion occurred, deserialization would lead to Remote Code Execution (RCE).
* **Resolution:** Replaced `pickle.dumps()` and `pickle.loads()` with safe JSON serialization.
  * Payloads are stored as JSON strings containing the job module/class path (`job_class`) and its state dictionary (`data`).
  * Deserialization reconstructs the class dynamically and updates the state safely via `__dict__.update()`.

---

## 2. Request Isolation in Multi-Threaded Environments

### Service Container
* **Risk:** In PHP, the container is destroyed after each request. In a persistent Python process (Uvicorn), request-scoped services would leak between concurrent requests if stored in a shared dictionary.
* **Resolution:** Implemented `contextvars` to isolate the `_scoped_instances` dictionary per async task context. This guarantees request isolation.

### Facade Class Caching
* **Risk:** Facades cached resolved services in a global class-level dictionary (`_resolved`). If a scoped service (like `Request` or `Auth`) was resolved, the very first request's state would be cached and served to all subsequent requests.
* **Resolution:** Bypassed class-level caching in the base `Facade` class for all keys marked as request-scoped in the Service Container.

---

## 3. Template Engine Resolution

### Namespace and Path Resolution
* **Problem 1:** Forge did not register the default view path (`resources/views`) back to the internal `_namespaces[""]` dictionary, causing `TemplateNotFound` errors.
* **Problem 2:** Forge did not support dot-notation template strings (e.g. `layouts.app`), failing to convert dots to directory separators.
* **Problem 3:** Forge `@yield` preprocessor regex did not support default values (e.g. `@yield("title", "Codepy Blog")`).
* **Resolution:**
  * Configured `_setup_env()` to populate `self._namespaces[""]`.
  * Added dot-to-slash conversion (`template.replace(".", "/")`) inside `_resolve_template()`.
  * Expanded regex matching for `@yield` with default arguments in `DirectivePreprocessor.DIRECTIVES`.
