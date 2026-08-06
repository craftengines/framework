"""Application configuration."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
from codepy.config import env

APP_NAME = env("APP_NAME", "Codepy")
APP_ENV = env("APP_ENV", "local")
APP_DEBUG = env("APP_DEBUG", True)
APP_URL = env("APP_URL", "http://localhost:8000")
APP_KEY = env("APP_KEY", "")
APP_LOCALE = env("APP_LOCALE", "en")
APP_FALLBACK_LOCALE = env("APP_FALLBACK_LOCALE", "en")
APP_TIMEZONE = env("APP_TIMEZONE", "UTC")
APP_VERSION = env("APP_VERSION", "v3.11")
APP_RELEASE = env("APP_RELEASE", "r00002")
version = APP_VERSION
release = APP_RELEASE
