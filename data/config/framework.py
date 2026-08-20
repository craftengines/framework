"""Global Framework Configurations and Features Defaults."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

FRAMEWORK_NAME = "Craft"

# Sourced from the package rather than hand-maintained here: these were literal
# strings that had already drifted from `engine/__init__.py` (claiming r00002
# against the package's r00001), so whichever one you read told you something
# different. Use `config('app.version')` / `config('app.release')`.
from craft import __release__ as FRAMEWORK_RELEASE  # noqa: E402
from craft import __version__ as FRAMEWORK_VERSION  # noqa: E402

# Global feature flags

# Off by default, and deliberately so. Multi-tenancy is an architectural
# decision with a cost — a tenant bound on every request, an isolation policy
# on every table, and a database that can actually enforce one — and it is not
# something an application should acquire by accident.
#
# The default used to be on, which made the out-of-the-box experience depend on
# the driver: a personal single-tenant app on SQLite worked only for as long as
# nobody signed in as the seeded `type = "tenant"` user, at which point the
# request was refused because SQLite cannot isolate anything. Turning it on is
# now the deliberate act, and the refusal that follows on a driver without
# isolation is then exactly right rather than a surprise.
#
# Set MULTI_TENANCY_ENABLED=true with PostgreSQL to build a tenanted product;
# see documentation/postgres.md for the two strategies and the database role
# the row-level-security one requires.
MULTI_TENANCY_ENABLED = env("MULTI_TENANCY_ENABLED", False)
PQC_SECURITY_ENABLED = env("PQC_SECURITY_ENABLED", True)
CAPTCHA_ENABLED = env("CAPTCHA_ENABLED", True)

# Default locale & timezone
DEFAULT_LOCALE = env("APP_LOCALE", "en")
SUPPORTED_LOCALES = ["en", "pt", "es"]
