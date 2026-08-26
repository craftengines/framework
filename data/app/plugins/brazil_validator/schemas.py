"""Validation result DTOs for Brazilian document validator plugin."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentValidationResult:
    """Immutable result object representing document validation output."""

    is_valid: bool
    document_type: str
    formatted_document: str
    raw_digits: str
    error_message: Optional[str] = None
