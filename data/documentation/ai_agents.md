# AI Agent Integration & Discovery Guide

Craft Engine is designed from the ground up to be **AI-Native** and exceptionally developer-friendly for both humans and autonomous coding agents (Cursor, Claude Code, GitHub Copilot, Windsurf, AGY).

---

## 🤖 Why Craft Engine is Agent-Friendly

1. **Active Record & Laravel-Style Ergonomics**:
   LLMs have been trained on vast amounts of Laravel, Django, and FastAPI code. Craft Engine uses the exact same intuitive mental models:
   - `Model.find(id)` / `Model.where(...)`
   - `Route.get(...)` / `Route.post(...)`
   - `Validator.make(data, rules)`
   - Controllers, FormRequests, Resources, and Forge templates.
2. **Deterministic CLI Tooling**:
   - Every file can be generated deterministically via `python dev.py make:*` (`make:model`, `make:controller`, `make:request`, `make:crud`, `make:auth`).
   - Predictable directory structures: `app/Models`, `app/Http/Controllers`, `database/migrations`, `resources/views`.
3. **Absolute Data Persistence**:
   - Clear architectural constraints prevent catastrophic data wipes. Destructive commands (`migrate:fresh`, `db:wipe`) are hard-blocked.
4. **Standardized Context Files (`llms.txt`)**:
   - Adheres to the [llmstxt.org](https://llmstxt.org/) specification for zero-friction LLM indexing.

---

## ⚡ Scaffolding Agent Rules & Context

Run the built-in scaffolding command to equip your repository with instant AI capabilities:

```bash
python dev.py agent:scaffold
```

This generates:
- `.cursorrules` — Directives for Cursor and IDE assistants, setting guidelines for file paths, facades, validation rules, and database safety.
- `llms.txt` — Standard high-density overview of Craft Engine for LLMs.
- `llms-full.txt` — Full API contracts and code examples.
- `.agents/mcp.json` — Model Context Protocol config snippet.

---

## 🛡️ Form Validation & Anti-Spam in Agent Code

When AI agents generate forms, Craft Engine provides single-line directives for complete bot defense and validation feedback:

```html
<!-- resources/views/contact.forge.py -->
@extends("layouts.app")

@section("content")
<form action="/contact" method="POST">
    @csrf
    @honeypot

    <div>
        <label>Your Email</label>
        <input type="email" name="email" value="{{ old('email', '') }}">
        @error('email')
            <span class="error">{{ message }}</span>
        @enderror
    </div>

    <button type="submit">Send</button>
</form>
@endsection
```

And in the controller:

```python
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.validation.validator import Validator

class ContactController(Controller):
    def store(self, request):
        validator = Validator.make(request.all(), {
            "email": ["required", "email"],
            "message": ["required", "text", "no_html", "spam_free"],
        })

        if validator.fails():
            return redirect.back().with_errors(validator.errors()).with_input()

        # Process contact message...
        return redirect(route="contact.success")
```

---

## 🛠️ Scaffolding Authentication (`make:auth`)

To generate a complete, working authentication system:

```bash
python dev.py make:auth
```

This scaffolds:
- `app/Http/Controllers/Auth/AuthController.py`
- `app/Http/Requests/Auth/LoginRequest.py`
- `app/Http/Requests/Auth/RegisterRequest.py`
- `resources/views/auth/login.forge.py` (with `@csrf`, `@honeypot`, `@error`)
- `resources/views/auth/register.forge.py`
- `resources/views/auth/dashboard.forge.py`
- Idempotently wires `/login`, `/register`, `/logout`, and `/dashboard` into `routes/web.py`.
