# Codepyquent ORM (Active Record)

Codepyquent is an Active Record ORM built specifically for the Python ecosystem. It provides an Eloquent-like experience by combining simple class-based model definitions with the efficiency of SQLAlchemy 2.0 Core.

---

## Defining Models

All database models inherit from `codepy.orm.Model`. By default, the database table name is inferred as the lowercase, snake_case plural version of the model class name:

```python
from codepy.orm import Model

class Post(Model):
    # Set list of attributes allowed to be set in bulk via create() or fill()
    fillable = ["title", "body", "user_id", "published"]

    # Cast database values automatically when read or saved
    casts = {
        "published": "boolean",
        "user_id": "string",
    }
```

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

### Read
```python
# Find a model by its primary key (ID)
post = await Post.find("some-uuid")

# Find a model or raise a ModelNotFoundException (resulting in a 404 response)
post = await Post.find_or_fail("some-uuid")
```

### Update
```python
# Update attributes and save to the database
post.fillable_attributes({"title": "Updated Title"})
post.save()

# Or update directly
post.update({"title": "Updated Title"})
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

---

## Relationships

Relationships are defined as methods returning relationship proxies. To keep execution non-blocking, always access relationships asynchronously.

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
user = await User.find("user-uuid")
# Use get() on the proxy to retrieve posts
posts = await user.posts().get()

post = await Post.find("post-uuid")
# Resolves the parent User model directly
author = await post.user()
```

---

## Read/Write Database Replicas

Codepyquent has built-in query splitting support. It automatically handles replica routing dynamically:
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

For multi-tenant SaaS environments, Codepyquent supports physical database schema-based isolation out-of-the-box in PostgreSQL.

### Architecture
1. **Dynamic search_path Switch**: `DB.set_tenant_schema(name)` runs `SET search_path TO "{tenant_schema}", public;` on the connection. Codepy talks to the driver directly (psycopg2), not through a SQLAlchemy pool.
2. **On-the-Fly Schema Creation**: `DB.ensure_tenant_schema(name)` checks whether the schema exists; if not, it creates it and runs all migrations inside it. On drivers without schema support (SQLite) it is a no-op, so tenant-aware middleware still runs in development and tests.

### How it works
The dynamic schema isolation is automatically handled by the `TenantMiddleware`. You can also switch schemas manually from code:

```python
from codepy.facades import DB

# Set the active tenant schema
DB.set_tenant_schema("tenant_cc751989_2bc1_4bcb_ae17_bc46adc5d5f7")

# Ensure the schema is created and fully migrated
DB.ensure_tenant_schema("tenant_cc751989_2bc1_4bcb_ae17_bc46adc5d5f7", tenant_user_model)

# Clear/disable tenant isolation and fallback to public schema
DB.set_tenant_schema(None)
```
