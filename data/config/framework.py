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
MULTI_TENANCY_ENABLED = env("MULTI_TENANCY_ENABLED", True)
PQC_SECURITY_ENABLED = env("PQC_SECURITY_ENABLED", True)
CAPTCHA_ENABLED = env("CAPTCHA_ENABLED", True)

# Default locale & timezone
DEFAULT_LOCALE = env("APP_LOCALE", "en")
SUPPORTED_LOCALES = ["en", "pt", "es"]
