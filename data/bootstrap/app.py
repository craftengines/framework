"""Application bootstrap — creates and boots the Craft application."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import services


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
    app.register_provider(PQCServiceProvider)
    app.register_provider(CaptchaServiceProvider)
    app.register_provider(FrameworkSubsystemsServiceProvider)

    # Register application service providers
    from app.Providers.AppServiceProvider import AppServiceProvider
    from app.Providers.AuthServiceProvider import AuthServiceProvider as AppAuthServiceProvider
    from app.Providers.EventServiceProvider import EventServiceProvider as AppEventServiceProvider
    from app.Providers.RouteServiceProvider import RouteServiceProvider

    app.register_provider(AppServiceProvider)
    app.register_provider(AppAuthServiceProvider)
    app.register_provider(AppEventServiceProvider)
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
kernel.with_middleware(
    SecurityHeaders,
    StartSession,
    SetLocale,
    VerifyCsrfToken,
    Authenticate,
    DatabaseLoggingMiddleware,
    TenantMiddleware,
)

asgi_app = kernel.get_starlette_app()
