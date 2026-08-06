# Sessions

Sessions are loaded before your code runs and saved after it returns, by the
`StartSession` middleware. Both drivers sign the cookie with `APP_KEY`, so a
tampered cookie is rejected rather than trusted.

## Drivers

| Driver | Where the payload lives | Trade-off |
|---|---|---|
| `cookie` | In the signed cookie | No storage to set up; capped by cookie size, and **readable by the client** |
| `file` | `storage/framework/sessions` | Server-side invalidation; only a signed id travels |

```ini
SESSION_DRIVER=cookie
SESSION_LIFETIME=7200
SESSION_COOKIE=codepy_session
SESSION_SAME_SITE=lax
SESSION_SECURE_COOKIE=false
```

> **Signed is not encrypted.** Under the `cookie` driver the payload is
> base64-encoded JSON. The client cannot change it — the signature would fail —
> but it can read it. Keep secrets out of the session, or use the `file` driver.

## Using the session

```python
def show(self, request):
    session = request.session()

    session.put("cart", [1, 2, 3])
    session.get("cart", [])
    session.has("cart")           # present and not None
    session.exists("cart")        # present, even if None
    session.forget("cart")
    session.pull("cart")          # read then remove
    session.all()                 # everything except internal keys
```

Dictionary access works too:

```python
session["cart"] = [1, 2]
"cart" in session
```

## Flash data

A flashed value is readable on the **next** request and then dropped — the usual
way to carry a message across a redirect:

```python
def store(self, request):
    request.session().flash("status", "Post created.")
    return self.redirect(route="posts.index")
```

```html
@if(session('status'))
    <div class="alert">{{ session('status') }}</div>
@endif
```

Keep it one request longer:

```python
request.session().reflash()
```

## CSRF tokens

Every session carries a token, created on first use:

```python
request.session().token()
request.session().regenerate_token()
```

In templates, `@csrf` renders the hidden field. See [Security](security.md).

## Session lifecycle

```python
session.regenerate()   # new id, same data — run this on login
session.invalidate()   # new id, no data, new token — run this on logout
session.flush()        # clear data, keep the session and its CSRF token
```

`Auth.login()` calls `regenerate()` for you, which closes session fixation: a
session id fixed before login stops being valid afterwards.

## Reaching the session outside a request

View helpers use a context variable that `StartSession` publishes:

```python
from codepy.http.session import get_current_session

session = get_current_session()   # None outside a request
```

Prefer `request.session()` where you have the request.

## Authentication state

`Authenticate` middleware rehydrates the user from the session on each request.
The manager holds no state between requests:

```python
auth = app.make("auth")
auth.reset()    # clear this request's user, keep the session
auth.logout()   # clear the user and forget it from the session
```

That distinction matters — `logout()` inside middleware would erase the key it
is about to read.

## File driver maintenance

Expired files are removed on read, and you can sweep them:

```python
from codepy.http.session import FileSessionStore

store = FileSessionStore(app_key, "storage/framework/sessions")
store.gc()                 # delete expired files, returns how many
store.destroy(session_id)  # invalidate one session server-side
```

Session ids are hashed before use as filenames, so a crafted id cannot escape
the directory.

## Testing

```python
from starlette.testclient import TestClient

client = TestClient(asgi_app)
client.get("/counter")          # cookie issued
client.get("/counter")          # same session

other = TestClient(asgi_app)    # a separate session
```
