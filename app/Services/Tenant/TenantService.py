"""TenantService implementation for Codepy Framework."""

class TenantService:
    def get_active_tenants(self):
        return [
            {"id": 1, "name": "Acme Global Corporation"},
            {"id": 2, "name": "Beta Industries"},
            {"id": 3, "name": "Gamma Logistics"}
        ]
