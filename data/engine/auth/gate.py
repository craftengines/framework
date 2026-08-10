"""
GateManager — Ability closures and model Policies, denying by default.
Category: Core Framework (Auth).
Relations:
  - Bound as `gate`, exposed via the `Gate` facade; `allows`/`denies`/`check`
    take the user explicitly, `authorize` raises `AuthorizationException`.
References:
  - Guide: `documentation/security.md#authorization--gates-gate-facade`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Callable, Dict, Optional


class GateManager:
    """Resolution order, first answer wins:

    1. an ability closure registered with `define()`;
    2. a method of the Policy registered for the model being acted upon;
    3. the RBAC/ABAC grant tables, via the `access` resolver — the ability name
       doubles as a permission slug, and a grant's attribute conditions are
       evaluated against the resource;
    4. deny.

    Step 4 is the point: an ability nobody defined and no grant covers is a
    refusal. A Gate that returns True for what it does not recognise is worse
    than no Gate, because it looks like protection.
    """

    def __init__(self, app: Any = None):
        self.app = app
        self._abilities: Dict[str, Callable] = {}
        self._policies: Dict[Any, Any] = {}

    def _access(self) -> Any:
        """The `AccessResolver`, or None when no container is bound.

        Models are used in unit tests with no booted application, so this has
        to degrade — but it degrades to *denial* (`allows` falls through to
        False), never to a grant.
        """
        if self.app is None:
            return None
        try:
            return self.app.make("access")
        except Exception:
            return None

    def define(self, ability: str, callback: Callable) -> None:
        self._abilities[ability] = callback

    def policy(self, model_cls: Any, policy_cls: Any) -> None:
        self._policies[model_cls] = policy_cls

    def allows(self, ability: str, user: Any, *args) -> bool:
        if ability in self._abilities:
            return bool(self._abilities[ability](user, *args))

        # Fall back to a registered policy for the model being acted upon.
        if args:
            target = args[0]
            model_cls = target if isinstance(target, type) else type(target)
            policy_cls = self._policies.get(model_cls)
            if policy_cls is not None:
                method = getattr(policy_cls(), ability, None)
                if callable(method):
                    return bool(method(user, *args))

        # Fall back to the grant tables: a permission slug works as a Gate
        # ability without anyone registering a closure for it. The resource —
        # `args[0]`, when there is one — is passed through, so a grant narrowed
        # by attribute conditions ("only your own", "only under 10k") is
        # evaluated here rather than silently treated as unconditional.
        resource = args[0] if args else None
        access = self._access()
        if access is not None:
            try:
                if access.allows(user, ability, resource):
                    return True
            except Exception:
                # A failed authorization query is not a decision. Deny.
                pass
        else:
            # No container (unit tests, a model used standalone): honour a
            # model that answers for itself, and only unconditionally.
            has_permission = getattr(user, "has_permission", None)
            if callable(has_permission):
                try:
                    if has_permission(ability):
                        return True
                except Exception:
                    pass

        # Deny by default: an unknown ability must never grant access.
        return False

    def denies(self, ability: str, user: Any, *args) -> bool:
        return not self.allows(ability, user, *args)

    def check(self, ability: str, user: Any, *args) -> bool:
        return self.allows(ability, user, *args)

    def authorize(self, ability: str, user: Any, *args) -> None:
        """Raise instead of returning False — for use inside controllers."""
        if not self.allows(ability, user, *args):
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException(f"Unauthorized: {ability}")


# The real implementation lives in `engine.auth.manager`; re-exported here so
# existing `from craft.auth.gate import AuthManager` imports keep working.
from engine.auth.manager import AuthManager  # noqa: E402,F401
