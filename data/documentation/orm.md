# Craft ORM (Active Record)

Craft ORM is an Active Record ORM built specifically for the Python ecosystem. It combines simple class-based model definitions with a custom, dependency-free query builder — there is no SQLAlchemy underneath it. Database access is synchronous, via `sqlite3`, `psycopg2` (PostgreSQL), and `PyMySQL` (MySQL).

---

## Defining Models

All database models inherit from `craft.orm.Model`. By default, the database table name is inferred as the lowercase, snake_case plural version of the model class name:

```python
from craft.orm import Model

class Post(Model):
    # Attributes allowed to arrive in bulk via create()
    fillable = ["title", "body", "user_id", "published"]
```

Class attributes a model understands:

| Attribute | Default | Purpose |
|---|---|---|
| `__table__` | inferred | Override the table name |
| `fillable` | `[]` | Columns allowed in mass assignment via `create()`. Fails closed: empty means *nothing* is mass-assignable. |
| `guarded` | `True` | Set `False` to disable mass-assignment filtering entirely (explicit opt-out) |
| `hidden` | `[]` | Columns excluded from `to_dict()` |
| `defaults` | `{}` | Column values applied on create when the caller omits them |
| `primary_key` | `"id"` | Primary key column |
| `key_type` | `"int"` | `"int"` (auto-increment) or `"uuid"` (client generated) |
| `uses_uuid` | `True` | Fill a public `uuid` column on create when the table has one |
| `uuid_column` | `"uuid"` | Name of the public UUID column |

---

## CRUD Operations

### Create
```python
post = Post.create({
    "title": "Clean Code in Python",
    "body": "Keep code modular and robust.",
    "user_id": "user-uuid",
    "published": True
})
```

`create()` enforces mass-assignment protection and fails closed: only
columns listed in `fillable` (plus the framework-managed primary key, UUID,
and timestamp columns) are taken from the input; everything else is
dropped. An empty/undeclared `fillable` means *nothing* is mass-assignable —
not "everything". A model that genuinely wants every column writable from
request input must opt in explicitly with `guarded = False`. Trusted,
internal input should instead use `Post.force_create({...})`, which bypasses
the guard entirely.

### Read
```python
# Find a model by its primary key (honours a custom `primary_key`)
post = Post.find("some-uuid")

# Find a model or raise a ModelNotFoundError (from craft.orm exceptions)
post = Post.find_or_fail("some-uuid")
```

### Update
```python
# Update attributes and save to the database
post.update({"title": "Updated Title"})

# Or set attributes individually, then save
post.set_attribute("title", "Updated Title")
post.save()
```

### Delete
```python
post.delete()
```

---

## Querying & Filtering

Use `Model.query()` to get a fluent, chainable `QueryBuilder` instance:

```python
# Chain where filters, sorting, and pagination
posts = (
    Post.query()
    .where("published", True)
    .where_in("user_id", ["uuid-1", "uuid-2"])
    .order_by_desc("created_at")
    .limit(10)
    .get()  # returns a Collection of Post models
)
```

Available terminal methods:
- `.get()`: Returns a `Collection` containing all matching model instances.
- `.first()`: Returns the first matching model instance or `None`.
- `.count()`: Returns the integer count of matching records.
- `.paginate(per_page=15)`: Returns a pagination object containing the current subset of results and pagination metadata.

All ORM and query builder calls are **synchronous** — no `await` is needed
(or accepted) anywhere in the ORM.

### Safety guarantees

- **`None` comparisons**: `where(col, None)` and `where(col, "=", None)`
  compile to `IS NULL`; `where(col, "!=", None)` / `where(col, "<>", None)`
  compile to `IS NOT NULL`. Any other operator with `None` raises `ValueError`.
- **Identifier validation**: column and table names must match
  `^[A-Za-z_][A-Za-z0-9_.]*$`, and operators are checked against a whitelist —
  anything else raises `ValueError`, so user input can never smuggle SQL into
  a query.
- **`or_where` grouping**: an `OR` parenthesises everything built so far
  (`(a AND b) OR c`), so earlier conditions such as soft-delete scoping are
  never bypassed by a trailing `or_where`.
