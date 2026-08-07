# Authorization (RBAC)

Craft ships a role-based access control (RBAC) system on top of the Gate/Policy
authorization already described in [Security](security.md). Where Gates and
Policies are hand-written per ability, RBAC lets you drive authorization from
data: assign roles to users, permissions to roles, and check either from a
controller, a Gate ability, or a route middleware.

## The 4 tables

| Table | Columns | Purpose |
|---|---|---|
| `roles` | `id`, `name`, `slug` | A named role, e.g. `admin`, `tenant-manager` |
| `permissions` | `id`, `name`, `slug` | A named permission, e.g. `manage-users` |
| `role_user` | `user_id`, `role_id` | Pivot: which roles a user has |
| `permission_role` | `role_id`, `permission_id` | Pivot: which permissions a role grants |

A user's permissions are the union of the permissions of every role they hold
— there is no direct user-to-permission assignment, by design: manage access
through roles.

## Models

`app/Models/Role.py` and `app/Models/Permission.py` are plain Craft ORM
models (`fillable = ["name", "slug"]`). The relations and checks live on the
base `Model` class (`services/orm/model.py`), so every model — not just
`User` — can carry roles and permissions if your app needs that:

```python
from craft.facades import Auth

user = Auth.user()

user.roles()                   # BelongsToMany -> Role, through role_user
user.permissions()             # BelongsToMany -> Permission, through permission_role
user.has_role("admin")         # bool — does the user hold this role?
user.has_permission("manage-users")  # bool — does any of the user's roles grant this?
```

`permissions()` on a `Role` instance returns the permissions granted to that
role (through `permission_role`); `permissions()` on a `User` is not itself
meaningful — check via `has_permission`, which follows `role_user` ->
`permission_role` in a single query.

## The Gate fallback tier

`GateManager.allows(ability, user, *args)` (`services/auth/gate.py`) resolves
an ability in three steps:

1. A registered ability closure (`Gate.define(...)`).
2. A policy on the target model's class (`Gate.policy(...)`).
3. **RBAC fallback** — if `user` has a `has_permission` method, `Gate.allows`
   calls `user.has_permission(ability)`. If that returns `True`, access is
   granted.
4. Deny by default.

This means a permission slug doubles as a Gate ability for free — grant
`"manage-users"` to a role, assign the role to a user, and
`Gate.allows("manage-users", user)` (or `Gate.authorize(...)`) just works,
with no closure to write. An explicit `Gate.define` or `Policy` method still
takes priority over the RBAC fallback, so you can override behaviour for a
specific ability without touching the role/permission data.

## Route middleware

Two middleware classes (`services/http/middleware.py`) enforce roles and
permissions at the route level, resolved through parameterized aliases in the
kernel (`services/http/kernel.py`):

```python
from craft.facades import Route

Route.get("/admin/roles", [RoleController, "index"]).middleware("auth", "role:admin")
Route.get("/reports", [ReportController, "index"]).middleware("auth", "permission:view-reports")
```

`"role:<slug>"` and `"permission:<slug>"` split on the first `:`; the base
alias (`role` / `permission`) resolves to `RequireRole` / `RequirePermission`,
and the slug is passed to the middleware's constructor
(`RequireRole(role="admin")`). Both middleware classes:

- Look up `Auth.user()`.
- Return **403** (via `AuthorizationException`) when the request expects JSON
  (`request.expects_json()`) and the check fails.
- Redirect to `/login` when there is no authenticated user at all and JSON was
  not requested.
- Otherwise raise the same 403 for an authenticated user missing the
  role/permission.

Unknown aliases — including a malformed `"role"` with no `:param` — still
raise `KeyError` at boot, same as any other unregistered route middleware
alias: a route that declares protection which silently does nothing is worse
than one that fails loudly.

## CLI

`dev.py` exposes RBAC management under three sub-apps (`services/cli/app.py`):

```bash
python dev.py role:list
python dev.py role:create "Tenant Manager" tenant-manager
python dev.py permission:list
python dev.py permission:create "Manage Users" manage-users
python dev.py role:grant tenant-manager manage-users
python dev.py user:assign-role tenant@craft.local tenant-manager
```

## Admin UI

`GET /admin/roles` lists every role with its granted permissions and a form to
grant a permission to a role; `GET /admin/permissions` lists every permission.
Both are behind `auth` and `role:admin` (`app/Http/Controllers/Admin/RoleController.py`,
`resources/views/admin/roles/index.forge.py`,
`resources/views/admin/permissions/index.forge.py`) — the first real usage of
the `role:<slug>` middleware in the shipped skeleton.

## Recipes

**Protect a new route by role.**

```python
# routes/web.py
Route.get("/reports", [ReportController, "index"]).middleware("auth", "role:admin")
```

`"auth"` first (redirects a guest to `/login` before `RequireRole` even runs —
without it, an unauthenticated request would 403 instead of getting the
familiar login redirect). Order matters here the same way it does for
`session`/`csrf`/`auth` in `bootstrap/app.py`.

**Protect a route by permission instead of role** — use this when the check
should survive a role being renamed or restructured later:

```python
Route.get("/reports", [ReportController, "index"]).middleware("auth", "permission:view-reports")
```

**Check inside a controller**, when the route-level middleware isn't granular
enough (e.g. the same route serves different content by permission):

```python
from craft.facades import Auth, Gate

class ReportController(Controller):
    def index(self, request):
        if not Auth.user().has_permission("view-reports"):
            return self.json({"message": "Forbidden"}, status=403)
        ...
```

or, to reuse the Gate fallback tier and get consistent exception handling:

```python
Gate.authorize("view-reports", Auth.user())  # raises AuthorizationException if denied
```

**Check inside a Forge view** — `has_permission`/`has_role` are plain model
methods, so they work through the `auth` global helper:

```html
@if(auth() and auth().has_permission("manage-users"))
    <a href="/admin/roles">Manage roles</a>
@endif
```

**Add a brand-new role from scratch**, end to end:

```bash
python dev.py permission:create "Export Data" export-data
python dev.py role:create "Analyst" analyst
python dev.py role:grant analyst export-data
python dev.py user:assign-role someone@example.com analyst
```

No migration needed — `roles`/`permissions`/the two pivot tables already
exist from the framework's own migrations. A new role or permission is just
a row.

## The 3 demo accounts

The framework seeds 3 demo accounts forming a role ladder: `user` (basic) ->
`tenant-manager` (elevated — has `manage-users` but isn't a full admin) ->
`admin` (full access, every permission). See [the README's Demo
accounts section](../README.md#demo-accounts) for emails/passwords and what
each one demonstrates.
