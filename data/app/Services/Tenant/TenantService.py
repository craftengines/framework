"""TenantService implementation for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

class TenantService:
    def get_active_tenants(self):
        # Static demo data until multi-tenant routing (subdomain -> tenant
        # database) is implemented for real. Shape matches what
        # `resources/views/admin/dashboard.forge.py` renders.
        return [
            {
                "id": 1,
                "name": "Acme Global Corporation",
                "domain": "acme.craft.local",
                "db_engine": "pgsql",
                "status": "Active",
            },
            {
                "id": 2,
                "name": "Beta Industries",
                "domain": "beta.craft.local",
                "db_engine": "pgsql",
                "status": "Active",
            },
            {
                "id": 3,
                "name": "Gamma Logistics",
                "domain": "gamma.craft.local",
                "db_engine": "pgsql",
                "status": "Suspended",
            },
        ]
