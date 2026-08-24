"""Optional backends must not be required to boot the framework.

CI proved this the hard way: `pip install -e "."` — a production install, no
dev extra — could not boot at all. `engine/ai/manager.py` imports the Gemini
and OpenAI drivers at module level, those imported `httpx` at module level, and
`httpx` is not a runtime dependency. Registering the AI service provider was
enough to raise `ModuleNotFoundError`.

Every other optional backend in the framework (boto3, redis, psycopg2, pymysql)
is imported inside the method that needs it, and raises with the package name
when it is missing. These tests hold the AI drivers to that same contract.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import builtins
import importlib
import sys

import pytest


def _reimport_without(module_name: str, target: str):
    """Import `target` with `module_name` unavailable, as a bare install is."""
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == module_name or name.startswith(f"{module_name}."):
            raise ImportError(f"No module named {module_name!r}")
        return real_import(name, *args, **kwargs)

    saved = {k: v for k, v in sys.modules.items() if k.startswith(target.split(".")[0])}
    for key in [k for k in sys.modules if k == target]:
        del sys.modules[key]

    builtins.__import__ = guarded
    try:
        return importlib.import_module(target)
    finally:
        builtins.__import__ = real_import
        sys.modules.update(saved)


@pytest.mark.parametrize("driver", [
    "engine.ai.drivers.gemini",
    "engine.ai.drivers.openai",
])
def test_an_ai_driver_imports_without_httpx(driver):
    """Importing the module is what boot does; it must not need the HTTP client."""
    module = _reimport_without("httpx", driver)
    assert module is not None


def test_the_ai_manager_imports_without_httpx():
    """The manager imports both drivers at module level — this is the path that
    made a production install unbootable."""
    assert _reimport_without("httpx", "engine.ai.manager") is not None


@pytest.mark.parametrize("driver,vendor", [
    ("engine.ai.drivers.gemini", "Gemini"),
    ("engine.ai.drivers.openai", "OpenAI"),
])
def test_the_failure_names_the_package_and_the_way_out(driver, vendor):
    """Deferring the import is only half of it: when it *is* needed and absent,
    the error has to say what to install."""
    module = importlib.import_module(driver)
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("No module named 'httpx'")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = guarded
    try:
        with pytest.raises(ImportError) as excinfo:
            module._httpx()
    finally:
        builtins.__import__ = real_import

    message = str(excinfo.value)
    assert "pip install httpx" in message
    assert vendor in message
    assert "mock" in message, "the error should point at the driver that needs nothing"


def test_httpx_is_declared_as_an_optional_extra():
    """It backs a driver, so it belongs beside redis and pymysql — not in the
    runtime dependencies, and not only in `dev` where the app cannot see it."""
    import os

    from bootstrap.app import app

    with open(os.path.join(app.base_path, "pyproject.toml"), encoding="utf-8") as handle:
        content = handle.read()

    extras = content.split("[project.optional-dependencies]", 1)[1]
    assert "ai = [" in extras
    assert "httpx" in extras.split("ai = [", 1)[1].split("]", 1)[0]


def test_the_mock_driver_needs_nothing_at_all():
    """What the error message tells people to fall back on has to actually work."""
    module = _reimport_without("httpx", "engine.ai.drivers.mock")
    assert hasattr(module, "MockAIDriver")
