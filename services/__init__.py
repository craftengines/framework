"""Codepy Framework Core Services Package.

The framework lives in `services/` but is imported publicly as `codepy.*`.
A meta path finder maps `codepy.<anything>` onto `services.<anything>` on
demand, so new subpackages are exposed automatically with no alias list to
keep in sync — and the unrelated third-party `codepy` package on PyPI can
never shadow the framework.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import os
import sys
from types import ModuleType
from typing import Optional, Sequence

__version__ = "0.1.0"

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

_ALIAS = "codepy"
_TARGET = __name__


class _AliasLoader(importlib.abc.Loader):
    """Loads `codepy.x.y` by importing `services.x.y` and re-exporting it."""

    def __init__(self, real_name: str):
        self.real_name = real_name

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> Optional[ModuleType]:
        return importlib.import_module(self.real_name)

    def exec_module(self, module: ModuleType) -> None:
        # The real module was already executed on import; nothing more to do.
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    """Resolves the `codepy` namespace to the `services` package."""

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]] = None,
        target: Optional[ModuleType] = None,
    ) -> Optional[importlib.machinery.ModuleSpec]:
        if fullname != _ALIAS and not fullname.startswith(_ALIAS + "."):
            return None

        real_name = _TARGET + fullname[len(_ALIAS):]
        try:
            importlib.import_module(real_name)
        except ImportError:
            return None

        spec = importlib.machinery.ModuleSpec(fullname, _AliasLoader(real_name))
        spec.submodule_search_locations = getattr(
            sys.modules[real_name], "__path__", None
        )
        return spec


def install_alias() -> None:
    """Register the `codepy` -> `services` import alias (idempotent)."""
    if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())
    sys.modules[_ALIAS] = sys.modules[_TARGET]


install_alias()
