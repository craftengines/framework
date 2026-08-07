# API Resources

A Resource controls exactly what leaves your application for a given model. It
is the boundary between your database columns and your public API.

## Defining one

```python
# app/Http/Resources/PostResource.py
from craft.resources import Resource


class PostResource(Resource):
    def to_array(self, request=None) -> dict:
        post = self.resource
        return {
            "id": post.get_attribute("id"),
            "title": post.get_attribute("title"),
            "body": post.get_attribute("body"),
            "published": bool(post.get_attribute("published")),
        }
```

```bash
python dev.py make resource Post
```

## Using one

```python
def show(self, request, id):
    post = Post.find_or_fail(id)
    return PostResource(post).response()
```

Or build the payload yourself:

```python
return self.json({"data": PostResource(post).to_array()})
```

## to_array or to_dict

Override whichever reads better. Both are honoured, and they agree:

```python
class PostResource(Resource):
    def to_dict(self) -> dict:
        return {"id": self.resource.get_attribute("id")}
```

> The base class used to read `self.resource.to_dict()` directly, so a subclass
> that defined `to_dict()` was ignored and the **entire model** was emitted —
> including fields you deliberately left out. If you are upgrading, check any
> resource that overrode `to_dict()`: it now does what it always looked like it
> did.

With no override, the resource passes the model through unchanged. That is a
sensible default for internal endpoints and the wrong one for public APIs — be
explicit about what you expose.

## Collections

```python
def index(self, request):
    return PostResource.collection(Post.all()).response()
```

```json
{ "data": [ { "id": 1, "title": "First" } ] }
```

Pagination metadata is carried through automatically:

```python
posts = Post.query().paginate(per_page=15, page=1)
return PostResource.collection(posts).response()
```

```json
{
  "data": [ ... ],
  "meta": { "total": 42, "per_page": 15, "current_page": 1, "last_page": 3 }
}
```

Add your own metadata:

```python
PostResource.collection(posts).response(meta={"version": "1"})
```

## Conditional fields

```python
class UserResource(Resource):
    def to_array(self, request=None):
        user = self.resource
        return {
            "id": user.get_attribute("id"),
            "name": user.get_attribute("name"),
            "email": self.when(self.is_owner(request), user.get_attribute("email")),
        }

    def is_owner(self, request):
        current = request.user() if request else None
        return current and current.get_attribute("id") == self.resource.get_attribute("id")
```

`when(condition, value, default=None)` returns `value` when the condition holds
and `default` otherwise. Pass a callable to defer the work.

## Nesting

```python
class PostResource(Resource):
    def to_array(self, request=None):
        post = self.resource
        return {
            "id": post.get_attribute("id"),
            "title": post.get_attribute("title"),
            "author": UserResource(post.author().first()).to_array(request),
            "comments": CommentResource.collection(post.comments().get()).to_array(request),
        }
```

Eager load first, or you have reintroduced N+1 one level down:

```python
posts = Post.with_("author", "comments").get()
```

See [ORM](orm.md#eager-loading).

## Resources and hidden attributes

`Model.hidden` covers `to_dict()`, which is the model's own serialisation. A
Resource is a separate, explicit list — it does not inherit `hidden`. For a
public API, prefer the Resource: an allow-list of what goes out is safer than a
deny-list of what stays in.

```python
class User(Model):
    hidden = ["password", "remember_token"]
```
