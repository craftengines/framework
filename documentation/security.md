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

## Post-Quantum Cryptography (PQC) Signatures

To guard sessions against post-quantum decrypt-and-harvest attacks, Codepy supports Post-Quantum Cryptography session cookie signatures via a hybrid Winternitz signature scheme.

The framework automatically hashes and signs cookie payloads utilizing `pqc` facades when session serialization occurs, ensuring cookies cannot be read or manipulated under standard or post-quantum compute environments.

---

## Captcha Integration

Inject security challenge-response captures using the Captcha plugin:

```python
from codepy.facades import Captcha

# Generate a captcha validation image/token layout
captcha_data = Captcha.generate()

# Validate the user's captcha text input
if not Captcha.validate(user_input_text, original_token):
    return response("Invalid Captcha Challenge", status=400)
```
