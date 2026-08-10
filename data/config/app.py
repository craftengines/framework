"""Application configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
from craft.config import env

APP_NAME = env("APP_NAME", "Craft")
APP_ENV = env("APP_ENV", "local")
# Debug must be opted into (.env sets it) — defaulting on leaks stack traces
# in production.
APP_DEBUG = env("APP_DEBUG", False)
APP_URL = env("APP_URL", "http://localhost:8000")
APP_KEY = env("APP_KEY", "")
APP_LOCALE = env("APP_LOCALE", "en")
APP_FALLBACK_LOCALE = env("APP_FALLBACK_LOCALE", "en")
# NOTE: there is deliberately no APP_TIMEZONE here. Craft writes every
# timestamp in UTC (`engine/orm/model.py`, `soft_deletes.py`, `queue/`), and
# nothing in the framework ever read the setting — changing it did nothing at
# all. A display-timezone feature can reintroduce it once something honours it.
# The framework's own version, from the package — it used to be hardcoded to
# "v3.11", which is the minimum Python version, not a release of Craft.
from craft import __release__ as APP_RELEASE  # noqa: E402
from craft import __version__ as APP_VERSION  # noqa: E402

#: Locales offered by the language switcher, most specific first.
APP_LOCALES = ["en", "pt", "pt-BR", "es"]

version = APP_VERSION

#: `config('app.release')` is read by the layout footer and the version badge.
#: It had no declaration at all, so both rendered blank; and `config/framework.py`
#: carried a second, hand-maintained copy that had already drifted out of step
#: with the package. The package is the single source of truth.
release = APP_RELEASE
