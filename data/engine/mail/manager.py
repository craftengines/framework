"""Mail Manager and Fluent PendingMail for Craft Framework.

Category: Core Framework (Mail).
Relations:
  - Backs `craft.facades.Mail`.
  - Configured by `config/mail.py`.
References:
  - Guide: `documentation/mail.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from engine.mail.contracts import EmailMessage, MailDriver
from engine.mail.drivers.log import ArrayMailDriver, LogMailDriver
from engine.mail.drivers.smtp import SMTPDriver
from engine.mail.mailable import Mailable


class PendingMail:
    """Fluent pending mail builder returned by `Mail.to(...)`."""

    def __init__(self, manager: "MailManager", recipients: List[str]):
        self.manager = manager
        self.recipients = list(recipients)
        self._cc: List[str] = []
        self._bcc: List[str] = []

    def cc(self, *recipients: str) -> "PendingMail":
        self._cc.extend(recipients)
        return self

    def bcc(self, *recipients: str) -> "PendingMail":
        self._bcc.extend(recipients)
        return self

    def send(self, mailable: Union[Mailable, str], **kwargs: Any) -> bool:
        """Send a Mailable instance or view template to the pending recipients."""
        if isinstance(mailable, Mailable):
            mailable.to(*self.recipients)
            if self._cc:
                mailable.cc(*self._cc)
            if self._bcc:
                mailable.bcc(*self._bcc)
            return self.manager.send_mailable(mailable)

        # Direct template string
        template_name = str(mailable)
        subject = kwargs.get("subject", "Notification")
        data = kwargs.get("data", {})
        mail = Mailable().to(*self.recipients).with_subject(subject).view(template_name, data)
        return self.manager.send_mailable(mail)

    def raw(self, text: str, subject: str) -> bool:
        """Send raw text message."""
        mail = Mailable().to(*self.recipients).with_subject(subject).text(text)
        return self.manager.send_mailable(mail)

    def html(self, html_content: str, subject: str) -> bool:
        """Send raw HTML message."""
        mail = Mailable().to(*self.recipients).with_subject(subject).html(html_content)
        return self.manager.send_mailable(mail)


class MailManager:
    """Mail manager for email and notification delivery."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._mailers: Dict[str, MailDriver] = {}
        self._default_override: Optional[str] = None

    def _get_config(self) -> Dict[str, Any]:
        if self.app:
            try:
                cfg = self.app.make("config")
                return {
                    "default": cfg.get("mail.default", "log"),
                    "from": cfg.get("mail.from_address", {"address": "noreply@craftengine.dev", "name": "Craft Engine"}),
                    "mailers": cfg.get("mail.mailers", {}),
                }
            except Exception:
                pass
        return {
            "default": "log",
            "from": {"address": "noreply@craftengine.dev", "name": "Craft Engine"},
            "mailers": {"log": {"transport": "log"}, "array": {"transport": "array"}},
        }

    def mailer(self, name: Optional[str] = None) -> MailDriver:
        """Resolve a mail transport driver by name or default."""
        cfg = self._get_config()
        mailer_name = name or self._default_override or cfg.get("default", "log")

        if mailer_name in self._mailers:
            return self._mailers[mailer_name]

        mailer_cfg = cfg.get("mailers", {}).get(mailer_name, {})
        transport = mailer_cfg.get("transport", "log")

        if transport == "smtp":
            instance: MailDriver = SMTPDriver(mailer_cfg)
        elif transport == "array":
            instance = ArrayMailDriver(mailer_cfg)
        else:
            instance = LogMailDriver(mailer_cfg)

        self._mailers[mailer_name] = instance
        return instance

    def set_default_mailer(self, name: str) -> None:
        """Override the active default mailer."""
        self._default_override = name

    def set_mailer(self, name: str, driver: MailDriver) -> None:
        """Register a custom mailer driver."""
        self._mailers[name] = driver
        self._mailers[name] = driver

    def to(self, *recipients: str) -> PendingMail:
        """Start a fluent email chain: `Mail.to('user@example.com').send(...)`."""
        flat: List[str] = []
        for r in recipients:
            if isinstance(r, (list, tuple)):
                flat.extend(r)
            else:
                flat.append(str(r))
        return PendingMail(self, flat)

    def send_mailable(self, mailable: Mailable, mailer_name: Optional[str] = None) -> bool:
        """Render and send a Mailable."""
        cfg = self._get_config()
        default_from = cfg.get("from", {})
        message = mailable.to_email_message(default_from=default_from)
        return self.mailer(mailer_name).send(message)

    def send(self, mailable: Union[Mailable, str], to: Optional[Union[str, List[str]]] = None, subject: Optional[str] = None, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> bool:
        if isinstance(mailable, Mailable):
            if to:
                mailable.to(to if isinstance(to, list) else [to])
            if subject:
                mailable.with_subject(subject)
            return self.send_mailable(mailable)

        # String template
        recipients = to if isinstance(to, list) else ([to] if to else [])
        m = Mailable().to(*recipients).with_subject(subject or "Notification").view(mailable, data or {})
        return self.send_mailable(m)

    def raw(self, text: str, to: Union[str, List[str]], subject: str) -> bool:
        """Send raw plain-text email."""
        recipients = to if isinstance(to, list) else [to]
        m = Mailable().to(*recipients).with_subject(subject).text(text)
        return self.send_mailable(m)
