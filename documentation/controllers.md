# Controllers, Requests, Validation & Views

Controllers organize request-handling logic in a central location. They receive an HTTP request, perform actions, and return an HTTP response.

---

## Controllers

Controllers inherit from the base class `craft.http.Controller`. Action methods are typically asynchronous and accept a `Request` parameter:

```python
from craft.http import Controller, Request
from app.Models.Post import Post
from craft.support import view

class PostController(Controller):
    async def index(self, request: Request):
        posts = await Post.query().get()
        return view("posts.index", {"posts": posts})
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

Invoke `.validate()` inside your controller action. If validation fails, it throws a validation exception (automatically redirecting back with errors for browser views or returning a `422 Unprocessable Entity` JSON response for API routes):

```python
async def store(self, request: Request):
    # Validate request
    validated_data = await StorePostRequest(request).validate()

    # Create post using validated attributes
    post = Post.create(validated_data)

    return redirect().route("posts.show", id=post.id)
```

---

## Views & Templating (Forge Engine)

The Forge templating engine compiles HTML files inside `resources/views/`. It compiles taravel Forge markup syntax into pure Jinja2 templates.

### Render Helper

Render templates using the global `view()` helper:
```python
return view("posts.index", {"posts": posts})
```

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
