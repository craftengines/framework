"""The control panel — a workspace for every signed-in account.

Category: Application (Panel Controllers).
Relations:
  - Routes in `routes/web.py` under `/panel`, all behind `auth`; the sections
    that manage other people additionally require `role:admin`.
  - Renders `resources/views/panel/*` inside `layouts/panel.forge.py`.
  - The sidebar comes from the `nav` registry
    (`engine/support/navigation.py`), declared in
    `app/Providers/PanelServiceProvider.py` and filtered per visitor.
References:
  - Guide: `documentation/authorization.md`

Design note. The panel is deliberately **not** an admin-only area. An ordinary
account gets a real workspace — their posts, their profile, and an honest
account of the access they hold — and an administrator sees the same shell with
more sections in it. Building two parallel panels is how the two drift apart;
one shell whose menu is filtered means an ordinary user cannot even see, let
alone click, what they may not have.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Auth, DB, Nav
from craft.http.controller import Controller
from craft.http.response import redirect


class PanelController(Controller):
    """Every page of the panel. Each action ends in `self.panel(...)`."""

    # -- shell -----------------------------------------------------------------

    def panel(self, request, template: str, data: dict):
        """Render a panel page with the shell's own context filled in.

        Centralised so no page can forget the menu — a panel page that renders
        without `nav_sections` loses its navigation entirely, and the failure
        looks like a styling bug rather than a missing variable.
        """
        user = Auth.user()
        context = {
            "current_user": user,
            "nav_sections": Nav.for_user(user, self._path(request)),
            "show_sidebar": False,
        }
        context.update(data)
        return self.view(template, context)

    @staticmethod
    def _path(request) -> str:
        """Current path, used to highlight the active menu item."""
        try:
            return request.url.path
        except Exception:
            return ""

    # -- workspace -------------------------------------------------------------

    def index(self, request):
        """Dashboard — the visitor's own workspace.

        What an ordinary account sees here is strictly its own: what it wrote,
        and when it joined. It does **not** see roles, groups, permission counts
        or anything else describing how access is configured. That is the
        installation's security configuration, not the visitor's personal data:
        knowing which roles exist and which of them you hold is a map for
        probing the system, and it belongs to whoever administers it.

        Administrators additionally get the installation-wide figures — the
        size of the system is itself information an account that cannot see its
        contents should not be handed.
        """
        from app.Models.Post import Post

        user = Auth.user()
        user_id = user.get_attribute("id")

        my_posts = Post.query().where("user_id", user_id).order_by_desc("created_at").limit(5).get()
        my_post_count = Post.query().where("user_id", user_id).count()

        stats = [
            {"label": "My posts", "value": my_post_count, "hint": "Written by you"},
            {"label": "Published", "value": my_post_count, "hint": "Visible on the site"},
            {"label": "Member since", "value": self._joined(user), "hint": "Your account"},
        ]

        admin_stats = []
        if self._is_admin(user):
            from app.Models.Group import Group
            from app.Models.User import User

            admin_stats = [
                {"label": "Users", "value": User.query().count(), "hint": "Accounts in this installation"},
                {"label": "Posts", "value": Post.query().count(), "hint": "Across every author"},
                {"label": "Groups", "value": Group.query().count(), "hint": "Teams with shared access"},
                {"label": "Modules", "value": len(self._modules()), "hint": "Feature areas"},
            ]

        return self.panel(request, "panel.index", {
            "heading": f"Welcome back, {user.get_attribute('name')}",
            "subheading": "Your workspace in this installation.",
            "stats": stats,
            "admin_stats": admin_stats,
            "my_posts": my_posts,
        })

    @staticmethod
    def _joined(user) -> str:
        """Just the date part of `created_at` — a timestamp is not a fact
        anybody reads off a dashboard."""
        value = user.get_attribute("created_at")
        return str(value).split("T")[0].split(" ")[0] if value else "—"

    def _is_admin(self, user) -> bool:
        """`is_admin`, or the `admin` role — either is sufficient.

        Same rule as the `access-admin-dashboard` Gate ability, so an
        installation that manages access purely through roles and one that flags
        the column both behave the same.
        """
        if user is None:
            return False
        if user.get_attribute("is_admin"):
            return True
        return self.app_access().has_role(user, "admin")

    def profile(self, request):
        """The account's own details — and nothing about how access is wired.

        The security-shaped rows (whether the account is an administrator, its
        internal `type`) are shown to administrators only. To an ordinary user
        this page is their name, their email and when they joined: their data,
        not the installation's configuration.
        """
        user = Auth.user()
        return self.panel(request, "panel.profile", {
            "heading": "My profile",
            "subheading": "Your account in this installation.",
            "user": user,
            "is_admin": self._is_admin(user),
        })

    def access(self, request):
        """Access audit — **administrators only** (`role:admin` on the route).

        Shows every permission in play, the path each grant arrives by
        (direct, role, group→role, group) and the conditions attached to it,
        straight from the resolver that makes the decision.

        This started life as a "My access" page for every visitor and was moved
        behind the admin guard: permission slugs, grant paths and raw ABAC
        conditions describe how the installation is secured. Telling an
        ordinary account that `delete-post` reaches it via `group-role` under
        such-and-such condition hands over a map for probing the system, and it
        answers a question only whoever administers access needs to ask.
        """
        user = Auth.user()
        access = self.app_access()

        grants = []
        for slug in access.permissions(user):
            for grant in access.explain(user, slug):
                grants.append({
                    "slug": slug,
                    "source": grant["source"],
                    "conditions": grant["conditions"],
                })

        return self.panel(request, "panel.access", {
            "heading": "Access audit",
            "subheading": "How this account's permissions are configured.",
            "roles": access.roles(user),
            "groups": access.groups(user),
            "grants": grants,
        })

    def posts(self, request):
        """Posts. Ordinary accounts see their own; administrators see all.

        The scoping is the point: the same page, the same template, and the
        query narrowed by who is asking.
        """
        from app.Models.Post import Post

        user = Auth.user()
        access = self.app_access()
        is_admin = access.has_role(user, "admin") or bool(user.get_attribute("is_admin"))

        query = Post.query().order_by_desc("created_at")
        if not is_admin:
            query = query.where("user_id", user.get_attribute("id"))

        return self.panel(request, "panel.posts", {
            "heading": "Posts" if is_admin else "My posts",
            "subheading": "Every post in this installation." if is_admin
                          else "Posts you have written.",
            "posts": query.limit(50).get(),
            "is_admin": is_admin,
        })

    # -- administration --------------------------------------------------------

    def users(self, request):
        """The account directory. Admin-only, and the route says so too."""
        from app.Models.User import User

        access = self.app_access()
        users = User.query().order_by_desc("created_at").limit(100).get()

        rows = [
            {
                "user": user,
                "roles": access.roles(user),
                "groups": access.groups(user),
            }
            for user in users
        ]

        return self.panel(request, "panel.users", {
            "heading": "Users",
            "subheading": f"{len(rows)} accounts.",
            "rows": rows,
        })

    def modules(self, request):
        """Feature modules, with their live enabled state."""
        return self.panel(request, "panel.modules", {
            "heading": "Modules",
            "subheading": "Feature areas. A disabled module makes its routes 404 "
                          "without a deploy.",
            "modules": self._modules(),
        })

    def toggle_module(self, request):
        """Enable or disable a module, then return to the list."""
        slug = request.post("slug")
        enable = request.post("enable") == "1"
        if slug:
            manager = self.container().make("module")
            manager.enable(slug) if enable else manager.disable(slug)
        return redirect(url="/panel/modules", status=302)

    def plugins(self, request):
        """Installed plugins, discovered from `plugins/<slug>/plugin.py`."""
        manager = self.container().make("plugin")
        try:
            installed = manager.installed()
        except Exception:
            installed = []
        return self.panel(request, "panel.plugins", {
            "heading": "Plugins",
            "subheading": "Discovered from plugins/<slug>/plugin.py.",
            "plugins": installed,
        })

    def system(self, request):
        """What this installation actually is: versions, driver, counts."""
        import platform
        import sys

        db = self.container().make("db")
        config = self.container().make("config")

        # Counted per dialect, the same way `dev.py db tables` does it — there
        # is no cross-driver table listing helper to lean on.
        listings = {
            "sqlite": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            "postgresql": "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()",
        }
        sql = listings.get(
            db.driver,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()",
        )
        try:
            table_count = len(db.statement(sql, read=True).fetchall())
        except Exception:
            # An unavailable count is reported as unavailable, never as zero:
            # "0 tables" and "could not ask" look identical and mean opposites.
            table_count = None

        facts = [
            ("Craft version", f"{config.get('app.version')} {config.get('app.release')}"),
            ("Environment", config.get("app.APP_ENV", "local")),
            ("Debug", "on" if config.get("app.APP_DEBUG", False) else "off"),
            ("Python", sys.version.split()[0]),
            ("Platform", platform.platform()),
            ("Database driver", db.driver),
            ("Tables", table_count if table_count is not None else "unavailable"),
            ("Locale", config.get("app.APP_LOCALE", "en")),
        ]

        return self.panel(request, "panel.system", {
            "heading": "About this install",
            "subheading": "Read from the running application, not from a config file.",
            "facts": facts,
        })

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def container():
        from craft.container.application import Container

        return Container.getInstance()

    def app_access(self):
        return self.container().make("access")

    def _modules(self):
        """Every module with the state the router will actually honour."""
        try:
            manager = self.container().make("module")
            modules = manager.all()
        except Exception:
            return []

        result = []
        for module in modules:
            slug = module.get("slug")
            result.append({
                "slug": slug,
                "name": module.get("name") or slug,
                "enabled": bool(module.get("enabled")),
            })
        return result
