"""
Model — Active Record base class for Craft ORM: CRUD, mass-assignment
protection, UUID identity, and relationship declarations.
Category: Core Framework (ORM).
Relations:
  - Subclassed by `app/Models/*`; builds queries through
    `engine/orm/query_builder.py` and relations through
    `engine/orm/relationships.py`.
  - Resolves the `db` binding via `Container.getInstance()`
    (`engine/container/application.py`).
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone

from engine.orm.query_builder import QueryBuilder, _MISSING, _assert_identifier
from engine.orm.relationships import (
    BelongsTo,
    BelongsToMany,
    HasMany,
    HasOne,
    Relation,
)


class Model:
    """Active Record Base Model."""

    __table__: Optional[str] = None
    #: Mass-assignable columns. Fail closed by default: an empty/undeclared
    #: `fillable` means **nothing** is mass-assignable through `create()` /
    #: `update_attributes()` — the exact opposite of the old (insecure)
    #: default, where empty meant unrestricted. A model that genuinely wants
    #: every column writable from request input must opt in explicitly with
    #: `guarded = False` (mirrors the "guarded" escape hatch other frameworks
    #: use for the same purpose). Trusted internal writes should keep using
    #: `force_create()` / `update()` instead of reaching for `guarded = False`.
    fillable: List[str] = []
    #: Set `False` to disable mass-assignment filtering entirely for this
    #: model — an explicit opt-out, not the default.
    guarded: bool = True
    hidden: List[str] = []
    #: Column values applied on create when the caller omits them.
    defaults: Dict[str, Any] = {}
    primary_key: str = "id"
    key_type: str = "int"  # "int" (auto-increment) or "uuid" (client generated)

    #: Fill a `uuid` column on create when the table has one. This is on by
    #: default: the integer `id` stays the key for joins, and the UUID is the
    #: identifier you expose publicly, so URLs never leak row counts or invite
    #: enumeration. Tables without the column are unaffected — nothing is
    #: inserted that the schema does not declare.
    uses_uuid: bool = True
    uuid_column: str = "uuid"

    #: Column -> cast name, e.g. `{"meta": "jsonb", "tags": "array:str"}`.
    #: Without one, an attribute holds whatever the driver returned and is
    #: written straight back — which works for text and numbers and fails for
    #: every structured PostgreSQL type. See `engine/orm/casts.py`.
    casts: Dict[str, str] = {}

    def __init__(self, attributes: Optional[Dict[str, Any]] = None):
        self._attributes: Dict[str, Any] = attributes or {}
        #: Eager-loaded relations, keyed by relation method name.
        self._relations: Dict[str, Any] = {}
        if self.casts:
            self._hydrate()

    # -- attribute casting -----------------------------------------------------

    @classmethod
    def _driver(cls) -> str:
        try:
            from engine.container.application import Container

            return Container.getInstance().make("db").driver
        except Exception:
            return "sqlite"

    @classmethod
    def _cast_for(cls, column: str) -> Any:
        from engine.orm.casts import resolve_cast

        spec = cls.casts.get(column)
        return resolve_cast(spec) if spec else None

    def _hydrate(self) -> None:
        """Turn stored values into Python ones, in place."""
        driver = self._driver()
        for column in self.casts:
            if column in self._attributes:
                cast = self._cast_for(column)
                self._attributes[column] = cast.hydrate(self._attributes[column], driver)

    @classmethod
    def _dehydrate(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Turn Python values into ones the driver will accept.

        A copy, not in place: the model keeps the Python value after a write, so
        `account.meta["plan"]` still reads as a dict rather than as the JSON
        wrapper that went to the database.
        """
        if not cls.casts:
            return attributes
        driver = cls._driver()
        out = dict(attributes)
        for column in cls.casts:
            if column in out:
                out[column] = cls._cast_for(column).dehydrate(out[column], driver)
        return out

    # -- eager-loaded relation cache -------------------------------------------

    def relation_loaded(self, name: Optional[str]) -> bool:
        return bool(name) and name in self._relations

    def get_relation(self, name: str) -> Any:
        return self._relations.get(name)

    def set_relation(self, name: Optional[str], value: Any) -> None:
        if name:
            self._relations[name] = value

    def unset_relation(self, name: str) -> None:
        self._relations.pop(name, None)

    @staticmethod
    def _calling_relation_name() -> Optional[str]:
        """Name of the model method that is building a relation.

        For the conventional `def posts(self): return self.has_many(Post)`, this
        returns "posts" — which is what the eager-load cache is keyed by. Reading
        the caller's frame is the established way to recover that name.
        """
        import inspect

        frame = inspect.currentframe()
        try:
            # 0: here, 1: has_many/belongs_to/..., 2: the model's relation method
            caller = frame.f_back.f_back if frame and frame.f_back else None
            return caller.f_code.co_name if caller else None
        finally:
            del frame

    @classmethod
    def get_table_name(cls) -> str:
        if cls.__table__:
            return cls.__table__
        name = cls.__name__.lower()
        if not name.endswith("s"):
            name += "s"
        return name

    @classmethod
    def query(cls) -> QueryBuilder:
        return QueryBuilder(model_class=cls)

    # -- UUID identity ---------------------------------------------------------

    @staticmethod
    def new_uuid() -> str:
        """A UUIDv7 — 48-bit millisecond timestamp, then randomness.

        Version 4 is uniformly random, so every insert lands on a different
        B-tree leaf and the index write set is effectively the whole index. A v7
        sorts by creation time, so inserts append to one side of it instead of
        scattering across it — same opacity in a URL, materially cheaper to
        index. PostgreSQL 18 has `uuidv7()` natively; on 16 and 17 it is
        generated here.
        """
        import os
        import time
        import uuid

        stamp = int(time.time() * 1000).to_bytes(6, "big")
        rest = bytearray(os.urandom(10))
        rest[0] = (rest[0] & 0x0F) | 0x70   # version 7
        rest[2] = (rest[2] & 0x3F) | 0x80   # RFC 4122 variant
        return str(uuid.UUID(bytes=bytes(stamp) + bytes(rest)))

    @classmethod
    def has_uuid_column(cls) -> bool:
        """Whether the table declares the public UUID column.

        The answer is cached on the DatabaseManager, not here: a schema belongs
        to a connection, so swapping connections — a replica, a tenant schema, a
        test database — has to invalidate it. Caching per model class meant a
        swap left the wrong answer behind.
        """
        try:
            from engine.container.application import Container

            db = Container.getInstance().make("db")
            return db.table_has_column(cls.get_table_name(), cls.uuid_column)
        except Exception:
            return False

    @classmethod
    def find_by_uuid(cls, value: str) -> Optional['Model']:
        if not value or (isinstance(value, str) and value.isdigit()):
            return None
        return cls.query().where(cls.uuid_column, value).first()

    @classmethod
    def find_by_uuid_or_fail(cls, value: str) -> 'Model':
        from engine.orm.exceptions import ModelNotFoundError

        found = cls.find_by_uuid(value)
        if found is None:
            raise ModelNotFoundError(f"No {cls.__name__} with uuid [{value}].")
        return found

    def route_key(self) -> Any:
        """The identifier to put in a URL — the UUID when there is one."""
        if self.uses_uuid and self._attributes.get(self.uuid_column):
            return self._attributes[self.uuid_column]
        return self._attributes.get(self.primary_key)

    @classmethod
    def find_by_route_key(cls, value: Any) -> Optional['Model']:
        """Resolve whatever `route_key()` produced, UUID or primary key.

        For security, when UUID is enabled on the model and schema, sequential
        integer queries are rejected to prevent ID enumeration.
        """
        if cls.uses_uuid and cls.has_uuid_column():
            if str(value).isdigit():
                return None
            return cls.find_by_uuid(str(value))
        return cls.find(value)

    @classmethod
    def create(cls, attributes: Dict[str, Any]) -> 'Model':
        # Mass-assignment protection, fail closed: only columns listed in
        # `fillable` may arrive from bulk input. An empty/undeclared
        # `fillable` means *nothing* is mass-assignable — not "everything",
        # which was the old, insecure default. Framework-managed columns
        # (primary key, UUID, timestamps) stay allowed regardless.
        # `guarded = False` is the explicit opt-out for a model that wants
        # every column writable; `force_create()` bypasses the guard
        # entirely for trusted internal writes.
        if cls.guarded is not False:
            allowed = set(cls.fillable) | {
                cls.primary_key, cls.uuid_column, "created_at", "updated_at",
            }
            attributes = {k: v for k, v in attributes.items() if k in allowed}
        return cls.force_create(attributes)

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> 'Model':
        """Insert without consulting `fillable` — for trusted, internal input."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        clean_attrs = dict(cls.defaults)
        clean_attrs.update(attributes)
        clean_attrs.setdefault("created_at", now)
        clean_attrs.setdefault("updated_at", now)

        inst = cls(clean_attrs)

        from engine.container.application import Container
        db = Container.getInstance().make("db")

        # Tables with a non auto-incrementing primary key need a client-side id.
        if cls.primary_key not in clean_attrs and cls.key_type == "uuid":
            clean_attrs[cls.primary_key] = cls.new_uuid()

        # Fill the public UUID when the table declares one.
        if (
            cls.uses_uuid
            and cls.uuid_column not in clean_attrs
            and cls.has_uuid_column()
        ):
            clean_attrs[cls.uuid_column] = cls.new_uuid()
            inst._attributes[cls.uuid_column] = clean_attrs[cls.uuid_column]

        new_id = db.insert_get_id(
            cls.get_table_name(), cls._dehydrate(clean_attrs), cls.primary_key
        )
        if new_id is not None:
            inst._attributes[cls.primary_key] = new_id
        elif cls.primary_key not in inst._attributes:
            import uuid

            inst._attributes[cls.primary_key] = str(uuid.uuid4())

        from engine.events.lifecycle import ModelCreated, fire

        fire(ModelCreated(inst))
        return inst

    def save(self) -> 'Model':
        """Insert or update this record."""
        from engine.container.application import Container

        db = Container.getInstance().make("db")
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        key = self.primary_key

        if self._attributes.get(key) is None:
            created = self.__class__.create(dict(self._attributes))
            self._attributes = created._attributes
            return self

        self._attributes["updated_at"] = now
        # Dehydrated for the write only — `self._attributes` keeps the Python
        # values, so the model reads the same before and after a save.
        updates = self._dehydrate(
            {k: v for k, v in self._attributes.items() if k != key}
        )
        for column in updates:
            _assert_identifier(column)
        assignments = ", ".join(f"{column} = ?" for column in updates)
        db.statement(
            f"UPDATE {self.get_table_name()} SET {assignments} WHERE {key} = ?",
            list(updates.values()) + [self._attributes[key]],
        )

        from engine.events.lifecycle import ModelUpdated, fire

        fire(ModelUpdated(self))
        return self

    def update(self, attributes: Dict[str, Any]) -> 'Model':
        """Update this record with `attributes` as given — trusted/internal
        input only. For request-supplied data use `update_attributes()`,
        which enforces `fillable` the same way `create()` does."""
        self._attributes.update(attributes)
        return self.save()

    def update_attributes(self, attributes: Dict[str, Any]) -> 'Model':
        """Mass-assignment-guarded update: the `update()` counterpart to
        `create()` for input coming from a request body. Fails closed the
        same way `create()` does — an empty/undeclared `fillable` allows
        nothing through unless the model opts out with `guarded = False`."""
        if self.guarded is not False:
            allowed = set(self.fillable)
            attributes = {k: v for k, v in attributes.items() if k in allowed}
        return self.update(attributes)

    def delete(self) -> bool:
        from engine.container.application import Container

        db = Container.getInstance().make("db")
        key = self.primary_key
        if self._attributes.get(key) is None:
            return False
        db.statement(
            f"DELETE FROM {self.get_table_name()} WHERE {key} = ?",
            [self._attributes[key]],
        )

        from engine.events.lifecycle import ModelDeleted, fire

        fire(ModelDeleted(self))
        return True

    @classmethod
    def all(cls) -> Any:
        return cls.query().get()

    @classmethod
    def where(cls, column: str, operator_or_value: Any = _MISSING, value: Any = _MISSING) -> QueryBuilder:
        return cls.query().where(column, operator_or_value, value)

    @classmethod
    def where_vector_similar(
        cls,
        column: str,
        vector: Any,
        min_similarity: float = 0.7,
        metric: str = "cosine",
    ) -> QueryBuilder:
        """Filter records by vector similarity (semantic search)."""
        return cls.query().where_vector_similar(column, vector, min_similarity=min_similarity, metric=metric)

    @classmethod
    def order_by_vector_similarity(
        cls,
        column: str,
        vector: Any,
        ascending: bool = False,
    ) -> QueryBuilder:
        """Sort records by vector similarity."""
        return cls.query().order_by_vector_similarity(column, vector, ascending=ascending)

    @classmethod
    def with_(cls, *relations: str) -> QueryBuilder:
        """Start a query that eager loads the given relations."""
        return cls.query().with_(*relations)

    @classmethod
    def find_or_fail(cls, id_val: Any) -> 'Model':
        from engine.orm.exceptions import ModelNotFoundError

        found = cls.find(id_val)
        if found is None:
            raise ModelNotFoundError(f"No {cls.__name__} found with id [{id_val}].")
        return found

    def to_dict(self) -> Dict[str, Any]:
        hidden = set(getattr(self, "hidden", []))
        return {k: v for k, v in self._attributes.items() if k not in hidden}

    def __getattr__(self, name: str) -> Any:
        attributes = self.__dict__.get("_attributes", {})
        if name in attributes:
            return attributes[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._attributes!r}>"

    @classmethod
    def find(cls, id_val: Any) -> Optional['Model']:
        if cls.uses_uuid and cls.has_uuid_column() and isinstance(id_val, str) and not id_val.isdigit():
            found = cls.find_by_uuid(id_val)
            if found is not None:
                return found
        return cls.query().where(cls.primary_key, id_val).first()


    def get_attribute(self, key: str) -> Any:
        return self._attributes.get(key)

    def set_attribute(self, key: str, value: Any) -> None:
        self._attributes[key] = value

    # -- relationships ---------------------------------------------------------

    def has_many(self, related_class: Type, foreign_key: Optional[str] = None,
                 local_key: str = "id", name: Optional[str] = None) -> HasMany:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        return HasMany(
            self, related_class, foreign_key=fk, local_key=local_key,
            name=name or self._calling_relation_name(),
        )

    def has_one(self, related_class: Type, foreign_key: Optional[str] = None,
                local_key: str = "id", name: Optional[str] = None) -> HasOne:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        return HasOne(
            self, related_class, foreign_key=fk, local_key=local_key,
            name=name or self._calling_relation_name(),
        )

    def belongs_to(self, related_class: Type, foreign_key: Optional[str] = None,
                   owner_key: str = "id", name: Optional[str] = None) -> BelongsTo:
        fk = foreign_key or f"{related_class.__name__.lower()}_id"
        return BelongsTo(
            self, related_class, foreign_key=fk, owner_key=owner_key,
            name=name or self._calling_relation_name(),
        )

    def belongs_to_many(
        self,
        related_class: Type,
        pivot_table: Optional[str] = None,
        foreign_pivot_key: Optional[str] = None,
        related_pivot_key: Optional[str] = None,
        name: Optional[str] = None,
    ) -> BelongsToMany:
        this = self.__class__.__name__.lower()
        other = related_class.__name__.lower()
        # Convention: singular names joined alphabetically.
        pivot = pivot_table or "_".join(sorted([this, other]))
        return BelongsToMany(
            self,
            related_class,
            pivot_table=pivot,
            foreign_pivot_key=foreign_pivot_key or f"{this}_id",
            related_pivot_key=related_pivot_key or f"{other}_id",
            name=name or self._calling_relation_name(),
        )

    # RBAC lived here — `roles()`, `permissions()`, `has_role()`,
    # `has_permission()` — on the base every model inherits from, hardwired to
    # `role_user.user_id`. So `Post.find(1).roles()` returned the roles of
    # *user* 1: wrong data, no error. It also made the framework import
    # `app.Models.Role`, pointing the engine at the application.
    #
    # They now live on the models they describe: `roles`/`has_role`/
    # `has_permission` on `app/Models/User.py`, `permissions` on
    # `app/Models/Role.py`.
