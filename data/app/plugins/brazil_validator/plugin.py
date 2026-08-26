"""Brazil Document Validator Plugin — Native Capability Plugin Descriptor."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from app.plugins.brazil_validator.engine import DocumentValidatorEngine

PLUGIN = {
    "slug": "brazil_validator",
    "name": "Brazil Document Validator Plugin",
    "version": "1.0.0",
    "description": "Stateless Modulo 11 CPF and CNPJ document validation engine.",
}


def register(app):
    """Bind the DocumentValidatorEngine into the application IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("plugin.brazil_validator", lambda c: DocumentValidatorEngine())
