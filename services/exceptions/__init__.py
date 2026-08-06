"""Exceptions exports."""

from services.exceptions.handler import (
    CodepyException,
    NotFoundHttpException,
    AuthorizationException,
    ValidationException,
    ExceptionHandler,
)

# Aliases
HttpException = CodepyException
