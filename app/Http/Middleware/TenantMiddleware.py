"""
TenantMiddleware — Dynamically routes incoming requests to isolated PostgreSQL schemas.
Category: Middleware (HTTP Pipeline Layer).
Relations:
  - Interacts with Auth and DB facades to bound schemas dynamically per request context.
  - Automatically migrates and sets up schema dependencies on first connection.
References:
  - Documentation: [documentation/orm.md](file:///d:/data/www/codepy/documentation/orm.md)
  - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
"""

import re
from codepy.http.middleware import Middleware
from codepy.facades import Auth, DB

class TenantMiddleware(Middleware):
    def handle(self, request, next):
        # Resolve user dynamically
        user = Auth.user()
        if user and user.get_attribute("type") == "tenant":
            # Determine schema name from user ID
            user_id = user.get_attribute("id")
            schema_name = f"tenant_{re.sub(r'[^a-zA-Z0-9_]', '_', str(user_id).lower())}"
            
            # Set and ensure tenant schema exists
            DB.set_tenant_schema(schema_name)
            DB.ensure_tenant_schema(schema_name, user)
        else:
            DB.set_tenant_schema(None)
            
        return next(request)
