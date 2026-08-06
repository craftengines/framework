"""Code generators backing the `craft make:*` commands."""

from __future__ import annotations

import os
import re
from typing import Dict, Optional, Tuple


def studly(value: str) -> str:
    parts = re.split(r"[_\-\s]+", value)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def snake(value: str) -> str:
    value = re.sub(r"[\-\s]+", "_", value)
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value)
    return re.sub(r"__+", "_", value).lower()


def plural(word: str) -> str:
    if word.endswith("y") and not word.endswith(("ay", "ey", "iy", "oy", "uy")):
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def table_for(model: str) -> str:
    return plural(snake(model))


# -- stubs ---------------------------------------------------------------------

def model_stub(name: str) -> str:
    return f'''"""{name} model."""

from codepy.orm.model import Model


class {name}(Model):
    __table__ = "{table_for(name)}"

    fillable = []
    hidden = []
'''


def controller_stub(name: str, resource: bool = False) -> str:
    if not resource:
        return f'''"""{name}."""

from codepy.http.controller import Controller


class {name}(Controller):
    async def index(self, request):
        return self.json({{"data": []}})
'''

    return f'''"""{name} — resource controller."""

from codepy.http.controller import Controller


class {name}(Controller):
    async def index(self, request):
        """GET / — list records."""
        return self.json({{"data": []}})

    async def show(self, request, id):
        """GET /{{id}} — show a single record."""
        return self.json({{"data": None}})

    async def store(self, request):
        """POST / — create a record."""
        return self.json({{"data": None}}, status=201)

    async def update(self, request, id):
        """PUT /{{id}} — update a record."""
        return self.json({{"data": None}})

    async def destroy(self, request, id):
        """DELETE /{{id}} — remove a record."""
        return self.json(None, status=204)
'''


def middleware_stub(name: str) -> str:
    return f'''"""{name} middleware."""


class {name}:
    async def handle(self, request, call_next):
        response = await call_next(request)
        return response
'''


def request_stub(name: str) -> str:
    return f'''"""{name} form request."""

from codepy.validation.form_request import FormRequest


class {name}(FormRequest):
    def authorize(self) -> bool:
        return True

    def rules(self) -> dict:
        return {{
            # "field": ["required", "string"],
        }}
'''


def resource_stub(name: str) -> str:
    return f'''"""{name} API resource."""

from codepy.resources import Resource


class {name}(Resource):
    def to_array(self, request=None) -> dict:
        return {{
            "id": self.resource.get_attribute("id"),
        }}
'''


def job_stub(name: str) -> str:
    return f'''"""{name} queued job."""

from codepy.queue import Job


class {name}(Job):
    def __init__(self, payload=None):
        self.payload = payload

    def handle(self):
        pass
'''


def event_stub(name: str) -> str:
    return f'''"""{name} event."""

from codepy.events.event import Event


class {name}(Event):
    def __init__(self, payload=None):
        self.payload = payload
'''


def listener_stub(name: str) -> str:
    return f'''"""{name} event listener."""


class {name}:
    def handle(self, event):
        pass
'''


def policy_stub(name: str) -> str:
    return f'''"""{name} authorization policy."""


class {name}:
    def view_any(self, user) -> bool:
        return True

    def view(self, user, model) -> bool:
        return True

    def create(self, user) -> bool:
        return True

    def update(self, user, model) -> bool:
        return True

    def delete(self, user, model) -> bool:
        return True
'''


def seeder_stub(name: str) -> str:
    return f'''"""{name}."""

from codepy.seeding import Seeder


class {name}(Seeder):
    def run(self):
        pass
'''


def factory_stub(name: str) -> str:
    model = name[:-7] if name.endswith("Factory") else name
    return f'''"""{name}."""

from codepy.factories import Factory
from faker import Faker


class {name}(Factory):
    model = None  # from app.Models.{model} import {model}

    def definition(self) -> dict:
        f = Faker()
        return {{}}
'''


def service_stub(name: str) -> str:
    return f'''"""{name}."""


class {name}:
    pass
'''


#: kind -> (stub builder, destination directory, filename suffix)
GENERATORS: Dict[str, Tuple] = {
    "model": (model_stub, os.path.join("app", "Models"), ""),
    "controller": (controller_stub, os.path.join("app", "Http", "Controllers"), "Controller"),
    "middleware": (middleware_stub, os.path.join("app", "Http", "Middleware"), "Middleware"),
    "request": (request_stub, os.path.join("app", "Http", "Requests"), "Request"),
    "resource": (resource_stub, os.path.join("app", "Http", "Resources"), "Resource"),
    "job": (job_stub, os.path.join("app", "Jobs"), ""),
    "event": (event_stub, os.path.join("app", "Events"), ""),
    "listener": (listener_stub, os.path.join("app", "Listeners"), ""),
    "policy": (policy_stub, os.path.join("app", "Policies"), "Policy"),
    "seeder": (seeder_stub, os.path.join("database", "seeders"), "Seeder"),
    "factory": (factory_stub, os.path.join("database", "factories"), "Factory"),
    "service": (service_stub, os.path.join("app", "Services"), "Service"),
}


def generate(kind: str, name: str, base_path: str, force: bool = False, **options) -> str:
    """Write a generated class file and return its path."""
    if kind not in GENERATORS:
        raise ValueError(f"Unknown generator [{kind}].")

    builder, directory, suffix = GENERATORS[kind]
    class_name = studly(name)
    if suffix and not class_name.endswith(suffix):
        class_name += suffix

    target_dir = os.path.join(base_path, directory)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f"{class_name}.py")

    if os.path.exists(path) and not force:
        raise FileExistsError(path)

    try:
        content = builder(class_name, **options)
    except TypeError:
        content = builder(class_name)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)

    init_path = os.path.join(target_dir, "__init__.py")
    if not os.path.exists(init_path) and directory.startswith(("app", "database")):
        open(init_path, "a", encoding="utf-8").close()

    return path


def generate_migration(
    name: str,
    base_path: str,
    table: Optional[str] = None,
    create: bool = True,
) -> str:
    """Write a timestamped migration file and return its path."""
    from services.migrations.migrator import make_migration_stub, migration_filename

    directory = os.path.join(base_path, "database", "migrations")
    os.makedirs(directory, exist_ok=True)

    file_name = migration_filename(snake(name))
    path = os.path.join(directory, file_name)

    inferred = table
    if inferred is None:
        match = re.match(r"^create_(\w+)_table$", snake(name))
        if match:
            inferred = match.group(1)
        else:
            match = re.match(r"^(?:add|update|alter)_.*_(?:to|in|on)_(\w+)_table$", snake(name))
            if match:
                inferred = match.group(1)
                create = False
        inferred = inferred or plural(snake(name))

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(make_migration_stub(snake(name), inferred, create))

    return path
