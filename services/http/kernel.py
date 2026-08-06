"""HTTP Kernel for Codepy Framework."""

import inspect
from typing import Any, List, Optional
from starlette.applications import Starlette
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse, HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route as StarletteRoute


class DynamicStarletteApp:
    def __init__(self, kernel: 'Kernel'):
        self.kernel = kernel

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        starlette_app = self.kernel._build_starlette_app()
        await starlette_app(scope, receive, send)


class Kernel:
    """HTTP Kernel wrapping Starlette app with Codepy pipeline dispatching."""

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
        from services.http import middleware as mw

        return {
            "auth": mw.RequireAuth,
            "api": mw.AuthenticateApiToken,
            "session": mw.StartSession,
            "csrf": mw.VerifyCsrfToken,
        }

    def alias_middleware(self, name: str, middleware_class: Any) -> "Kernel":
        """Register an extra route-middleware alias."""
        self._aliases[name] = middleware_class
        return self

    def resolve_route_middleware(self, entries: List[Any]) -> List[Any]:
        """Turn a route's middleware list into instances.

        Accepts alias strings and classes. Unknown aliases raise rather than
        being skipped — a route that declares protection which silently does
        nothing is worse than one that fails loudly at boot.
        """
        aliases = {**self.route_middleware_aliases(), **self._aliases}
        resolved = []
        for entry in entries or []:
            if isinstance(entry, str):
                if entry not in aliases:
                    raise KeyError(
                        f"Unknown route middleware [{entry}]. Register it with "
                        f"kernel.alias_middleware('{entry}', SomeMiddleware)."
                    )
                resolved.append(self._instantiate(aliases[entry]))
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

        return Starlette(debug=True, routes=routes)

    def get_starlette_app(self) -> DynamicStarletteApp:
        return DynamicStarletteApp(self)

    def _instantiate(self, mw_cls: Any) -> Any:
        """Build a middleware, passing the app when it accepts one."""
        try:
            signature = inspect.signature(mw_cls.__init__)
        except (TypeError, ValueError):
            return mw_cls()
        if "app" in signature.parameters:
            return mw_cls(self.app)
        return mw_cls()

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
            from services.http.request import from_starlette

            request = await from_starlette(request).prepare()

            if module_name:
                config = self.app.make("config")
                db = self.app.make("db")

                enabled = config.get(f"modules.{module_name}.enabled", True)

                try:
                    res = db.statement("SELECT enabled FROM modules WHERE slug = ?", [module_name], read=True)
                    row = res.fetchone()
                    if row:
                        enabled = bool(row[0])
                except Exception:
                    pass

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

            try:
                return current_call(request)
            except Exception as exc:
                return self._render_exception(request, exc)

        return endpoint

    def _render_exception(self, request: Any, exc: Exception) -> StarletteResponse:
        """Turn an exception into a response via the registered handler."""
        status = getattr(exc, "status_code", None)
        headers = getattr(exc, "headers", None)
        if status in (301, 302, 303, 307, 308) and headers and "location" in headers:
            return RedirectResponse(headers["location"], status_code=status)

        try:
            handler = self.app.make("exception_handler")
        except Exception:
            handler = None

        if handler is not None and hasattr(handler, "render"):
            wants_json = getattr(request, "expects_json", lambda: True)()
            return handler.render(exc, wants_json=wants_json)

        return JSONResponse({"error": str(exc)}, status_code=status or 500)
