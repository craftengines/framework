"""App service provider — register application-level bindings."""

from codepy.providers import ServiceProvider


class AppServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        pass
