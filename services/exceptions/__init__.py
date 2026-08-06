"""Exceptions exports."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.exceptions.handler import (
    CodepyException,
    NotFoundHttpException,
    AuthorizationException,
    ValidationException,
    ExceptionHandler,
)

# Aliases
HttpException = CodepyException
