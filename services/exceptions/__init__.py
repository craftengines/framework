"""Exceptions exports."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.exceptions.handler import (
    CraftException,
    NotFoundHttpException,
    AuthorizationException,
    ValidationException,
    ExceptionHandler,
)

# Aliases
HttpException = CraftException
