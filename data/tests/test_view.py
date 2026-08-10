"""Forge view engine: Forge directives, helpers and error propagation."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from jinja2 import TemplateNotFound, UndefinedError

from craft.view.forge import Forge, compile_directives, resolve_view_path


class TestViewPathResolution:
    def test_dot_notation_becomes_a_path(self):
        assert resolve_view_path("layouts.app") == "layouts/app.forge.py"

    def test_nested_dots(self):
        assert resolve_view_path("admin.users.index") == "admin/users/index.forge.py"

    def test_explicit_extensions_are_left_alone(self):
        assert resolve_view_path("layouts/app.forge.py") == "layouts/app.forge.py"
        assert resolve_view_path("page.html") == "page.html"


class TestDirectives:
    def test_csrf_becomes_a_hidden_field(self):
        assert compile_directives("@csrf") == "{{ csrf_field() }}"

    def test_auth_block(self):
        assert compile_directives("@auth x @endauth") == "{% if auth() %} x {% endif %}"

    def test_guest_block(self):
        assert compile_directives("@guest x @endguest") == "{% if not auth() %} x {% endif %}"

    def test_if_else(self):
        result = compile_directives("@if(a > 1) x @else y @endif")
        assert result == "{% if a > 1 %} x {% else %} y {% endif %}"

    def test_elseif_is_not_eaten_by_if(self):
        result = compile_directives("@if(a) x @elseif(b) y @endif")
        assert "{% elif b %}" in result

    def test_foreach(self):
        result = compile_directives("@foreach(posts as post) x @endforeach")
        assert result == "{% for post in posts %} x {% endfor %}"

    def test_extends_resolves_the_view_path(self):
        # The whole reason every layout-extending view used to fail.
        assert compile_directives('@extends("layouts.app")') == (
            '{% extends "layouts/app.forge.py" %}'
        )

    def test_include_resolves_the_view_path(self):
        assert compile_directives('@include("partials.nav")') == (
            '{% include "partials/nav.forge.py" %}'
        )

    def test_section_opens_a_block(self):
        assert compile_directives('@section("content")') == "{% block content %}"

    def test_inline_section_emits_the_bare_string(self):
        assert compile_directives('@section("title", "Hello")') == (
            "{% block title %}Hello{% endblock %}"
        )

    def test_inline_section_with_an_expression(self):
        assert compile_directives('@section("title", post.title)') == (
            "{% block title %}{{ post.title }}{% endblock %}"
        )

    def test_endsection(self):
        assert compile_directives("@endsection") == "{% endblock %}"

    def test_yield_becomes_an_empty_block(self):
        assert compile_directives('@yield("content")') == "{% block content %}{% endblock %}"

    def test_method_spoofing(self):
        assert 'name="_method" value="PUT"' in compile_directives('@method("PUT")')

    def test_plain_text_is_untouched(self):
        source = "<p>An email like a@b.com must survive</p>"
        assert compile_directives(source) == source


class TestRendering:
    @pytest.fixture
    def forge(self, tmp_path, migrated_database):
        views = tmp_path / "resources" / "views"
        (views / "layouts").mkdir(parents=True)

        (views / "layouts" / "app.forge.py").write_text(
            "<html><title>@yield('title')</title><body>@yield('body')</body></html>",
            encoding="utf-8",
        )
        (views / "page.forge.py").write_text(
            '@extends("layouts.app")\n'
            '@section("title", "Hi")\n'
            '@section("body")<p>{{ name }}</p>@endsection',
            encoding="utf-8",
        )
        (views / "broken.forge.py").write_text("{{ undefined_variable.attribute }}", encoding="utf-8")
        (views / "form.forge.py").write_text("<form>@csrf</form>", encoding="utf-8")

        class FakeApp:
            base_path = str(tmp_path)

        return Forge(FakeApp())

    def test_renders_through_a_layout(self, forge):
        html = forge.render("page", {"name": "Jane"})
        assert "<title>Hi</title>" in html
        assert "<p>Jane</p>" in html

    def test_missing_template_raises(self, forge):
        # It used to return a "<div>Rendered view: x</div>" placeholder with a
        # 200, so a broken view looked like a working page.
        with pytest.raises(TemplateNotFound):
            forge.render("does.not.exist")

    def test_template_errors_propagate(self, forge):
        with pytest.raises(UndefinedError):
            forge.render("broken")

    def test_exists(self, forge):
        assert forge.exists("page") is True
        assert forge.exists("nope") is False

    def test_csrf_field_renders_an_input(self, forge):
        assert 'name="_token"' in forge.render("form")

    def test_autoescaping_is_on(self, forge):
        html = forge.render("page", {"name": "<script>alert(1)</script>"})
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_share_exposes_a_global(self, forge):
        import os

        forge.share("site_name", "Craft")
        with open(os.path.join(forge.views_dir, "shared.forge.py"), "w", encoding="utf-8") as handle:
            handle.write("{{ site_name }}")

        assert forge.render("shared") == "Craft"


class TestHelpers:
    def test_config_helper_reads_app_config(self, migrated_database):
        from craft.view.forge import config_value

        assert config_value("app.APP_NAME", "fallback") is not None

    def test_config_helper_falls_back(self, migrated_database):
        from craft.view.forge import config_value

        assert config_value("nothing.here", "fallback") == "fallback"

    def test_csrf_token_is_empty_without_a_session(self):
        from craft.view.forge import csrf_token

        assert csrf_token() == ""

    def test_csrf_token_reads_the_current_session(self):
        from craft.http.session import Session, current_session
        from craft.view.forge import csrf_token

        session = Session()
        token = current_session.set(session)
        try:
            assert csrf_token() == session.token()
        finally:
            current_session.reset(token)
