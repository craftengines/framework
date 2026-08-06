"""Forge View Engine for Codepy Framework.

Jinja2 with Blade-style directives. Templates are preprocessed before Jinja
compiles them, so `@csrf`, `@auth` and friends work in `.blade.py` files.
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from jinja2 import BaseLoader, Environment, FileSystemLoader, TemplateNotFound
from markupsafe import Markup

def resolve_view_path(name: str) -> str:
    """Turn a Laravel-style view name into a template path.

    `layouts.app` -> `layouts/app.blade.py`. Without this, `@extends` handed the
    dotted name straight to Jinja, which looked for a file literally called
    "layouts.app" — so every view that extended a layout failed to render.
    """
    if name.endswith((".blade.py", ".html")):
        return name
    return name.replace(".", "/") + ".blade.py"


#: Blade directive -> Jinja equivalent. Order matters: longer directives first,
#: so `@endauth` is not partially matched by `@end`.
DIRECTIVES = [
    (r"@csrf\b", "{{ csrf_field() }}"),
    (r"@method\(\s*['\"](\w+)['\"]\s*\)", r'<input type="hidden" name="_method" value="\1">'),
    (r"@auth\b", "{% if auth() %}"),
    (r"@endauth\b", "{% endif %}"),
    (r"@guest\b", "{% if not auth() %}"),
    (r"@endguest\b", "{% endif %}"),
    (r"@can\(\s*(.+?)\s*\)", r"{% if can(\1) %}"),
    (r"@endcan\b", "{% endif %}"),
    (r"@elseif\s*\((.+?)\)", r"{% elif \1 %}"),
    (r"@if\s*\((.+?)\)", r"{% if \1 %}"),
    (r"@else\b", "{% else %}"),
    (r"@endif\b", "{% endif %}"),
    (r"@foreach\s*\((.+?)\s+as\s+(.+?)\)", r"{% for \2 in \1 %}"),
    (r"@endforeach\b", "{% endfor %}"),
    (r"@endsection\b", "{% endblock %}"),
    (r"@yield\(\s*['\"]([\w.-]+)['\"]\s*,\s*(.+?)\s*\)", r"{% block \1 %}\2{% endblock %}"),
    (r"@yield\(\s*['\"]([\w.-]+)['\"]\s*\)", r"{% block \1 %}{% endblock %}"),
]

_COMPILED = [(re.compile(pattern), replacement) for pattern, replacement in DIRECTIVES]

# Directives carrying a view name need the path resolved, so they are handled
# with a callback rather than a plain substitution.
_EXTENDS_RE = re.compile(r"@extends\(\s*['\"](.+?)['\"]\s*\)")
_INCLUDE_RE = re.compile(r"@include\(\s*['\"](.+?)['\"]\s*\)")

# `@section("title", "value")` is the inline form; `@section("content")` opens a
# block closed by @endsection.
_SECTION_INLINE_RE = re.compile(r"@section\(\s*['\"]([\w.-]+)['\"]\s*,\s*(.+?)\s*\)")
_SECTION_RE = re.compile(r"@section\(\s*['\"]([\w.-]+)['\"]\s*\)")


def _inline_section(match: "re.Match[str]") -> str:
    """`@section("title", "Hello")` -> a block containing Hello.

    A quoted literal is emitted as bare text; anything else is treated as an
    expression, so `@section("title", post.title)` still works.
    """
    name, value = match.group(1), match.group(2).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        body = value[1:-1]
    else:
        body = "{{ " + value + " }}"
    return "{% block " + name + " %}" + body + "{% endblock %}"


def compile_directives(source: str) -> str:
    """Rewrite Blade directives into Jinja syntax."""
    source = _EXTENDS_RE.sub(
        lambda m: '{% extends "' + resolve_view_path(m.group(1)) + '" %}', source
    )
    source = _INCLUDE_RE.sub(
        lambda m: '{% include "' + resolve_view_path(m.group(1)) + '" %}', source
    )
    source = _SECTION_INLINE_RE.sub(_inline_section, source)
    source = _SECTION_RE.sub(r"{% block \1 %}", source)

    for pattern, replacement in _COMPILED:
        source = pattern.sub(replacement, source)
    return source


class BladeLoader(BaseLoader):
    """Wraps a loader, translating directives as each template is read."""

    def __init__(self, inner: BaseLoader):
        self.inner = inner

    def get_source(self, environment, template):
        source, filename, uptodate = self.inner.get_source(environment, template)
        return compile_directives(source), filename, uptodate

    def list_templates(self):
        return self.inner.list_templates()


# -- view helpers available inside every template --------------------------------

def csrf_token() -> str:
    from services.http.session import get_current_session

    session = get_current_session()
    return session.token() if session is not None else ""


def csrf_field() -> Markup:
    return Markup(f'<input type="hidden" name="_token" value="{csrf_token()}">')


def auth_user() -> Any:
    from services.container.application import Container

    try:
        return Container.getInstance().make("auth").user()
    except Exception:
        return None


def can(ability: str, *args) -> bool:
    from services.container.application import Container

    try:
        gate = Container.getInstance().make("gate")
    except Exception:
        return False
    return bool(gate.allows(ability, auth_user(), *args))


def route_url(name: str, **params) -> str:
    from services.container.application import Container

    try:
        return Container.getInstance().make("router").url_for(name, **params)
    except Exception:
        return "/"


def asset(path: str, version: Any = None) -> str:
    """URL for a file under `public/`, with a cache-busting query string.

        {{ asset('assets/css/codepy-theme.css') }}
        -> /assets/css/codepy-theme.css?ver=0.1.0

    The version defaults to the application version, so a release invalidates
    every cached asset at once. In debug the file's modification time is used
    instead, so an edit shows up on the next reload without a version bump.
    """
    path = "/" + str(path).lstrip("/")

    if version is None:
        if config_value("app.APP_DEBUG"):
            import os

            from services.container.application import Container

            try:
                base = getattr(Container.getInstance(), "base_path", os.getcwd())
                stamp = os.path.getmtime(os.path.join(base, "public", path.lstrip("/")))
                version = int(stamp)
            except (OSError, Exception):
                version = None
        if version is None:
            version = config_value("app.APP_VERSION", "0")

    return f"{path}?ver={version}"


def config_value(key: str, default: Any = None) -> Any:
    from services.container.application import Container

    try:
        return Container.getInstance().make("config").get(key, default)
    except Exception:
        return default


def active_locale() -> str:
    """The locale in effect for this request.

    Templates used to read `config('app.locale')`, but the config repository
    registers the key as `APP_LOCALE` / `app_locale` — there is no `locale`, so
    that lookup always returned None and no language ever showed as active.
    """
    from services.support.translation import get_current_locale

    return str(
        get_current_locale()
        or config_value("app.APP_LOCALE")
        or config_value("app.app_locale")
        or "en"
    )


def session_value(key: str, default: Any = None) -> Any:
    from services.http.session import get_current_session

    session = get_current_session()
    return session.get(key, default) if session is not None else default

def old_input(key: str, default: Any = "") -> Any:
    """Previously submitted value, flashed back after a failed validation."""
    return (session_value("_old_input") or {}).get(key, default)


class Forge:
    """Renders templates from `resources/views`."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        base_path = app.base_path if app else os.getcwd()
        views_dir = os.path.join(base_path, "resources", "views")
        if not os.path.exists(views_dir):
            views_dir = os.getcwd()

        self.views_dir = views_dir
        self.env = Environment(
            loader=BladeLoader(FileSystemLoader(views_dir)),
            autoescape=True,
        )
        self.env.globals.update(
            {
                "csrf_token": csrf_token,
                "csrf_field": csrf_field,
                "auth": auth_user,
                "can": can,
                "route": route_url,
                "asset": asset,
                "config": config_value,
                "locale": active_locale,
                "session": session_value,
                "old": old_input,
            }
        )

        from services.support.collection import __ as translate

        self.env.globals["__"] = translate

    def share(self, key: str, value: Any) -> None:
        """Make a value available to every template."""
        self.env.globals[key] = value

    def exists(self, template_name: str) -> bool:
        try:
            self.env.get_template(self._resolve(template_name))
            return True
        except TemplateNotFound:
            return False

    @staticmethod
    def _resolve(template_name: str) -> str:
        return resolve_view_path(template_name)

    def render(self, template_name: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Render a template.

        Errors propagate. This used to catch every exception and return a
        `<div>Rendered view: x</div>` placeholder, so a typo in a template — or
        a missing variable — silently produced a page that looked fine.
        """
        template = self.env.get_template(self._resolve(template_name))
        return template.render(**(data or {}))


__all__ = ["Forge", "compile_directives", "csrf_token", "csrf_field"]
