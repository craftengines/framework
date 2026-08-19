"""Craft Framework Mail Subsystem."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.mail.contracts import EmailMessage, MailDriver
from engine.mail.mailable import Mailable
from engine.mail.manager import MailManager, PendingMail

__all__ = [
    "EmailMessage",
    "MailDriver",
    "Mailable",
    "MailManager",
    "PendingMail",
]
