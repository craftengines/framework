"""DatabaseLoggingMiddleware for Codepy Framework."""

import logging

from services.http.middleware import Middleware
from app.Models.SystemLog import SystemLog


class DatabaseLoggingMiddleware(Middleware):
    """Records an entry in `system_logs` for every incoming request."""

    def handle(self, request, next_callable):
        try:
            SystemLog.create(
                {"message": f"Connection established: {request.method} {request.url.path}"}
            )
        except Exception:
            # Logging must never break the request — but it must be visible.
            logging.getLogger("codepy").warning(
                "DatabaseLoggingMiddleware could not write a system log.", exc_info=True
            )
        return next_callable(request)
