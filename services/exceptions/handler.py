"""Exceptions and the HTTP exception handler for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import traceback
from typing import Any, Optional


class CraftException(Exception):
    status_code = 500


class NotFoundHttpException(CraftException):
    status_code = 404


class AuthorizationException(CraftException):
    status_code = 403


class ValidationException(CraftException):
    status_code = 422

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__("Validation failed")


class ExceptionHandler:
    """Converts exceptions into HTTP responses, honouring `app.debug`."""

    #: Exception types that should never be reported to the log.
    dont_report = (NotFoundHttpException,)

    def __init__(self, app: Any = None):
        self.app = app

    def should_report(self, exception: BaseException) -> bool:
        """Only server faults are worth a stack trace.

        A 404, a failed CSRF check or a validation error is the client getting
        it wrong — logging a full traceback for each one buries the real faults.
        """
        if isinstance(exception, self.dont_report):
            return False
        return self.status_for(exception) >= 500

    # -- configuration ---------------------------------------------------------

    def _debug(self) -> bool:
        if self.app is None:
            return False
        try:
            return bool(self.app.make("config").get("app.debug", False))
        except Exception:
            return False

    def _logger(self) -> Optional[Any]:
        if self.app is None:
            return None
        try:
            return self.app.make("log")
        except Exception:
            return None

    # -- handling --------------------------------------------------------------

    def report(self, exception: BaseException) -> None:
        logger = self._logger()
        if logger is None:
            return

        if self.should_report(exception):
            logger.error("%s: %s", type(exception).__name__, exception, exc_info=exception)
        else:
            logger.info(
                "%s (%s): %s",
                type(exception).__name__,
                self.status_for(exception),
                exception,
            )

    def status_for(self, exception: BaseException) -> int:
        return int(getattr(exception, "status_code", 500))

    def to_payload(self, exception: BaseException) -> dict:
        payload: dict = {
            "message": str(exception) or type(exception).__name__,
            "status": self.status_for(exception),
        }
        if isinstance(exception, ValidationException):
            payload["errors"] = exception.errors
        if self._debug():
            payload["exception"] = type(exception).__name__
            payload["trace"] = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        return payload

    def render(self, exception: BaseException, wants_json: bool = True) -> Any:
        """Build a Starlette response for the given exception."""
        self.report(exception)
        status = self.status_for(exception)
        payload = self.to_payload(exception)

        if wants_json:
            from starlette.responses import JSONResponse

            return JSONResponse(payload, status_code=status)

        from starlette.responses import HTMLResponse

        detail = ""
        if self._debug():
            detail = "<pre>" + "".join(payload.get("trace", [])) + "</pre>"
        return HTMLResponse(
            f"<h1>{status}</h1><p>{payload['message']}</p>{detail}", status_code=status
        )


__all__ = [
    "CraftException",
    "NotFoundHttpException",
    "AuthorizationException",
    "ValidationException",
    "ExceptionHandler",
]
