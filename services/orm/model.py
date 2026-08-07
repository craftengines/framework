"""Base Model class for Craft ORM."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone

from services.orm.query_builder import QueryBuilder
from services.orm.relationships import (
    BelongsTo,
    BelongsToMany,
    HasMany,
    HasOne,
    Relation,
)


class Model:
    """Active Record Base Model."""

    __table__: Optional[str] = None
    fillable: List[str] = []
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

    def __init__(self, attributes: Optional[Dict[str, Any]] = None):
        self._attributes: Dict[str, Any] = attributes or {}
        #: Eager-loaded relations, keyed by relation method name.
        self._relations: Dict[str, Any] = {}

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
        import uuid

        return str(uuid.uuid4())

    @classmethod
    def has_uuid_column(cls) -> bool:
        """Whether the table declares the public UUID column.

        The answer is cached on the DatabaseManager, not here: a schema belongs
        to a connection, so swapping connections — a replica, a tenant schema, a
        test database — has to invalidate it. Caching per model class meant a
        swap left the wrong answer behind.
        """
        try:
            from services.container.application import Container

            db = Container.getInstance().make("db")
            return db.table_has_column(cls.get_table_name(), cls.uuid_column)
        except Exception:
            return False

    @classmethod
    def find_by_uuid(cls, value: str) -> Optional['Model']:
        return cls.query().where(cls.uuid_column, value).first()

    @classmethod
    def find_by_uuid_or_fail(cls, value: str) -> 'Model':
        from services.orm.exceptions import ModelNotFoundError

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
        """Resolve whatever `route_key()` produced, UUID or primary key."""
        if cls.uses_uuid and cls.has_uuid_column() and not str(value).isdigit():
            return cls.find_by_uuid(str(value))
        return cls.find(value)

    @classmethod
    def create(cls, attributes: Dict[str, Any]) -> 'Model':
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        clean_attrs = dict(cls.defaults)
        clean_attrs.update(attributes)
        clean_attrs.setdefault("created_at", now)
        clean_attrs.setdefault("updated_at", now)

        inst = cls(clean_attrs)

        from services.container.application import Container
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

        new_id = db.insert_get_id(cls.get_table_name(), clean_attrs, cls.primary_key)
        if new_id is not None:
            inst._attributes[cls.primary_key] = new_id
        elif cls.primary_key not in inst._attributes:
            import uuid

            inst._attributes[cls.primary_key] = str(uuid.uuid4())

        return inst

    def save(self) -> 'Model':
        """Insert or update this record."""
        from services.container.application import Container

        db = Container.getInstance().make("db")
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        key = self.primary_key

        if self._attributes.get(key) is None:
            created = self.__class__.create(dict(self._attributes))
            self._attributes = created._attributes
            return self

        self._attributes["updated_at"] = now
        updates = {k: v for k, v in self._attributes.items() if k != key}
        assignments = ", ".join(f"{column} = ?" for column in updates)
        db.statement(
            f"UPDATE {self.get_table_name()} SET {assignments} WHERE {key} = ?",
            list(updates.values()) + [self._attributes[key]],
        )
        return self

    def update(self, attributes: Dict[str, Any]) -> 'Model':
        self._attributes.update(attributes)
        return self.save()

    def delete(self) -> bool:
        from services.container.application import Container

        db = Container.getInstance().make("db")
        key = self.primary_key
        if self._attributes.get(key) is None:
            return False
        db.statement(
            f"DELETE FROM {self.get_table_name()} WHERE {key} = ?",
            [self._attributes[key]],
        )
        return True

    @classmethod
    def all(cls) -> Any:
        return cls.query().get()

    @classmethod
    def where(cls, column: str, operator_or_value: Any, value: Any = None) -> QueryBuilder:
        return cls.query().where(column, operator_or_value, value)

    @classmethod
    def with_(cls, *relations: str) -> QueryBuilder:
        """Start a query that eager loads the given relations."""
        return cls.query().with_(*relations)

    @classmethod
    def find_or_fail(cls, id_val: Any) -> 'Model':
        from services.orm.exceptions import ModelNotFoundError

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
        return cls.query().where("id", id_val).first()

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

    def roles(self) -> BelongsToMany:
        """Roles assigned to this user, through the `role_user` pivot."""
        from app.Models.Role import Role

        return BelongsToMany(
            self,
            Role,
            pivot_table="role_user",
            foreign_pivot_key="user_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def permissions(self) -> BelongsToMany:
        """Permissions granted to this role, through `permission_role`."""
        from app.Models.Permission import Permission

        return BelongsToMany(
            self,
            Permission,
            pivot_table="permission_role",
            foreign_pivot_key="role_id",
            related_pivot_key="permission_id",
            name="permissions",
        )

    def has_permission(self, slug: str) -> bool:
        from services.container.application import Container
        db = Container.getInstance().make("db")
        res = db.statement(
            """
            SELECT p.slug FROM permissions p
            JOIN permission_role pr ON p.id = pr.permission_id
            JOIN role_user ru ON pr.role_id = ru.role_id
            WHERE ru.user_id = ? AND p.slug = ?
            """,
            [self.get_attribute("id"), slug],
            read=True
        )
        return len(res.fetchall()) > 0
