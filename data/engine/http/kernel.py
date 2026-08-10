"""
Kernel — Builds the Starlette ASGI app: mounts the router, static files, and
runs each request through the registered middleware stack.
Category: Core Framework (HTTP).
Relations:
  - Built once in `bootstrap/app.py`; consumes `engine/http/router.py` and
    `engine/http/middleware.py`.
References:
  - Guide: `documentation/routing.md`, `documentation/deployment.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import inspect
import os
from typing import Any, List, Optional
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse, HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route as StarletteRoute, Mount
from starlette.staticfiles import StaticFiles


def render_exception(app: Any, request: Any, exc: Exception) -> StarletteResponse:
    """Turn an exception into a response via the registered handler.

    Shared by the kernel's outer catch and by middleware (StartSession) that
    needs to materialise an exception-driven response early enough to still
    attach the session cookie to it.
    """
    status = getattr(exc, "status_code", None)
    headers = getattr(exc, "headers", None)
    if status in (301, 302, 303, 307, 308) and headers and "location" in headers:
        return RedirectResponse(headers["location"], status_code=status)

    try:
        handler = app.make("exception_handler")
    except Exception:
        handler = None

    if handler is not None and hasattr(handler, "render"):
        wants_json = getattr(request, "expects_json", lambda: True)()
        return handler.render(exc, wants_json=wants_json)

    return JSONResponse({"error": str(exc)}, status_code=status or 500)


class DynamicStarletteApp:
    def __init__(self, kernel: 'Kernel'):
        self.kernel = kernel
        self._app: Optional[Starlette] = None
        self._version: Any = None

    #: Verbs a browser cannot send from a form, and so may be spoofed.
    SPOOFABLE_METHODS = ("PUT", "PATCH", "DELETE")

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        # Rebuild only when the route table changed — rebuilding the whole
        # Starlette app per request was pure waste.
        router = self.kernel.app.make("router")
        version = getattr(router, "_version", None)
        if version is None:
            version = len(router.routes)
        if self._app is None or self._version != version:
            self._app = self.kernel._build_starlette_app()
            self._version = version

        scope, receive = await self._apply_method_override(scope, receive)
        await self._app(scope, receive, send)

    async def _apply_method_override(self, scope: Any, receive: Any):
        """Honour a `_method` form field, before Starlette routes the request.

        HTML forms can only issue GET and POST, so the framework emits a hidden
        `_method` input — the `@method("PUT")` view directive and every
        edit/delete form the CRUD builder generates rely on it. Nothing ever
        read it back: the browser sent POST, `Route.resource()` had registered
        the route under PUT/DELETE, and the request 405'd. The directive
        produced decorative HTML and generated admin forms simply did not work.

        This has to happen at the ASGI layer: Starlette matches on the method
        before any endpoint or middleware of ours runs, so rewriting it later
        is already too late.
        """
        if scope.get("type") != "http" or scope.get("method") != "POST":
            return scope, receive

        content_type = b""
        for header, value in scope.get("headers", []):
            if header == b"content-type":
                content_type = value
                break
        if not content_type.startswith((b"application/x-www-form-urlencoded", b"multipart/form-data")):
            return scope, receive

        # The body can only be consumed once, so buffer it and hand the app a
        # receive channel that replays exactly what we read.
        body = b""
        messages = []
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break

        override = self._extract_method(body, content_type)
        if override in self.SPOOFABLE_METHODS:
            scope = dict(scope)
            scope["method"] = override

        replay = iter(messages)

        async def replaying_receive():
            try:
                return next(replay)
            except StopIteration:
                return await receive()

        return scope, replaying_receive

    @staticmethod
    def _extract_method(body: bytes, content_type: bytes) -> Optional[str]:
        import re
        from urllib.parse import parse_qs

        try:
            if content_type.startswith(b"application/x-www-form-urlencoded"):
                values = parse_qs(body.decode("latin-1")).get("_method")
                return values[0].upper() if values else None

            # Multipart: a targeted scan beats parsing the whole payload, which
            # may carry file uploads we have no reason to buffer twice.
            match = re.search(
                rb'name="_method"\r?\n\r?\n([A-Za-z]+)', body
            )
            return match.group(1).decode("latin-1").upper() if match else None
        except Exception:
            return None


class Kernel:
    """HTTP Kernel wrapping Starlette app with Craft pipeline dispatching."""

    def __init__(self, app: Any):
        self.app = app
        self.middleware_classes: List[Any] = []
        self._middleware: Optional[List[Any]] = None
        self._aliases: dict = {}

    def with_middleware(self, *middleware) -> 'Kernel':
        self.middleware_classes.extend(middleware)
        self._middleware = None  # rebuild the stack on next request
        return self

    def middleware(self) -> List[Any]:
        """Middleware instances, built once and reused.

        Building them per request was a correctness bug, not just waste: a
        middleware that caches anything — the session store and its signing key,
        for one — got a fresh copy every time, so nothing survived a request.
        """
        if self._middleware is None:
            self._middleware = [self._instantiate(cls) for cls in self.middleware_classes]
        return self._middleware

    #: Short names usable in `Route.get(...).middleware("auth")`.
    def route_middleware_aliases(self) -> dict:
        from engine.http import middleware as mw

        return {
            "auth": mw.RequireAuth,
            "api": mw.AuthenticateApiToken,
            "session": mw.StartSession,
            "csrf": mw.VerifyCsrfToken,
            "throttle": mw.ThrottleRequests,
            "role": mw.RequireRole,
            "permission": mw.RequirePermission,
            "group": mw.RequireGroup,
        }

    def alias_middleware(self, name: str, middleware_class: Any) -> "Kernel":
        """Register an extra route-middleware alias."""
        self._aliases[name] = middleware_class
        return self

    def resolve_route_middleware(self, entries: List[Any]) -> List[Any]:
        """Turn a route's middleware list into instances.

        Accepts alias strings and classes. Aliases may carry a parameter after
        a colon — `"role:admin"` / `"permission:manage-users"` — which is
        passed as the first positional argument to the resolved middleware
        class (e.g. `RequireRole(role="admin")`). Unknown aliases raise rather
        than being skipped — a route that declares protection which silently
        does nothing is worse than one that fails loudly at boot.
        """
        aliases = {**self.route_middleware_aliases(), **self._aliases}
        resolved = []
        for entry in entries or []:
            if isinstance(entry, str):
                if entry in aliases:
                    # Some aliases (`role`, `permission`) are only meaningful
                    # with a `:param` — a bare use is a caller mistake, not a
                    # silently-do-nothing middleware, so it must still raise.
                    try:
                        resolved.append(self._instantiate(aliases[entry]))
                        continue
                    except TypeError:
                        raise KeyError(
                            f"Route middleware [{entry}] requires a parameter — "
                            f"use '{entry}:<value>' (e.g. '{entry}:admin')."
                        ) from None

                base_alias, _, param = entry.partition(":")
                if param and base_alias in aliases:
                    resolved.append(self._instantiate(aliases[base_alias], param))
                    continue

                raise KeyError(
                    f"Unknown route middleware [{entry}]. Register it with "
                    f"kernel.alias_middleware('{entry}', SomeMiddleware)."
                )
            elif isinstance(entry, type):
                resolved.append(self._instantiate(entry))
            else:
                resolved.append(entry)
        return resolved

    def _build_starlette_app(self) -> Starlette:
        router = self.app.make("router")
        routes = []

        for r in router.routes:
            endpoint = self._create_endpoint(r.action, r._module, r.middleware_list)
            for m in r.methods:
                routes.append(StarletteRoute(r.uri, endpoint=endpoint, methods=[m]))

        # Serve static files (CSS, JS, images) from the public/ directory.
        public_dir = os.path.join(self.app.base_path, "public")
        if os.path.isdir(public_dir):
            routes.append(
                Mount("/", app=StaticFiles(directory=public_dir), name="static")
            )

        # Never hardcode debug — it leaks stack traces to clients in production.
        try:
            debug = bool(self.app.make("config").get("app.APP_DEBUG", False))
        except Exception:
            debug = False

        return Starlette(debug=debug, routes=routes)

    def get_starlette_app(self) -> DynamicStarletteApp:
        return DynamicStarletteApp(self)

    def _instantiate(self, mw_cls: Any, param: Optional[str] = None) -> Any:
        """Build a middleware, passing the app and an alias parameter when accepted."""
        try:
            signature = inspect.signature(mw_cls.__init__)
        except (TypeError, ValueError):
            return mw_cls()

        kwargs = {}
        if "app" in signature.parameters:
            kwargs["app"] = self.app

        if param is not None:
            # First declared parameter after `self`/`app` receives the value
            # from the `alias:param` route middleware string.
            positional = [
                name
                for name in signature.parameters
                if name not in ("self", "app")
            ]
            if positional:
                kwargs[positional[0]] = param

        return mw_cls(**kwargs)

    def _create_endpoint(
        self,
        action: Any,
        module_name: Optional[str] = None,
        route_middleware: Optional[List[Any]] = None,
    ) -> Any:
        route_stack = self.resolve_route_middleware(route_middleware or [])

        async def endpoint(request: StarletteRequest) -> StarletteResponse:
            # Middleware and controllers are synchronous, so the body has to be
            # read here — they cannot await `request.form()` themselves.
            from engine.http.request import from_starlette

            request = await from_starlette(request).prepare()

            if module_name:
                # Ask the ModuleManager rather than issuing a SELECT here: it is
                # the single source of truth for module state and it caches the
                # answer, so a module-scoped route no longer costs a query per
                # request. A module the manager has never heard of (`None`)
                # falls back to config, which defaults to enabled.
                state = None
                try:
                    state = self.app.make("module").state(module_name)
                except Exception:
                    state = None

                if state is None:
                    config = self.app.make("config")
                    enabled = bool(config.get(f"modules.{module_name}.enabled", True))
                else:
                    enabled = state

                if not enabled:
                    return JSONResponse({"error": "Module Disabled"}, status_code=404)

            def handle_action(req):
                if isinstance(action, list):
                    controller_cls, method_name = action[0], action[1]
                    controller_inst = self.app.make(controller_cls) if isinstance(controller_cls, type) else controller_cls()
                    method = getattr(controller_inst, method_name)

                    path_params = dict(req.path_params)
                    kwargs = {"request": req}
                    kwargs.update(path_params)

                    sig = inspect.signature(method)
                    call_kwargs = {}
                    for param_name in sig.parameters.keys():
                        if param_name in kwargs:
                            call_kwargs[param_name] = kwargs[param_name]
                        elif param_name == "request":
                            call_kwargs["request"] = req

                    result = method(**call_kwargs)
                elif callable(action):
                    sig = inspect.signature(action)
                    if len(sig.parameters) == 0:
                        result = action()
                    else:
                        result = action(req)
                else:
                    result = action

                if inspect.iscoroutine(result):
                    # Async controller action. The middleware chain is
                    # synchronous and already running on the event loop, so run
                    # the coroutine to completion on its own loop in a worker
                    # thread instead of returning str(coroutine).
                    import asyncio
                    from concurrent.futures import ThreadPoolExecutor

                    with ThreadPoolExecutor(max_workers=1) as pool:
                        result = pool.submit(asyncio.run, result).result()

                if hasattr(result, "to_starlette"):
                    return result.to_starlette()
                if isinstance(result, StarletteResponse):
                    return result
                if isinstance(result, (dict, list)):
                    return JSONResponse(result)
                return HTMLResponse(str(result))

            # Route middleware runs inside the global stack, so it can rely on
            # the session and resolved user that the global stack sets up.
            current_call = handle_action
            for mw_inst in reversed(self.middleware() + route_stack):
                prev_call = current_call
                current_call = lambda req, inst=mw_inst, next_fn=prev_call: inst.handle(req, next_fn)

            # The whole middleware + controller chain is synchronous and every
            # ORM call blocks. Running it inline blocked the event loop for the
            # duration of the request, so the process served exactly one at a
            # time — the measured ~30 req/s ceiling, flat from 1 to 100 clients.
            # Offloading to the thread pool is only safe because the connection
            # layer now keeps one session per thread, and because the auth
            # manager's per-request state is thread-local; without those, two
            # requests would share a cursor and an identity.
            def serve(req):
                try:
                    return current_call(req)
                finally:
                    # End of the request on this thread: give the pooled
                    # connection back. Inside the worker thread, because that is
                    # the thread that borrowed it.
                    try:
                        self.app.make("db").release()
                    except Exception:
                        pass

            try:
                return await run_in_threadpool(serve, request)
            except Exception as exc:
                return self._render_exception(request, exc)

        return endpoint

    def _render_exception(self, request: Any, exc: Exception) -> StarletteResponse:
        """Turn an exception into a response via the registered handler."""
        return render_exception(self.app, request, exc)
