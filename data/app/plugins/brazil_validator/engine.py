"""Pure Modulo 11 validation algorithms for CPF and CNPJ documents."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from app.plugins.brazil_validator.schemas import DocumentValidationResult


class DocumentValidatorEngine:
    """Stateless engine providing Modulo 11 validation for Brazilian documents."""

    @staticmethod
    def _extract_digits(value: str) -> str:
        return re.sub(r"\D", "", str(value or ""))

    @classmethod
    def validate_cpf(cls, value: str) -> DocumentValidationResult:
        """Validate a 11-digit CPF using standard Modulo 11 verification."""
        digits = cls._extract_digits(value)
        if len(digits) != 11 or len(set(digits)) == 1:
            return DocumentValidationResult(
                is_valid=False,
                document_type="CPF",
                formatted_document="",
                raw_digits=digits,
                error_message="CPF must contain 11 non-identical digits.",
            )

        # Validate first check digit
        factor = 10
        total = sum(int(digit) * (factor - i) for i, digit in enumerate(digits[:9]))
        remainder = (total * 10) % 11
        first_check = 0 if remainder == 10 else remainder

        if first_check != int(digits[9]):
            return DocumentValidationResult(
                is_valid=False,
                document_type="CPF",
                formatted_document="",
                raw_digits=digits,
                error_message="CPF first verification digit is invalid.",
            )

        # Validate second check digit
        factor = 11
        total = sum(int(digit) * (factor - i) for i, digit in enumerate(digits[:10]))
        remainder = (total * 10) % 11
        second_check = 0 if remainder == 10 else remainder

        if second_check != int(digits[10]):
            return DocumentValidationResult(
                is_valid=False,
                document_type="CPF",
                formatted_document="",
                raw_digits=digits,
                error_message="CPF second verification digit is invalid.",
            )

        formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return DocumentValidationResult(
            is_valid=True,
            document_type="CPF",
            formatted_document=formatted,
            raw_digits=digits,
        )

    @classmethod
    def validate_cnpj(cls, value: str) -> DocumentValidationResult:
        """Validate a 14-digit CNPJ using standard Modulo 11 verification."""
        digits = cls._extract_digits(value)
        if len(digits) != 14 or len(set(digits)) == 1:
            return DocumentValidationResult(
                is_valid=False,
                document_type="CNPJ",
                formatted_document="",
                raw_digits=digits,
                error_message="CNPJ must contain 14 non-identical digits.",
            )

        # Validate first check digit
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(d) * w for d, w in zip(digits[:12], weights1))
        remainder = total % 11
        first_check = 0 if remainder < 2 else 11 - remainder

        if first_check != int(digits[12]):
            return DocumentValidationResult(
                is_valid=False,
                document_type="CNPJ",
                formatted_document="",
                raw_digits=digits,
                error_message="CNPJ first verification digit is invalid.",
            )

        # Validate second check digit
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(d) * w for d, w in zip(digits[:13], weights2))
        remainder = total % 11
        second_check = 0 if remainder < 2 else 11 - remainder

        if second_check != int(digits[13]):
            return DocumentValidationResult(
                is_valid=False,
                document_type="CNPJ",
                formatted_document="",
                raw_digits=digits,
                error_message="CNPJ second verification digit is invalid.",
            )

        formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return DocumentValidationResult(
            is_valid=True,
            document_type="CNPJ",
            formatted_document=formatted,
            raw_digits=digits,
        )
