"""
Router — Route registration (`get`/`post`/...), groups, `resource()`/
`api_resource()`, named routes, and `url_for()`.
Category: Core Framework (HTTP).
Relations:
  - Exposed via the `Route` facade; mounted into Starlette by
    `services/http/kernel.py`; middleware aliases resolved by
    `services/http/middleware.py`.
References:
  - Guide: `documentation/routing.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from typing import Any, Callable, Dict, List, Optional, Union


class RouteEntry:
    def __init__(self, methods: List[str], uri: str, action: Any, prefix: str = "", name_prefix: str = "", middleware: Optional[List[Any]] = None):
        self.methods = [m.upper() for m in methods]
        # Always produce an absolute path: a group prefix given without a
        # leading slash ("api") must not yield "api/posts" — Starlette asserts
        # on routes that do not start with "/".
        combined = "/".join(p for p in (prefix.strip("/"), uri.strip("/")) if p)
        self.uri = f"/{combined}" if combined else "/"
        self.action = action
        self._name = ""
        self.name_prefix = name_prefix
        self.middleware_list = middleware or []
        self._module: Optional[str] = None

    def name(self, name: str) -> 'RouteEntry':
        self._name = f"{self.name_prefix}{name}"
        return self

    def middleware(self, *middleware) -> 'RouteEntry':
        self.middleware_list.extend(middleware)
        return self

    def module(self, module_name: str) -> 'RouteEntry':
        self._module = module_name
        return self


class Router:
    def __init__(self, container: Optional[Any] = None):
        self.container = container
        self.routes: List[RouteEntry] = []
        #: Bumped on every registration so the kernel can cache the built
        #: Starlette app and rebuild only when the route table changes.
        self._version = 0
        self._named_routes: Dict[str, RouteEntry] = {}
        self._group_stack: List[Dict[str, Any]] = []

    def add_route(self, methods: Union[str, List[str]], uri: str, action: Any) -> RouteEntry:
        if isinstance(methods, str):
            methods = [methods]

        prefix = "".join([g.get("prefix", "") for g in self._group_stack])
        name_prefix = "".join([g.get("name", "") for g in self._group_stack])

        middleware = []
        for g in self._group_stack:
            if "middleware" in g:
                m_item = g["middleware"]
                if isinstance(m_item, list):
                    middleware.extend(m_item)
                else:
                    middleware.append(m_item)

        route = RouteEntry(methods, uri, action, prefix=prefix, name_prefix=name_prefix, middleware=middleware)
        self.routes.append(route)
        self._version += 1
        return route

    def get(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route(["GET", "HEAD"], uri, action)

    def post(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("POST", uri, action)

    def put(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("PUT", uri, action)

    def patch(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("PATCH", uri, action)

    def delete(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("DELETE", uri, action)

    def group(self, callback: Callable, prefix: str = "", middleware: Optional[Union[str, List[str]]] = None, name: str = "") -> None:
        group_attrs = {}
        if prefix:
            group_attrs["prefix"] = prefix
        if middleware:
            group_attrs["middleware"] = middleware
        if name:
            group_attrs["name"] = name

        self._group_stack.append(group_attrs)
        try:
            callback()
        finally:
            self._group_stack.pop()

    def resource(self, name: str, controller: Any, write_middleware: Optional[Union[str, List[str]]] = None) -> None:
        """Register the standard 7 CRUD routes.

        `write_middleware` — e.g. "auth" — is applied only to the
        state-changing actions (store/update/destroy), not to the read-only
        ones (index/show/create/edit), so a resource can stay publicly
        readable while still requiring a logged-in user to mutate it.
        """
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        self.get(f"/{name}/create", [controller, "create"]).name(f"{name}.create")
        store = self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        self.get(f"/{name}/{{id}}/edit", [controller, "edit"]).name(f"{name}.edit")
        update = self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        destroy = self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")
        if write_middleware:
            mw = write_middleware if isinstance(write_middleware, list) else [write_middleware]
            for route in (store, update, destroy):
                route.middleware(*mw)

    def api_resource(self, name: str, controller: Any, write_middleware: Optional[Union[str, List[str]]] = None) -> None:
        """Same as `resource()` but without the HTML-only create/edit routes."""
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        store = self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        update = self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        destroy = self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")
        if write_middleware:
            mw = write_middleware if isinstance(write_middleware, list) else [write_middleware]
            for route in (store, update, destroy):
                route.middleware(*mw)

    def url_for(self, name: str, **params) -> str:
        from urllib.parse import quote, urlencode

        for r in self.routes:
            if r._name == name:
                url = r.uri
                used = set()
                for k, v in params.items():
                    placeholder = f"{{{k}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, quote(str(v), safe=""))
                        used.add(k)
                leftover = re.findall(r"\{(\w+)\}", url)
                if leftover:
                    raise ValueError(
                        f"Missing parameters {leftover} for route [{name}]."
                    )
                extra = {k: v for k, v in params.items() if k not in used}
                if extra:
                    url += "?" + urlencode(extra)
                return url
        return f"/{name}"
