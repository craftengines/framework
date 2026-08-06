"""Global Framework Configurations and Features Defaults."""

from codepy.config import env

FRAMEWORK_NAME = "Codepy"
FRAMEWORK_VERSION = env("APP_VERSION", "v3.11")
FRAMEWORK_RELEASE = env("APP_RELEASE", "r00002")

# Global feature flags
MULTI_TENANCY_ENABLED = env("MULTI_TENANCY_ENABLED", True)
PQC_SECURITY_ENABLED = env("PQC_SECURITY_ENABLED", True)
CAPTCHA_ENABLED = env("CAPTCHA_ENABLED", True)

# Default locale & timezone
DEFAULT_LOCALE = env("APP_LOCALE", "en")
SUPPORTED_LOCALES = ["en", "pt", "es"]
