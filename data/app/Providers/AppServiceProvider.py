"""App service provider — register application-level bindings."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.providers import ServiceProvider


class AppServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        pass
