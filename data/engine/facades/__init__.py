"""Concrete Facades for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.facades.base import Facade


class Route(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "router"


class DB(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "db"


class Config(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "config"


class Auth(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "auth"


class Event(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "events"


class Queue(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "queue"


class Log(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "log"


class Cache(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "cache"


class Hash(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "hash"


class Migrator(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "migrator"


class Gate(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "gate"


class Nav(Facade):
    """The navigation registry — declare a menu, resolve it per visitor.

    `Nav.for_user(user, path)` returns only the sections and items that user
    may actually reach, so the menu never offers a link that ends in a 403.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "nav"


class Access(Facade):
    """Roles, groups and permissions — including a grant's attribute conditions.

    `Gate` answers "may this user do X?" and consults `Access` on the way.
    Reach for `Access` directly to *inspect* authorization: which roles or
    groups a user has, every permission they can reach, and `explain()` for
    why a particular permission reaches them.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "access"


class View(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "view"


class Schema(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "schema"


class Module(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "module"


class Plugin(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "plugin"


class Setting(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "setting"


class PQC(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "pqc"


class Captcha(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "captcha"


class Schedule(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "schedule"


class Firewall(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "firewall"


class Honeypot(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "honeypot"


class Image(Facade):
    """Fluent image manipulation and optimization facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "image"


class Media(Facade):
    """Multimedia processing and video thumbnail facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "media"


class AI(Facade):
    """Unified AI SDK and Agent Orchestrator facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "ai"


class Agent(Facade):
    """Agent Tool registration and discovery facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "agent"


class MCP(Facade):
    """Model Context Protocol server facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "agent"

