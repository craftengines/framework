# Controllers, Requests, Validation & Views

Controllers organize request-handling logic in a central location. They receive an HTTP request, perform actions, and return an HTTP response.

---

## Controllers

Controllers inherit from the base class `craft.http.Controller`. Action methods accept a `Request` parameter (plain `def` is the norm — the ORM is synchronous; `async def` actions are also awaited by the kernel if you need them for other I/O):

```python
from craft.http import Controller, Request
from app.Models.Post import Post

class PostController(Controller):
    def index(self, request: Request):
        posts = Post.query().get()
        return self.view("posts.index", {"posts": posts})
```

---

## HTTP Requests

The `Request` object exposes incoming payload data, files, and server properties:

```python
# Retrieve request input parameters (combines JSON body, Form data, and Query arguments)
title = request.input("title", default="Default Title")

# Retrieve all input parameters as a dictionary
data = request.all()

# Access request properties
method = request.method
path = request.path
headers = request.headers
cookies = request.cookies
```

---

## Form Validation (FormRequest)

For complex validation layouts, define a `FormRequest` class mapping a declarative rules list to incoming request data. The validator enforces constraints dynamically:

### Example FormRequest

```python
from craft.validation import FormRequest

class StorePostRequest(FormRequest):
    def authorize(self) -> bool:
        # Perform authorization checks (e.g. return Auth.check())
        return True

    def rules(self) -> dict:
        return {
            "title": ["required", "string", "max:255"],
            "body": ["required", "string"],
            "published": ["sometimes", "boolean"],
        }
```

### Validating Requests in Controllers

Invoke `.validated()` inside your controller action. It authorizes first (raising `AuthorizationException`, rendered as 403), then validates — a failure raises `ValidationException`, rendered by the exception handler as a `422 Unprocessable Entity` response. On success it returns only the fields you wrote rules for:

```python
from craft.support import redirect

def store(self, request: Request):
    # Authorize and validate the request
    validated_data = StorePostRequest(request).validated()

    # Create post using validated attributes
    post = Post.create(validated_data)

    return redirect(route="posts.show", id=post.get_attribute("id"))
```

`redirect` is a plain function: `redirect(url)` for a literal URL, or `redirect(route="name", **params)` for a named route. Inside a controller, `self.redirect(...)` does the same.

---

## Views & Templating (Forge Engine)

The Forge templating engine compiles HTML files inside `resources/views/`. It compiles Forge markup syntax into pure Jinja2 templates.

### Rendering

Render templates with the controller's `self.view()` helper:
```python
return self.view("posts.index", {"posts": posts})
```

Prefer `self.view()`: rendering errors propagate to the exception handler, so a missing template raises `TemplateNotFound` instead of failing silently. (A standalone `view()` function also exists in `craft.support`, but it swallows rendering errors and returns a placeholder response — avoid it in application code. See [Views](views.md).)

### Syntax Examples

#### Layout Extension (`resources/views/posts/index.forge.py`)
```html
@extends("layouts.app")

@section("title", "Active Posts")

@section("content")
    <h1 class="text-3xl font-bold">Latest Posts</h1>
    <div class="space-y-4">
        @foreach(posts as post)
            <article class="p-4 border rounded">
                <h2>{{ post.title }}</h2>
                <p>{{ post.body }}</p>
            </article>
        @endforeach
    </div>
@endsection
```

#### Authorization & CSRF Helpers
```html
<!-- Display blocks to authenticated users only -->
@auth
    <p>Welcome, {{ auth().get_attribute('name') }}</p>
@endauth

<!-- Form setup with CSRF protection token -->
<form action="/posts" method="POST">
    @csrf
    <input type="text" name="title" />
    <button type="submit">Submit</button>
</form>
```
