# Authentication & Security

Codepy contains modular authentication and authorization components mapped to clean, static facade accessors. It also features modern security layers, such as Post-Quantum Cryptography (PQC) session signatures and CAPTCHA integrations.

---

## Authentication (Auth Facade)

Use the `Auth` facade to authenticate user credentials and query the current session state:

```python
from codepy.facades import Auth

# Attempt authentication using login attributes
if Auth.attempt({"email": "user@codepy.io", "password": "securepassword"}):
    # Retrieve current authenticated User model instance
    user = Auth.user()
    print(f"Authenticated as {user.name}")

# Check if a user session is active
if Auth.check():
    # Logout current user session
    Auth.logout()
```

---

## User Roles & Types

Codepy supports three user roles/types out-of-the-box:
1. **User (`user`)**: A standard user account.
2. **Admin (`admin`)**: A system administrator account with full administrative credentials.
3. **Tenant (`tenant`)**: A tenant account representing an isolated workspace/SaaS client.

### Role Check Helpers
The `User` model exposes convenient boolean properties for checking the active user type:

```python
user = Auth.user()

if user.is_admin_user:
    # Perform administrator actions
    pass

if user.is_tenant_user:
    # Perform tenant actions
    pass

if user.is_standard_user:
    # Perform standard user actions
    pass
```

---

## Authorization & Gates (Gate Facade)

Authorization checks allow or deny requests based on user permissions.

### Defining Gates
Gates are closure callbacks mapped to action permissions (typically declared inside `AppServiceProvider` or a dedicated provider):

```python
from codepy.facades import Gate

# Define a gate rule
Gate.define("publish-posts", lambda user: user.role == "editor" or user.is_admin)

# Check the gate permissions in a controller
if not Gate.allows("publish-posts"):
    return response("Unauthorized", status=403)
```

---

## Authorization Policies

Policies organize authorization checks around specific models.

### Example Policy
```python
class PostPolicy:
    def update(self, user, post) -> bool:
        # User can update a post only if they own it
        return user.id == post.user_id

    def delete(self, user, post) -> bool:
        return user.is_admin or user.id == post.user_id
```

### Registering & Checking Policies
```python
from app.Models.Post import Post

# Register Policy mapping (usually inside AuthServiceProvider)
Gate.policy(Post, PostPolicy)

# Check policy permissions in a controller action
post = await Post.find("post-uuid")
if not Gate.check("update", user, post):
    return response("Forbidden", status=403)
```

---

## Sessions and CSRF

Sessions are signed with **HMAC-SHA256** using `APP_KEY`. A cookie that was
tampered with, or signed with a different key, is rejected rather than trusted.

> **Signed is not encrypted.** With `SESSION_DRIVER=cookie` the payload is
> base64-encoded JSON in the cookie — the client cannot *change* it, but can
> *read* it. Do not put secrets in the session under that driver. Use
> `SESSION_DRIVER=file`, which keeps the payload on the server and puts only a
> signed id in the cookie.

CSRF is verified on POST/PUT/PATCH/DELETE, via the `_token` field or the
`X-CSRF-TOKEN` header. Routes matching `api/*` are exempt. A mismatch returns
**419**.

```html
<form method="POST" action="/posts">
    @csrf
    <input name="title">
</form>
```

## Post-Quantum Cryptography (PQC)

Codepy ships a hybrid Winternitz (WOTS) signature utility for signing tokens
where post-quantum resistance matters:

```python
from codepy.facades import PQC

token = PQC.sign_token(payload, secret_key, seed)
PQC.verify_token(token, secret_key, public_key)
```

It is a standalone utility — **session cookies use HMAC-SHA256, not WOTS**. Wire
PQC in explicitly where you need it.

---

## Captcha Integration

A short alphanumeric challenge held in the session. Both calls take the request —
the code lives in the session, not in a token you pass around.

```python
from codepy.facades import Captcha

# In the GET handler: generate and render the challenge
code = Captcha.generate(request)
html = Captcha.get_obfuscated_html(code)

# In the POST handler: validate what the user typed
if not Captcha.validate(request, request.input("captcha")):
    return response("Invalid Captcha Challenge", status=400)
```

The stored code is cleared on every validation attempt, whether or not it
succeeded — a captcha is single-use, otherwise one challenge can be brute-forced.
