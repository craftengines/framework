"""Driver capabilities for the Craft ORM.

`driver == "postgresql"` used to be tested inline wherever a dialect difference
mattered — the connection layer, the manager, the migrator, the schema grammar.
This module is the one place that answers "can this driver do X?", and the one
place that decides what happens when it cannot.

Category: Core Framework (ORM).
Relations:
  - Exposed as `Connection.dialect` (`engine/orm/connection.py`) and
    `DatabaseManager.dialect` (`engine/orm/db.py`).
  - Consulted by the PostgreSQL macros in `engine/orm/postgres/`, the queue
    drivers, the lock manager and the tenancy manager.
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Optional, Protocol, Set, runtime_checkable

#: Every capability the framework asks a driver about. A name outside this set
#: is a typo, and `supports()` raises rather than quietly answering False —
#: a misspelled feature that reports "unsupported" switches a subsystem off
#: with no signal at all.
FEATURES = frozenset({
    "advisory_locks",
    "arrays",
    "extensions",
    "fulltext",
    "jsonb",
    "listen_notify",
    "partial_indexes",
    "partitioning",
    "ranges",
    "returning",
    "rls",
    "skip_locked",
    "transactional_ddl",
    "trigram",
    "uuidv7",
    "vector",
})

#: Capabilities whose absence is a *security* difference rather than a
#: performance one. `require()` never lets these degrade — see its docstring.
SECURITY_FEATURES = frozenset({"rls", "advisory_locks"})


class UnsupportedFeatureError(RuntimeError):
    """The configured driver cannot provide a feature the caller depends on."""


@runtime_checkable
class Dialect(Protocol):
    """What the rest of the framework may assume about a driver."""

    name: str
    features: Set[str]

    def supports(self, feature: str) -> bool: ...

    def require(self, feature: str, because: str) -> None: ...


class BaseDialect:
    """Common behaviour; subclasses declare only their feature set."""

    name = "generic"
    features: Set[str] = set()

    def supports(self, feature: str) -> bool:
        if feature not in FEATURES:
            raise ValueError(
                f"Unknown capability [{feature}]. Known: {', '.join(sorted(FEATURES))}."
            )
        return feature in self.features

    def require(self, feature: str, because: str) -> None:
        """Refuse to continue without `feature`.

        A missing capability is not a degraded mode to be logged. The tenant
        middleware used to warn once and keep serving requests against shared
        tables — an isolation failure wearing the costume of a working feature.
        Anything missing stops the caller here, with a message that names the
        driver, the capability and the way out.
        """
        if self.supports(feature):
            return
        raise UnsupportedFeatureError(
            f"The {self.name!r} driver has no {feature!r}, which {because}. "
            f"Use PostgreSQL for this application, or turn the feature off "
            f"explicitly in config."
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Dialect {self.name}>"


#: Capabilities PostgreSQL only has once an extension is installed. Claiming
#: these from the version alone is wrong in the way that matters: the query
#: compiles, reaches the server and fails there with `type "vector" does not
#: exist` — a runtime error in place of the capability check that exists to
#: prevent exactly that.
EXTENSION_FEATURES = {
    "vector": "vector",
    "trigram": "pg_trgm",
}

#: Capabilities that arrived in a specific server release. Same principle as
#: the extension gate: what the server actually has, not what the driver could
#: in principle be talking to.
VERSION_FEATURES = {
    # `uuidv7()` became a built-in function in PostgreSQL 18. Below that the
    # framework generates v7 in Python (`Model.new_uuid`), which is equivalent
    # but cannot be a column DEFAULT.
    "uuidv7": (18, 0),
}

#: Everything a stock, current server provides.
POSTGRES_CORE = set(FEATURES) - set(EXTENSION_FEATURES) - set(VERSION_FEATURES)

#: Below this the framework does not claim to work. Row-level security,
#: `SKIP LOCKED`, declarative partitioning and generated columns all predate it.
MINIMUM_POSTGRES = (14, 0)

#: What the framework is developed and validated against. Older servers are
#: supported, not recommended: `uuidv7()`, virtual generated columns and the
#: planner work that makes partitioned tables cheap all land after 15.
RECOMMENDED_POSTGRES = (18, 4)


def format_version(version: Optional[tuple]) -> str:
    return ".".join(str(part) for part in version) if version else "unknown"


class PostgresDialect(BaseDialect):
    """PostgreSQL, narrowed by server version and installed extensions.

    `extensions=None` and `version=None` mean "nothing has asked the server
    yet", and the dialect reports the full feature set — the right answer for
    compiling SQL with no connection to consult. A live `Connection` always
    probes (see `Connection.dialect`), so the answer a running application gets
    is the true one.
    """

    name = "postgresql"

    def __init__(
        self,
        extensions: Optional[Set[str]] = None,
        version: Optional[tuple] = None,
    ):
        self.version = version
        if extensions is None and version is None:
            self.features = set(FEATURES)
            self.extensions: Optional[Set[str]] = None
            return

        self.extensions = set(extensions or ())
        self.features = set(POSTGRES_CORE)
        self.features |= {
            feature
            for feature, extension in EXTENSION_FEATURES.items()
            if extension in self.extensions
        }
        self.features |= {
            feature
            for feature, since in VERSION_FEATURES.items()
            if version is not None and version >= since
        }

    # -- version -----------------------------------------------------------

    @property
    def meets_minimum(self) -> bool:
        return self.version is None or self.version >= MINIMUM_POSTGRES

    @property
    def meets_recommended(self) -> bool:
        return self.version is None or self.version >= RECOMMENDED_POSTGRES

    def version_advice(self) -> Optional[str]:
        """What to say about this server's version, or None when nothing.

        Two different messages, because they are two different situations: a
        server below the minimum will fail on features the framework uses
        unconditionally, while one below the recommended version works and
        merely misses newer ones.
        """
        if self.version is None:
            return None
        if not self.meets_minimum:
            return (
                f"PostgreSQL {format_version(self.version)} is below the "
                f"minimum this framework supports "
                f"({format_version(MINIMUM_POSTGRES)}). Features it uses "
                f"unconditionally are not present on this server."
            )
        if not self.meets_recommended:
            missing = sorted(
                feature
                for feature, since in VERSION_FEATURES.items()
                if self.version < since
            )
            return (
                f"PostgreSQL {format_version(self.version)} works, but "
                f"{format_version(RECOMMENDED_POSTGRES)} is what this framework "
                f"is validated against"
                + (f"; unavailable here: {', '.join(missing)}." if missing else ".")
            )
        return None

    def require(self, feature: str, because: str) -> None:
        """As `BaseDialect.require`, but name the actual gap.

        "PostgreSQL has no 'vector'" would be misleading and unactionable. The
        gap is either one `CREATE EXTENSION` or one server upgrade, and the
        message should say which.
        """
        if self.supports(feature):
            return

        extension = EXTENSION_FEATURES.get(feature)
        if extension is not None:
            raise UnsupportedFeatureError(
                f"{feature!r} needs the {extension!r} extension, which is not "
                f"installed on this database. Add "
                f"`Schema.extension({extension!r})` to a migration."
            )

        since = VERSION_FEATURES.get(feature)
        if since is not None:
            raise UnsupportedFeatureError(
                f"{feature!r} arrived in PostgreSQL {format_version(since)} and "
                f"this server is {format_version(self.version)}, which {because}. "
                f"Upgrade the server, or use the framework's own equivalent "
                f"where one exists."
            )

        super().require(feature, because)


class SqliteDialect(BaseDialect):
    """SQLite — development and the test-suite.

    JSON1 offers containment-ish semantics and FTS5 offers search, but neither
    matches PostgreSQL closely enough to claim the capability: a query that
    works here and silently means something else there is worse than one that
    refuses to run. Development parity comes from running PostgreSQL in
    development, not from emulating it.
    """

    name = "sqlite"
    features = {"partial_indexes", "transactional_ddl"}


class MySqlDialect(BaseDialect):
    """MySQL 8+ — the intersection that genuinely exists there."""

    name = "mysql"
    features = {"skip_locked", "advisory_locks", "fulltext"}


_DIALECTS = {
    "postgresql": PostgresDialect,
    "sqlite": SqliteDialect,
    "mysql": MySqlDialect,
}


def dialect_for(driver: str) -> BaseDialect:
    """The dialect for a normalised driver name, defaulting to the narrowest.

    An unknown driver gets SQLite's feature set rather than PostgreSQL's: the
    conservative answer refuses features it might have supported, while the
    optimistic one emits SQL the driver cannot parse.
    """
    return _DIALECTS.get(driver, SqliteDialect)()


__all__ = [
    "FEATURES",
    "MINIMUM_POSTGRES",
    "RECOMMENDED_POSTGRES",
    "SECURITY_FEATURES",
    "VERSION_FEATURES",
    "format_version",
    "BaseDialect",
    "Dialect",
    "MySqlDialect",
    "PostgresDialect",
    "SqliteDialect",
    "UnsupportedFeatureError",
    "dialect_for",
]
