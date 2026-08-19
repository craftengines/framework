# Mail & Notification Subsystem

Craft Engine provides a fluent, driver-agnostic email and notification delivery system.

## 🚀 Sending Emails

### 1. Fluent One-Liner / Raw Email
```python
from craft.facades import Mail

# Send simple plain text email
Mail.raw("Your verification code is 481920", to="user@example.com", subject="Verify Account")

# Fluent chain
Mail.to("user@example.com").cc("manager@example.com").raw("Meeting rescheduled to 3 PM", subject="Meeting Update")
```

---

### 2. Template-Driven Mailable Class
Create a declarative `Mailable` subclass:

```python
# app/Mail/WelcomeUserMailable.py
from craft.mail.mailable import Mailable

class WelcomeUserMailable(Mailable):
    subject = "Welcome to our Platform!"

    def __init__(self, user):
        super().__init__()
        self.user = user

    def build(self):
        return self.view("emails.welcome", {"user": self.user})
```

Dispatch it easily:
```python
from craft.facades import Mail
from app.Mail.WelcomeUserMailable import WelcomeUserMailable

Mail.to(user.email).send(WelcomeUserMailable(user))
```

---

## 🛠️ Transports (`smtp`, `log`, `array`)
Configured in `config/mail.py`:
- `smtp`: Standard production SMTP delivery with TLS/SSL authentication.
- `log`: Writes outgoing emails to the application logger (`storage/logs/craft.log`).
- `array`: In-memory driver for rapid, deterministic testing (`Mail.set_default_mailer('array')`).
