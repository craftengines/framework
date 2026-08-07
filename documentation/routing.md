# Routing

Craft includes a highly flexible and expressive routing engine mapped via the `Route` facade. The routes map incoming HTTP request methods and paths directly to controller actions or closure handlers.

Routes are defined inside the `routes/` directory:
- `routes/web.py` for standard browser-based HTML routes (supporting session state, cookie-based auth, CSRF validations, and template responses).
- `routes/api.py` for stateless JSON API routes (typically prefixed with `/api`).

---

## Basic Routes

You map paths to a controller action using a list with the controller class and the string action name:

```python
from craft.facades import Route
from app.Http.Controllers.Blog.PostController import PostController

# Basic GET route
Route.get("/posts", [PostController, "index"]).name("posts.index")

# POST route
Route.post("/posts", [PostController, "store"]).name("posts.store")
```

Other supported HTTP verbs include:
```python
Route.put("/posts/{id}", [PostController, "update"])
Route.patch("/posts/{id}", [PostController, "patch"])
Route.delete("/posts/{id}", [PostController, "destroy"])
```

---

## Route Parameters

You capture dynamic path parameters using curly braces `{}`. These are parsed and passed as keyword arguments to the mapped controller action:

```python
# Route mapping
Route.get("/posts/{id}", [PostController, "show"]).name("posts.show")

# Controller Action
class PostController(Controller):
    async def show(self, request, id: str):
        post = await Post.find_or_fail(id)
        return view("posts.show", {"post": post})
```

---

## Route Named Access

You can chain `.name()` to name a route. This decouples your HTML templates and controller redirects from hardcoded URLs.
Generate URLs using the global helper `route()` or `Route.url_for()`:

```python
# Generate path
url = route("posts.show", id="some-uuid-value")  # returns '/posts/some-uuid-value'
```

---

## Route Groups

Grouping allows you to apply bulk attributes—such as route prefixes, shared middleware, or name prefixes—to multiple routes at once:

```python
Route.group(
    lambda: (
        Route.get("/dashboard", [AdminController, "index"]).name("dashboard"),
        Route.get("/settings", [AdminController, "settings"]).name("settings"),
    ),
    prefix="/admin",
    middleware=["auth"],
    name="admin.",
)
```
- Mapped URLs: `/admin/dashboard`, `/admin/settings`
- Route names: `admin.dashboard`, `admin.settings`
- Middleware applied: `auth` middleware group/class.

---

## Resource Controllers

A single call to `Route.resource` maps standard RESTful operations on a resource to their corresponding controller actions:

```python
Route.resource("posts", PostController)
```

The resource mapper registers the following routes:

| Verb | Path | Action | Route Name | Description |
|---|---|---|---|---|
| GET | `/posts` | `index` | `posts.index` | List posts |
| GET | `/posts/create` | `create` | `posts.create` | Form to create post |
| POST | `/posts` | `store` | `posts.store` | Store a new post |
| GET | `/posts/{post}` | `show` | `posts.show` | Display a post |
| GET | `/posts/{post}/edit`| `edit` | `posts.edit` | Form to edit post |
| PUT/PATCH| `/posts/{post}` | `update` | `posts.update` | Update a post |
| DELETE | `/posts/{post}` | `destroy` | `posts.destroy`| Delete a post |

Use `Route.api_resource` to exclude `create` and `edit` routes when mapping REST APIs.
