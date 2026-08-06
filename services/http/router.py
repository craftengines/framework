"""Routing system for Codepy Framework."""

import re
from typing import Any, Callable, Dict, List, Optional, Union


class RouteEntry:
    def __init__(self, methods: List[str], uri: str, action: Any, prefix: str = "", name_prefix: str = "", middleware: Optional[List[Any]] = None):
        self.methods = [m.upper() for m in methods]
        clean_prefix = prefix.rstrip('/')
        clean_uri = uri.lstrip('/')
        self.uri = f"{clean_prefix}/{clean_uri}".rstrip('/') if clean_prefix or clean_uri else '/'
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

    def resource(self, name: str, controller: Any) -> None:
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        self.get(f"/{name}/create", [controller, "create"]).name(f"{name}.create")
        self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        self.get(f"/{name}/{{id}}/edit", [controller, "edit"]).name(f"{name}.edit")
        self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")

    def api_resource(self, name: str, controller: Any) -> None:
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")

    def url_for(self, name: str, **params) -> str:
        for r in self.routes:
            if r._name == name:
                url = r.uri
                for k, v in params.items():
                    url = url.replace(f"{{{k}}}", str(v))
                return url
        return f"/{name}"
