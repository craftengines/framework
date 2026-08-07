"""TenantService implementation for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

class TenantService:
    def get_active_tenants(self):
        return [
            {"id": 1, "name": "Acme Global Corporation"},
            {"id": 2, "name": "Beta Industries"},
            {"id": 3, "name": "Gamma Logistics"}
        ]
