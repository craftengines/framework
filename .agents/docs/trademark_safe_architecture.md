# Trademark-Safe Architectural Renaming & Portability Strategy

To protect the **Codepy** framework from future legal or trademark issues, we must replace proprietary names associated with Laravel (e.g., *Laravel, Artisan, Eloquent, Blade, Telescope, Horizon, Forge*) with generic or Pythonic alternatives. 

At the same time, we must maintain the exact structure, design patterns, and ergonomics to ensure developers can seamlessly port legacy projects from Laravel, Symfony, and CodeIgniter to Python.

---

## 1. Trademark-Safe Naming Map

| Laravel Concept (Proprietary) | Codepy Safe Term | Concept Vibe & Legality |
|---|---|---|
| **Laravel** (The Framework) | **Codepy** | Brand-safe, combines "Code" and "Python". |
| **artisan.py** (The CLI Tool) | **craft.py** / `python craft.py` | Evokes "craftsmanship" (similar to artisan) but is generic. |
| **Eloquent** (Active Record ORM) | **Fluent** / **ActiveRecord** | "Fluent" describes the chainable query builder; "ActiveRecord" is a standard design pattern. |
| **Blade** (Template Preprocessor) | **Razor** / **Edge** | "Razor" (from ASP.NET) or "Edge" (from AdonisJS) are generic template names. |
| **Forge** (Template Preprocessor Core) | **Loom** | Refers to weaving templates together, completely generic. |
| **Telescope** (Dev Debugger) | **Spyglass** / **Observer** | Safe, nautical terms for looking closely. |
| **Horizon** (Redis Queue Dashboard) | **Vista** / **Panorama** | Synonyms of horizon, legally safe. |

---

## 2. Code-Level Implementation Plan

### A. Renaming the CLI Entrypoint (`artisan.py` -> `craft.py`)
Rename the command-line file to `craft.py`.
```python
# Rename artisan.py to craft.py
# Execution: python craft.py serve, python craft.py migrate-fresh
```

### B. Renaming the ORM (`Codepyquent` -> `ActiveRecord` or `Fluent`)
Inside the codebase, rename packages to refer to the **Fluent** API or standard **ActiveRecord** terminology.
```python
# Instead of codepy.orm (using Eloquent terms inside docstrings)
# Use: codepy.database.activerecord
from codepy.database.activerecord import Model
```

### C. Renaming Template Preprocessing (`Forge` & `Blade` -> `Loom` & `Razor`)
Instead of calling the compiler "Forge" and files `.blade.py`, use:
* Files ending in `.razor.py` or `.edge.py`
* The engine class named `Loom` (representing compilation and template stitching).

---

## 3. Portability & Migration Compatibility Layer

To facilitate porting legacy PHP projects, we will introduce a **Compatibility Bridge**. This bridge will map common PHP patterns to their Pythonic equivalents:

### A. Routing Compatibility Mapping
Legacy PHP frameworks use uppercase HTTP methods or string-based namespaces. Codepy's router can support a translation utility to map legacy routes automatically:
```python
# Compatibility helper inside routes/web.py
def legacy_route(method: str, path: str, action: str):
    # Translates "UserController@index" to [UserController, "index"]
    controller_name, method_name = action.split("@")
    Route.add(method.upper(), path, [controller_name, method_name])
```

### B. ORM Attribute Compatibility Mapping
Laravel models use camelCase attributes dynamically (`$user->firstName`). Python models use snake_case (`user.first_name`). 
We can implement a dynamic attribute getter in the base model that translates camelCase requests to snake_case attributes:
```python
# Inside codepy.database.activerecord.Model
def __getattr__(self, name: str) -> Any:
    # If legacy code calls user.firstName, translate to user.first_name
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return self.get_attribute(snake_name)
```
