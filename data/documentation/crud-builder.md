# CRUD builder

Generates a full vertical slice for an entity — migration, model, controller,
form request, resource, route, **and a server-rendered admin UI** — wired to
real database calls, not placeholder scaffolds. Available both from the CLI
and from the admin UI.

## CLI

```bash
python dev.py make crud Product --fields "name:string:required,price:decimal,active:boolean"
```

`--fields` is a comma-separated list of `name:type[:rule1|rule2|...]`. `type`
is one of `string`, `text`, `integer`, `boolean`, `decimal`, `date`,
`datetime` — the same vocabulary `Schema`'s `Blueprint` supports. If a
field's rules include `required` it becomes a non-nullable column;
otherwise it is nullable. Omit `--fields` for a bare entity with no columns
beyond `id`/`timestamps`.

This creates:

| File | Purpose |
|---|---|
| `database/migrations/*_create_products_table.py` | Table DDL |
| `app/Models/Product.py` | Model with `fillable` from the field list |
| `app/Http/Requests/StoreProductRequest.py` | Validation rules from the field list |
| `app/Http/Resources/ProductResource.py` | Every field exposed in `to_array()` |
| `app/Http/Controllers/ProductController.py` | `index/show/store/update/destroy`, querying the model |
| `resources/views/admin/products/index.forge.py` | Admin list view — one table column per field, edit/delete per row |
| `resources/views/admin/products/create.forge.py` | Admin create form |
| `resources/views/admin/products/edit.forge.py` | Admin edit form |
| `app/Http/Controllers/Admin/ProductAdminController.py` | Server-rendered `index/create/store/edit/update/destroy` |

It also appends a self-contained `Route.group(..., prefix="/api/v1", ...)`
block registering `Route.api_resource("products", ProductController,
write_middleware=["api", "auth"])` to `routes/api.py`, after a `# CRUD
Builder Routes` marker comment — idempotent, so generating the same entity
twice does not duplicate the route. Generated controllers only return JSON,
so they're registered as an API resource (matching the existing
`PostController` convention) rather than in `routes/web.py`, which is behind
CSRF verification that a JSON client has no `_token` to satisfy. Reads stay
public; writes (`store`/`update`/`destroy`) go through `["api", "auth"]`:
`api` (`AuthenticateApiToken`) resolves a user from a bearer token if one is
sent, then `auth` (`RequireAuth`) is the alias that actually rejects the
request when nobody ended up authenticated — `AuthenticateApiToken` alone
never blocks a missing/invalid token, it just continues unauthenticated.
The generated `StoreProductRequest.authorize()` also checks for an
authenticated user by default (see the `request_stub` template in
`engine/cli/generators.py`). `PostController` additionally calls
`Gate.authorize(...)` in `store`/`update`/`destroy` to deny non-owner
writes; the generated CRUD controller does **not** add that call, since
there's no policy to authorize against for an arbitrary entity — add an
ownership check yourself once the model has a `user_id` column, following
the `TODO` left in the generated FormRequest.

It also registers a server-rendered admin UI, by default, with no extra flag:
`GET /admin/products` (list), `GET /admin/products/create`, `POST
/admin/products`, `GET /admin/products/{id}/edit`, `PUT
/admin/products/{id}`, `DELETE /admin/products/{id}` — all behind the `auth`
middleware, appended to `routes/web.py` after a `# CRUD Builder Admin Routes`
marker (idempotent, same discipline as the JSON API block). This is a
**separate controller** (`ProductAdminController`, under `app/Http/
Controllers/Admin/`) from the JSON API's `ProductController` — same entity,
no name collision, both coexist and can be generated together for the same
model. The admin views follow the plain server-rendered style already used
by `posts/*.forge.py`: a table with one column per field (long `text` fields
are truncated in the list), the same dashed-border empty state when there
are zero records, and a create/edit form with one labeled input per field
(checkbox for `boolean`, date input for `date`/`datetime`, textarea for
`text`, text/number input otherwise), CSRF token, and `old()`-based
validation-error redisplay (mirroring `PostController.store()`/`update()`).

Run the migration afterwards:

```bash
python dev.py migrate
```

Pass `--force` to overwrite files that already exist.

## CRUD builder form (`/admin/crud-builder`)

`GET /admin/crud-builder` (behind the `auth` middleware, like `/admin`) shows
a form: an entity name plus repeatable field rows (name, type, required).
Submitting `POST /admin/crud-builder` runs the same `build_crud()` used by
the CLI and shows a report listing every file written — migration, model,
request, resource, both controllers, the three admin views, and both route
registrations.

As with the CLI, migrations are **not** run automatically — review the
generated migration and run `python dev.py migrate` yourself.

## Generated admin UI (`/admin/<slug>`)

Once an entity is generated (and its migration run), its records get a real
admin screen for free — no hand-written view or controller needed: a list at
`/admin/<slug>` with a "New <Entity>" button and an edit/delete link per row,
and create/edit forms with one input per field. This is what closes the gap
with frameworks that give a free admin list+edit UI from a model
registration — Craft's CRUD builder no longer stops at a JSON API.

## Programmatic use

Both the CLI and the admin controller call into `engine/cli/crud_builder.py`:

```python
from craft.cli import crud_builder

result = crud_builder.build_crud(
    "Product",
    [
        {"name": "name", "type": "string", "nullable": False},
        {"name": "price", "type": "decimal", "nullable": True},
    ],
    base_path,
)
# result["files"] -> {"migration": "...", "model": "...", ...}
```
