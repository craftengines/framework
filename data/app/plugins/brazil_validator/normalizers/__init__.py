"""Brazilian standard format normalizers."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .cep import normalize_cep
from .phone import normalize_phone
from .address import normalize_address, normalize_street
from .cnae import normalize_cnae, normalize_cnae_list

__all__ = [
    "normalize_cep",
    "normalize_phone",
    "normalize_address",
    "normalize_street",
    "normalize_cnae",
    "normalize_cnae_list",
]