- **Update timestamps**: `QueryBuilder.update()` only stamps `updated_at` on
  model-backed queries — raw table updates (pivot tables, ad-hoc tables) are
  left untouched.

---

## Relationships

Relationships are defined as methods returning relationship proxies. Calling the relation method gives you a proxy; use `get()` or `first()` on it to run the query.

### One-to-Many (`has_many` / `belongs_to`)

#### User Model:
```python
class User(Model):
    fillable = ["name", "email", "password"]

    def posts(self):
        return self.has_many(Post)
```

#### Post Model:
```python
class Post(Model):
    fillable = ["title", "body", "user_id"]

    def user(self):
        return self.belongs_to(User)
```

#### Accessing relationships:
```python
user = User.find("user-uuid")
# Use get() on the proxy to retrieve posts
posts = user.posts().get()

post = Post.find("post-uuid")
# belongs_to returns a relation proxy — resolve the parent with first()
author = post.user().first()
```

---

## Read/Write Database Replicas

Craft ORM has built-in query splitting support. It automatically handles replica routing dynamically:
- **Write connection (`read=False`)**: Used for mass write executions (`insert`, `update`, `delete`), migrations, and direct database execution statements.
- **Read connection (`read=True`)**: Used automatically by the query builder for selecting data (`SELECT` queries, `get()`, `first()`, `count()`, `paginate()`, and `Model.find()`).
This routes heavy data-reading traffic to read-only replicas without requiring manual connection management from the application code.

---

## UUID identity

Every model carries two identifiers by default: the integer `id` — narrow,
sequential, fast to join and to use as a foreign key — and a `uuid`, which is
what you expose publicly. A sequential id in a URL tells anyone how many records
you have and invites walking the table by incrementing a number.

Declare the column and the framework fills it in:

```python
Schema.create_table("products", lambda t: (
    t.id(),          # primary key
    t.uuid_key(),    # public identifier, unique
    t.string("name"),
    t.timestamps(),
))
```

```python
product = Product.create({"name": "Desk"})
product.get_attribute("id")     # 1
product.get_attribute("uuid")   # '3f2504e0-4f89-11d3-9a0c-0305e82c3301'

Product.find_by_uuid(value)
Product.find_by_uuid_or_fail(value)
```

Use it in routes without leaking the key:

```python
def show(self, request, id):
    product = Product.find_by_route_key(id)   # resolves a UUID or an id
```

`route_key()` returns the UUID when the model has one, so URL generation picks
it up automatically.

A table with no `uuid` column is untouched — nothing is inserted that the schema
does not declare. Opt a model out with `uses_uuid = False`, or rename the column
with `uuid_column`.

For a UUID as the primary key itself, with no integer at all:

```python
Schema.create_table("events", lambda t: (t.uuid_primary(), t.timestamps()))

class Event(Model):
    key_type = "uuid"
```

## Multi-Tenant Database Schema Isolation

For multi-tenant SaaS environments, Craft ORM supports physical database schema-based isolation out-of-the-box in PostgreSQL.

### Architecture
1. **Dynamic search_path Switch**: `DB.set_tenant_schema(name)` runs `SET search_path TO "{tenant_schema}", public;` on the connection. Craft talks to the driver directly (psycopg2) — there is no connection-pooling ORM layer in between.
2. **On-the-Fly Schema Creation**: `DB.ensure_tenant_schema(name)` checks whether the schema exists; if not, it creates it and runs all migrations inside it. On drivers without schema support (SQLite) it is a no-op, so tenant-aware middleware still runs in development and tests.

### How it works
The dynamic schema isolation is automatically handled by the `TenantMiddleware`. You can also switch schemas manually from code:

```python
from craft.facades import DB

# Set the active tenant schema
DB.set_tenant_schema("tenant_cc751989_2bc1_4bcb_ae17_bc46adc5d5f7")

# Ensure the schema is created and fully migrated
DB.ensure_tenant_schema("tenant_cc751989_2bc1_4bcb_ae17_bc46adc5d5f7", tenant_user_model)

# Clear/disable tenant isolation and fallback to public schema
DB.set_tenant_schema(None)
```
