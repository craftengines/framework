"""Mail Contracts and Protocols for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Union


@dataclass
class EmailMessage:
    to: List[str]
    subject: str
    body_text: str = ""
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)


class MailDriver(Protocol):
    """Protocol for mail transport drivers."""

    def send(self, message: EmailMessage) -> bool:
        """Send an email message."""
        ...
