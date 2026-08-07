"""FormRequest for Craft Framework.

Subclass it to declare authorization and validation rules next to the endpoint
that needs them::

    class StorePostRequest(FormRequest):
        def authorize(self):
            return self.user() is not None

        def rules(self):
            return {"title": ["required", "string", "max:255"]}

    def store(self, request):
        data = StorePostRequest(request).validated()
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.validation.validator import Validator


class FormRequest:
    """Authorizes and validates an incoming request's input."""

    def __init__(self, request: Any = None):
        self.request = request
        self._validator: Optional[Validator] = None

    # -- to override -----------------------------------------------------------

    def authorize(self) -> bool:
        return True

    def rules(self) -> Dict[str, List[Any]]:
        return {}

    def messages(self) -> Dict[str, str]:
        return {}

    def prepare_for_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hook to normalise input before the rules run."""
        return data

    # -- input -----------------------------------------------------------------

    def data(self) -> Dict[str, Any]:
        """Every input on the request: query string plus parsed body."""
        request = self.request
        if request is None:
            return {}
        if isinstance(request, dict):
            return dict(request)
        if hasattr(request, "all"):
            try:
                return dict(request.all() or {})
            except Exception:
                return {}
        return {}

    def user(self) -> Any:
        if self.request is not None and hasattr(self.request, "user"):
            return self.request.user()
        return None

    # -- running ---------------------------------------------------------------

    def validator(self) -> Validator:
        if self._validator is None:
            data = self.prepare_for_validation(self.data())
            self._validator = Validator(data, self.rules(), self.messages())
        return self._validator

    @property
    def errors(self) -> Dict[str, List[str]]:
        return self.validator().errors

    def passes(self) -> bool:
        return self.authorize() and self.validator().passes()

    def fails(self) -> bool:
        return not self.passes()

    def validated(self) -> Dict[str, Any]:
        """Authorize, validate, and return only the fields that were ruled on.

        Raises `AuthorizationException` or `ValidationException`. This used to
        return the raw body without checking anything — every rule declared on a
        FormRequest was silently ignored.
        """
        if not self.authorize():
            from services.exceptions.handler import AuthorizationException

            raise AuthorizationException("This action is unauthorized.")

        return self.validator().validated()


__all__ = ["FormRequest"]
