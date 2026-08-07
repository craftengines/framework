"""Application configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
from craft.config import env

APP_NAME = env("APP_NAME", "Craft")
APP_ENV = env("APP_ENV", "local")
APP_DEBUG = env("APP_DEBUG", True)
APP_URL = env("APP_URL", "http://localhost:8000")
APP_KEY = env("APP_KEY", "")
APP_LOCALE = env("APP_LOCALE", "en")
APP_FALLBACK_LOCALE = env("APP_FALLBACK_LOCALE", "en")
APP_TIMEZONE = env("APP_TIMEZONE", "UTC")
# The framework's own version, from the package — it used to be hardcoded to
# "v3.11", which is the minimum Python version, not a release of Craft.
from services import __version__ as APP_VERSION  # noqa: E402

#: Locales offered by the language switcher, most specific first.
APP_LOCALES = ["en", "pt", "pt-BR", "es"]

version = APP_VERSION
