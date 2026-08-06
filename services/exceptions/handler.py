"""Exceptions and the HTTP exception handler for Codepy Framework."""

from __future__ import annotations

import traceback
from typing import Any, Optional


class CodepyException(Exception):
    status_code = 500


class NotFoundHttpException(CodepyException):
    status_code = 404


class AuthorizationException(CodepyException):
    status_code = 403


class ValidationException(CodepyException):
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
        if isinstance(exception, self.dont_report):
            return
        logger = self._logger()
        if logger is not None:
            logger.error("%s: %s", type(exception).__name__, exception, exc_info=exception)

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
    "CodepyException",
    "NotFoundHttpException",
    "AuthorizationException",
    "ValidationException",
    "ExceptionHandler",
]
