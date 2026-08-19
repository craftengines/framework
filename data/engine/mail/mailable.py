"""Mailable Base Class for Craft Framework.

Category: Core Framework (Mail).
Relations:
  - Dispatched via `craft.facades.Mail.send(mailable)`.
  - Renders Forge views when template is specified.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional
from engine.mail.contracts import EmailMessage


class Mailable:
    """Base class for declarative, template-driven email notifications."""

    subject: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None

    def __init__(self):
        self._to: List[str] = []
        self._cc: List[str] = []
        self._bcc: List[str] = []
        self._subject: Optional[str] = None
        self._view_template: Optional[str] = None
        self._view_data: Dict[str, Any] = {}
        self._raw_html: Optional[str] = None
        self._raw_text: Optional[str] = None
        self._attachments: List[Dict[str, Any]] = []

    def to(self, *recipients: str) -> "Mailable":
        for r in recipients:
            if isinstance(r, (list, tuple)):
                self._to.extend(r)
            else:
                self._to.append(str(r))
        return self

    def cc(self, *recipients: str) -> "Mailable":
        for r in recipients:
            self._cc.append(str(r))
        return self

    def bcc(self, *recipients: str) -> "Mailable":
        self._bcc.extend(recipients)
        return self

    def with_subject(self, subject: str) -> "Mailable":
        self._subject = subject
        return self

    def view(self, template: str, data: Optional[Dict[str, Any]] = None) -> "Mailable":
        self._view_template = template
        self._view_data = data or {}
        return self

    def html(self, html_content: str) -> "Mailable":
        self._raw_html = html_content
        return self

    def text(self, text_content: str) -> "Mailable":
        self._raw_text = text_content
        return self

    def attach(self, filename: str, data: bytes, mime_type: Optional[str] = None) -> "Mailable":
        self._attachments.append({
            "filename": filename,
            "data": data,
            "mime_type": mime_type or "application/octet-stream",
        })
        return self

    def build(self) -> "Mailable":
        """Hook for subclasses to configure the message."""
        return self

    def to_email_message(self, default_from: Optional[Dict[str, str]] = None) -> EmailMessage:
        self.build()

        from_addr = self.from_address or (default_from.get("address") if default_from else "noreply@craftengine.dev")
        from_n = self.from_name or (default_from.get("name") if default_from else "Craft Engine")
        subj = self._subject or self.subject or "Notification from Craft Engine"

        html_body = self._raw_html
        if not html_body and self._view_template:
            from engine.facades import View
            try:
                html_body = View.make(self._view_template, self._view_data).render()
            except Exception:
                html_body = f"<html><body><p>{self._view_template}</p></body></html>"

        text_body = self._raw_text or (html_body or "")

        return EmailMessage(
            to=list(self._to),
            subject=subj,
            body_text=text_body,
            body_html=html_body,
            from_address=from_addr,
            from_name=from_n,
            cc=list(self._cc),
            bcc=list(self._bcc),
            attachments=list(self._attachments),
        )
