# CRUD builder

Generates a full vertical slice for an entity — migration, model, controller,
form request, resource, and route — wired to real database calls, not
placeholder scaffolds. Available both from the CLI and from the admin UI.

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
`services/cli/generators.py`). `PostController` additionally calls
`Gate.authorize(...)` in `store`/`update`/`destroy` to deny non-owner
writes; the generated CRUD controller does **not** add that call, since
there's no policy to authorize against for an arbitrary entity — add an
ownership check yourself once the model has a `user_id` column, following
the `TODO` left in the generated FormRequest.

Run the migration afterwards:

```bash
python dev.py migrate
```

Pass `--force` to overwrite files that already exist.

## Admin UI

`GET /admin/crud-builder` (behind the `auth` middleware, like `/admin`) shows
a form: an entity name plus repeatable field rows (name, type, required).
Submitting `POST /admin/crud-builder` runs the same `build_crud()` used by
the CLI and shows a report listing every file written.

As with the CLI, migrations are **not** run automatically — review the
generated migration and run `python dev.py migrate` yourself.

## Programmatic use

Both the CLI and the admin controller call into `services/cli/crud_builder.py`:

```python
from services.cli import crud_builder

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
