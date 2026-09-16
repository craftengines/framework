"""Structured log formatting and request correlation.

A log line that cannot be tied to the request that produced it is close to
useless once more than one instance is serving: the interleaved output of four
workers reads as noise, and the one line that explains an incident is
indistinguishable from the thousand around it. Every record therefore carries
the identifier of the request in flight, and the JSON formatter puts it in a
field a log platform can filter on rather than inside a sentence.

Category: Core Framework (Support).
Relations:
  - Installed by `LogServiceProvider` in `engine/providers/service_providers.py`.
  - Reads the request context set by `engine/support/context.py`.
References:
  - Guide: `documentation/observability.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from engine.support import context
from engine.support.redaction import redact_message, redact_structure

#: Attributes `logging` puts on every record. Anything else was passed by the
#: caller through `extra=` and is worth carrying into the payload.
_RESERVED = frozenset(
    """args asctime created exc_info exc_text filename funcName levelname levelno
    lineno module msecs message msg name pathname process processName
    relativeCreated stack_info thread threadName taskName""".split()
)

#: Fields promoted to the top level of the payload when present in the request
#: context, in the order a reader scans for them.
_PROMOTED = ("request_id", "method", "path", "status", "duration_ms", "user_id")


class RequestContextFilter(logging.Filter):
    """Attach the request context to every record passing through.

    A filter rather than a formatter concern, so the values are on the record
    itself and a project that swaps in its own formatter keeps them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in context.current().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request context as real fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_message(record.getMessage()),
        }

        for key in _PROMOTED:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = redact_structure({key: value})[key]

        for key, value in record.__dict__.items():
            if key in _RESERVED or key in payload or key.startswith("_"):
                continue
            # Redacted by key name first (a field literally called `password`
            # is dropped outright) and by value shape second (a bearer token
            # or card-number-shaped string inside a field with an innocuous
            # name is still caught) - wrapping in a single-key dict reuses
            # redact_structure's key-name check for this one field/value pair.
            payload[key] = redact_structure({key: value})[key]

        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": redact_message(str(record.exc_info[1])) if record.exc_info[1] else None,
                "stack": redact_message(self.formatException(record.exc_info)),
            }

        # `default=str` rather than dropping what will not serialise: a UUID or
        # a datetime passed through `extra=` is exactly the kind of value worth
        # having, and losing the whole line over it would be the wrong trade.
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """The human-readable format, with the request id when there is one."""

    DEFAULT_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        line = redact_message(super().format(record))
        identifier = getattr(record, "request_id", None)
        return f"{line} [request_id={identifier}]" if identifier else line


def formatter_for(name: str) -> logging.Formatter:
    """Build the formatter named in the channel config."""
    if str(name).lower() == "json":
        return JsonFormatter()
    return TextFormatter(TextFormatter.DEFAULT_FORMAT)
