# Migrations, Seeders & Factories

Craft provides database schema version control (Migrations) and database seeding tools (Seeders and Factories) to set up and manage database states across different environments.

---

## Migrations

Migrations are stored in `database/migrations/` and contain two functions: `up()` to create/modify tables, and `down()` to reverse the change.

### Example Migration

```python
from craft.migrations import Migration, Schema

def up():
    Schema.create_table("posts", lambda t: (
        t.id(),
        t.string("title").unique(),
        t.text("body"),
        t.boolean("published").default(False),
        t.foreign_id("user_id").constrained().cascade_on_delete(),
        t.timestamps(),
    ))

def down():
    Schema.drop_table("posts")
```

### Table Column Types

The table builder object (`t`) supports the following data type definitions:

- `t.id()`: Auto-incrementing or UUID primary key.
- `t.string(name)`: Standard character string.
- `t.text(name)`: Rich/long text block.
- `t.integer(name)`: Number field.
- `t.boolean(name)`: True/False field.
- `t.uuid(name)`: Unique UUID column.
- `t.timestamps()`: Automatically generates `created_at` and `updated_at` datetime columns.
- `t.foreign_id(name).constrained()`: Creates a foreign key constraint linking to the referenced primary key.

### Running Migrations

Manage database schemas using the `dev.py` CLI:

```bash
# Run all pending migrations
python dev.py migrate

# Drop all tables and rerun all migrations from scratch
python dev.py migrate fresh
```

---

## Seeders

Seeders populate your database with dummy or initial system records. They inherit from `craft.seeding.Seeder` and define a `run` method:

### Example Seeder

```python
from craft.seeding import Seeder
from app.Models.User import User
from craft.facades import DB

class DatabaseSeeder(Seeder):
    def run(self):
        # 1. Clean existing records (Optional)
        DB.statement("DELETE FROM users")

        # 2. Add records
        User.create({
            "name": "Admin User",
            "email": "admin@craft.io",
            "password": "hashed-secret-password"
        })
```

Execute seeders by running:
```bash
python dev.py db seed
```

---

## Factories

Factories define default mock attribute layouts for your models. They utilize the Python `faker` library to generate realistic test data:

### Example Factory

```python
from craft.factories import Factory
from app.Models.Post import Post

class PostFactory(Factory):
    model = Post

    def definition(self):
        return {
            "title": self.faker.sentence(),
            "body": self.faker.paragraph(),
            "published": True,
            "user_id": "user-uuid"
        }
```

Use factories within seeders or unit tests to generate multiple records quickly:
```python
# Create and save a single post to the database
post = PostFactory.new().create()

# Generate a list of 5 unsaved post model instances
posts = PostFactory.new().count(5).make()
```
