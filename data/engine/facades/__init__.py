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
