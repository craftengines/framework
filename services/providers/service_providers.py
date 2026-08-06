"""Framework Service Providers for Codepy Framework."""

from services.providers.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    def register(self):
        from services.orm.db import DatabaseManager
        from services.migrations.schema import SchemaBuilder

        db_mgr = DatabaseManager(self.app)
        self.app.instance("db", db_mgr)
        self.app.instance("schema", SchemaBuilder(db_mgr))

    def boot(self):
        self.app.make("db").boot()


class RouterServiceProvider(ServiceProvider):
    def register(self):
        from services.http.router import Router
        self.app.singleton("router", lambda c: Router(c))


class ViewServiceProvider(ServiceProvider):
    def register(self):
        from services.view.forge import Forge
        self.app.singleton("view", lambda c: Forge(c))


class AuthServiceProvider(ServiceProvider):
    def register(self):
        from services.auth.gate import GateManager
        from services.auth.manager import AuthManager
        from services.auth.password import Hash

        self.app.instance("auth", AuthManager(self.app))
        self.app.instance("gate", GateManager())
        self.app.instance("hash", Hash())


class EventServiceProvider(ServiceProvider):
    def register(self):
        from services.events.dispatcher import EventDispatcher
        self.app.singleton("events", lambda c: EventDispatcher())


class QueueServiceProvider(ServiceProvider):
    def register(self):
        from services.queue.manager import QueueManager
        self.app.singleton("queue", lambda c: QueueManager(c))


class LoggingServiceProvider(ServiceProvider):
    def register(self):
        import logging
        self.app.singleton("log", lambda c: logging.getLogger("codepy"))


class CacheServiceProvider(ServiceProvider):
    def register(self):
        from services.cache.manager import CacheManager
        self.app.instance("cache", CacheManager(self.app))


class MigratorServiceProvider(ServiceProvider):
    def register(self):
        from services.migrations.migrator import Migrator
        self.app.instance("migrator", Migrator(self.app))


class ExceptionServiceProvider(ServiceProvider):
    def register(self):
        from services.exceptions.handler import ExceptionHandler
        self.app.instance("exception_handler", ExceptionHandler(self.app))


class PQCServiceProvider(ServiceProvider):
    def register(self):
        from services.security.pqc import PQC
        self.app.singleton("pqc", lambda c: PQC())


class CaptchaServiceProvider(ServiceProvider):
    def register(self):
        from services.security.captcha import Captcha
        self.app.singleton("captcha", lambda c: Captcha())


class FrameworkSubsystemsServiceProvider(ServiceProvider):
    def register(self):
        from services.modules.manager import ModuleManager
        from services.plugins.manager import PluginManager
        from services.support.settings import SettingManager

        class ScheduleManager:
            def command(self, cmd):
                class Entry:
                    def hourly(self): return self
                    def daily(self): return self
                return Entry()

        self.app.singleton("module", lambda c: ModuleManager())
        self.app.singleton("plugin", lambda c: PluginManager())
        self.app.singleton("setting", lambda c: SettingManager())
        self.app.singleton("schedule", lambda c: ScheduleManager())
