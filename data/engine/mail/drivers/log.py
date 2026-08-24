"""Log and Array/Memory Mail Drivers for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from engine.mail.contracts import EmailMessage


class LogMailDriver:
    """Mail driver that logs outgoing emails to the craft application logger."""

    def __init__(self, config: Dict[str, Any]):
        self.channel = config.get("channel", "craft")
        self.logger = logging.getLogger(self.channel)

    def send(self, message: EmailMessage) -> bool:
        self.logger.info(
            "----- OUTGOING EMAIL -----\n"
            "From: %s <%s>\n"
            "To: %s\n"
            "Subject: %s\n"
            "Body:\n%s\n"
            "--------------------------",
            message.from_name,
            message.from_address,
            ", ".join(message.to),
            message.subject,
            message.body_text or message.body_html,
        )
        return True


class ArrayMailDriver:
    """In-memory mail driver for fast deterministic testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.messages: List[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        self.messages.append(message)
        return True

    def flush(self) -> None:
        self.messages.clear()
