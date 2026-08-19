"""Application bootstrap — creates and boots the Craft application."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import engine  # noqa: F401  installs the `craft.*` import alias


from craft.container.application import Application
from craft.facades.base import Facade


def create_app() -> Application:
    """Create and bootstrap the Craft application."""
    app = Application(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load config
    app.register_config()

    # Register framework service providers
    from craft.providers.service_providers import (
        DatabaseServiceProvider,
        RouterServiceProvider,
        ViewServiceProvider,
        AuthServiceProvider,
        EventServiceProvider,
        QueueServiceProvider,
        LoggingServiceProvider,
        CacheServiceProvider,
        MigratorServiceProvider,
        ExceptionServiceProvider,
        PQCServiceProvider,
        CaptchaServiceProvider,
        FirewallServiceProvider,
        HoneypotServiceProvider,
        MediaServiceProvider,
        FrameworkSubsystemsServiceProvider,
    )

    app.register_provider(DatabaseServiceProvider)
    app.register_provider(RouterServiceProvider)
    app.register_provider(ViewServiceProvider)
    app.register_provider(AuthServiceProvider)
    app.register_provider(EventServiceProvider)
    app.register_provider(QueueServiceProvider)
    app.register_provider(LoggingServiceProvider)
    app.register_provider(CacheServiceProvider)
    app.register_provider(MigratorServiceProvider)
    app.register_provider(ExceptionServiceProvider)
    app.register_provider(FirewallServiceProvider)
    app.register_provider(HoneypotServiceProvider)
    app.register_provider(MediaServiceProvider)

    # `config/framework.py` ships these as feature flags, but nothing read
    # them: both providers registered unconditionally, so setting
    # PQC_SECURITY_ENABLED=false or CAPTCHA_ENABLED=false changed nothing. A
    # switch that does not switch is worse than no switch.
    config = app.make("config")
    if config.get("framework.PQC_SECURITY_ENABLED", True):
        app.register_provider(PQCServiceProvider)
    if config.get("framework.CAPTCHA_ENABLED", True):
        app.register_provider(CaptchaServiceProvider)


    app.register_provider(FrameworkSubsystemsServiceProvider)

    # Register application service providers
    from app.Providers.AppServiceProvider import AppServiceProvider
    from app.Providers.AuthServiceProvider import AuthServiceProvider as AppAuthServiceProvider
    from app.Providers.EventServiceProvider import EventServiceProvider as AppEventServiceProvider
    from app.Providers.PanelServiceProvider import PanelServiceProvider
    from app.Providers.RouteServiceProvider import RouteServiceProvider

    app.register_provider(AppServiceProvider)
    app.register_provider(AppAuthServiceProvider)
    app.register_provider(AppEventServiceProvider)
    # Declares the control panel's menu. Registered after the auth provider
    # because every menu item is guarded by the same roles, permissions and
    # groups the routes are, resolved through the `access` binding.
    app.register_provider(PanelServiceProvider)
    app.register_provider(RouteServiceProvider)

    # Wire facades to the app before booting providers
    Facade._app = app

    # Boot all providers
    app.boot()

    return app


# Create the app instance
app = create_app()

# Build the ASGI application
from craft.http.kernel import Kernel
from app.Http.Middleware.DatabaseLoggingMiddleware import DatabaseLoggingMiddleware
from app.Http.Middleware.TenantMiddleware import TenantMiddleware

from craft.http.middleware import (
    Authenticate,
    SecurityHeaders,
    SetLocale,
    StartSession,
    VerifyCsrfToken,
)

kernel = Kernel(app)

# Order matters: the session must exist before the locale can be remembered in
# it, before CSRF verification, and before the user is resolved from it.
# SecurityHeaders goes first so every response — including error responses
# rendered inside StartSession — carries the baseline headers.
_global_middleware = [
    SecurityHeaders,
    StartSession,
    SetLocale,
    VerifyCsrfToken,
    Authenticate,
    DatabaseLoggingMiddleware,
]

# `MULTI_TENANCY_ENABLED` used to be decorative: TenantMiddleware ran on every
# request whatever the flag said. A single-tenant app now stops paying for the
# per-request tenant resolution it never wanted.
if app.make("config").get("framework.MULTI_TENANCY_ENABLED", True):
    _global_middleware.append(TenantMiddleware)

kernel.with_middleware(*_global_middleware)

asgi_app = kernel.get_starlette_app()
