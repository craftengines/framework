"""Session configuration."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.config import env

#: "cookie" keeps the payload in a signed cookie; "file" keeps it under
#: storage/framework/sessions and puts only a signed id in the cookie.
driver = env("SESSION_DRIVER", "cookie")

#: Seconds a session stays valid.
lifetime = env("SESSION_LIFETIME", 7200)

cookie = env("SESSION_COOKIE", "codepy_session")

#: Send the cookie only over HTTPS. Turn this on in production.
secure = env("SESSION_SECURE_COOKIE", False)

#: "lax" blocks the cookie on cross-site POSTs while keeping normal links working.
same_site = env("SESSION_SAME_SITE", "lax")

#: Master switch for CSRF verification. Only turn this off for a stateless API.
csrf = env("SESSION_CSRF", True)
