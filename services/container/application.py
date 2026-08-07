"""Service Container and Application bootstrap for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import inspect
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Type, Union

# Importing the package installs the `craft.*` -> `services.*` import alias.
import services  # noqa: F401


class Container:
    """Inversion-of-Control container supporting bindings, singletons, scoped instances and auto-resolution."""

    _instance: Optional['Container'] = None

    def __init__(self):
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        # Constructing a container deliberately does NOT claim the global
        # singleton. It used to, which meant building a second container
        # anywhere — a test fixture, a worker, a tenant-scoped app — silently
        # repointed every `Container.getInstance()` call in the process at it.
        # Claim it explicitly with `make_current()` or `scoped()`.

    @classmethod
    def getInstance(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    @classmethod
    def setInstance(cls, container: Optional['Container']) -> None:
        cls._instance = container

    def make_current(self) -> 'Container':
        """Make this container the one `getInstance()` returns."""
        Container._instance = self
        return self

    @classmethod
    @contextmanager
    def scoped_instance(cls, container: Optional['Container'] = None):
        """Temporarily swap the global container, restoring it on exit.

            with Container.scoped_instance(tenant_app):
                ...  # facades and models resolve from tenant_app

        Not to be confused with `scoped()`, which registers a request-scoped
        binding.
        """
        previous = cls._instance
        cls._instance = container
        try:
            yield container
        finally:
            cls._instance = previous

    def bind(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None, shared: bool = False) -> None:
        key = self._normalize_key(abstract)
        if concrete is None:
            concrete = key

        self._bindings[key] = {
            "concrete": concrete,
            "shared": shared,
        }

    def singleton(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None) -> None:
        self.bind(abstract, concrete, shared=True)

    def instance(self, abstract: Union[str, Type], instance: Any) -> None:
        key = self._normalize_key(abstract)
        self._instances[key] = instance

    def scoped(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None) -> None:
        key = self._normalize_key(abstract)
        self._bindings[key] = {
            "concrete": concrete or key,
            "shared": False,
            "scoped": True,
        }

    def alias(self, abstract: Union[str, Type], alias: str) -> None:
        key = self._normalize_key(abstract)
        self._aliases[alias] = key

    def make(self, abstract: Union[str, Type], parameters: Optional[Dict[str, Any]] = None) -> Any:
        key = self._normalize_key(abstract)

        # Resolve alias if present
        while key in self._aliases:
            key = self._aliases[key]

        # Return cached singleton instance
        if key in self._instances:
            return self._instances[key]

        # Return cached scoped instance
        if key in self._scoped_instances:
            return self._scoped_instances[key]

        binding = self._bindings.get(key)
        if binding:
            concrete = binding["concrete"]
            shared = binding.get("shared", False)
            is_scoped = binding.get("scoped", False)

            if callable(concrete) and not inspect.isclass(concrete):
                obj = concrete(self)
            elif isinstance(concrete, str):
                obj = self.make(concrete, parameters)
            elif inspect.isclass(concrete):
                obj = self._build(concrete, parameters)
            else:
                obj = concrete

            if shared:
                self._instances[key] = obj
            elif is_scoped:
                self._scoped_instances[key] = obj

            return obj

        # Attempt auto-resolution for un-bound classes
        if inspect.isclass(abstract):
            return self._build(abstract, parameters)
        elif isinstance(abstract, str):
            try:
                module_parts = abstract.rsplit(".", 1)
                if len(module_parts) == 2:
                    mod = __import__(module_parts[0], fromlist=[module_parts[1]])
                    cls = getattr(mod, module_parts[1])
                    if inspect.isclass(cls):
                        return self._build(cls, parameters)
            except Exception:
                pass

        raise KeyError(f"Target [{key}] is not bound in container and cannot be resolved.")

    def _build(self, concrete: Type, parameters: Optional[Dict[str, Any]] = None) -> Any:
        parameters = parameters or {}
        try:
            init_method = getattr(concrete, "__init__")
        except AttributeError:
            return concrete()

        if init_method is object.__init__:
            return concrete()

        signature = inspect.signature(init_method)
        args = []
        kwargs = {}

        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            if param_name in parameters:
                kwargs[param_name] = parameters[param_name]
                continue

            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation
                try:
                    kwargs[param_name] = self.make(param_type)
                    continue
                except Exception:
                    pass

            if param.default != inspect.Parameter.empty:
                kwargs[param_name] = param.default
            else:
                raise ValueError(f"Cannot resolve parameter [{param_name}] for class [{concrete.__name__}].")

        return concrete(*args, **kwargs)

    def _normalize_key(self, abstract: Union[str, Type]) -> str:
        if inspect.isclass(abstract):
            return f"{abstract.__module__}.{abstract.__qualname__}"
        return str(abstract)

    def forget_scoped_instances(self) -> None:
        self._scoped_instances.clear()


class Application(Container):
    """Application bootstrap class representing the core framework context."""

    def __init__(self, base_path: Optional[str] = None, bind_as_global: Optional[bool] = None):
        """Bootstrap an application.

        `bind_as_global` controls whether this application becomes the one
        `Container.getInstance()` returns:

        * ``None`` (default) — claim it unless another *Application* already
          holds it. The real application wins; a scratch application built
          later (test fixture, worker, tenant scope) leaves the global alone.
          A bare fallback `Container` — which `getInstance()` creates when
          something resolves the container before boot — is always displaced,
          otherwise it would permanently shadow the real app's bindings.
        * ``True`` / ``False`` — claim it, or never claim it.

        Use ``Container.scoped_instance(app)`` to swap the global one temporarily.
        """
        super().__init__()
        self.base_path = base_path or os.getcwd()
        self._providers: List[Any] = []
        self._booted = False

        if bind_as_global is None:
            bind_as_global = not isinstance(Container._instance, Application)
        if bind_as_global:
            self.make_current()

        # Register self as container instance
        self.instance("app", self)
        self.instance(Container, self)
        self.instance(Application, self)

    def load_environment(self, filename: str = ".env") -> None:
        """Load the project's `.env` file into the process environment."""
        from services.config.repository import load_dotenv

        load_dotenv(os.path.join(self.base_path, filename))

    def register_config(self) -> None:
        from services.config.repository import ConfigRepository

        # .env must be loaded before config modules read it via env().
        self.load_environment()
        config_repo = ConfigRepository(os.path.join(self.base_path, "config"))
        self.instance("config", config_repo)

    def register_provider(self, provider_class: Type) -> Any:
        provider = provider_class(self)
        if hasattr(provider, "register"):
            provider.register()
        self._providers.append(provider)
        if self._booted and hasattr(provider, "boot"):
            provider.boot()
        return provider

    def boot(self) -> None:
        if self._booted:
            return

        for provider in self._providers:
            if hasattr(provider, "boot"):
                provider.boot()

        self._booted = True
