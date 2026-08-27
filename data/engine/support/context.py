"""Per-request context that follows the work, not the thread.

A framework that serves requests on a thread pool cannot keep request-scoped
values in a global or in thread-local storage: a thread is reused by the next
request, and a value left behind is attributed to it. A `ContextVar` is copied
into whatever runs the work and restored on the way out, so the identifier a
log line carries is the identifier of the request that emitted it, even though
neither the logger nor the thread knows which one that is.

Category: Core Framework (Support).
Relations:
  - Populated by `RequestContext` middleware in `engine/http/middleware.py`.
  - Read by the log filter in `engine/support/logging.py` and by the exception
    handler in `engine/exceptions/handler.py`.
References:
  - Guide: `documentation/observability.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import contextlib
import re
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional

#: Everything known about the request being served, or an empty mapping
#: outside one. A single variable rather than one per field, so a task that
#: copies the context copies all of it, consistently.
_CONTEXT: ContextVar[Optional[Dict[str, Any]]] = ContextVar("craft_request_context", default=None)

#: An inbound identifier is echoed rather than replaced, so one request can be
#: followed across services - but it is not pasted into logs unchecked. A
#: header is attacker-controlled: an unbounded value bloats every log line it
#: touches, and a newline in one forges log entries.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

#: Checked before the pattern so a megabyte header is rejected by length
#: rather than by running a regex over it.
MAX_ID_LENGTH = 128


def new_request_id() -> str:
    """A fresh identifier for a request that arrived without one."""
    return uuid.uuid4().hex


def sanitize_request_id(value: Optional[str]) -> Optional[str]:
    """Accept an inbound identifier, or None if it cannot be trusted."""
    if not value or len(value) > MAX_ID_LENGTH:
        return None
    return value if _SAFE_ID.match(value) else None


def current() -> Dict[str, Any]:
    """Everything known about the request in flight. Never None."""
    ctx = _CONTEXT.get()
    return ctx if ctx is not None else {}


def get(key: str, default: Any = None) -> Any:
    return current().get(key, default)


def request_id() -> Optional[str]:
    """The identifier of the request in flight, or None outside one."""
    return get("request_id")


def put(**values: Any) -> None:
    """Add to the context of the request in flight.

    Replaces the mapping rather than mutating it: the previous mapping may be
    shared with a context this call has no business changing.
    """
    _CONTEXT.set({**current(), **values})


@contextlib.contextmanager
def bind(**values: Any) -> Iterator[Dict[str, Any]]:
    """Bind context for the duration of the block, then restore it.

    The reset is what makes a pooled thread safe to reuse: without it the next
    request served by this thread would inherit the previous one's identifier
    and every log line would name the wrong request.
    """
    token = _CONTEXT.set({**current(), **values})
    try:
        yield current()
    finally:
        _CONTEXT.reset(token)


def clear() -> None:
    """Drop the context entirely. For a worker between jobs."""
    _CONTEXT.set({})
