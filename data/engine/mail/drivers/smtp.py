"""SMTP Mail Driver for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict

from engine.mail.contracts import EmailMessage


class SMTPDriver:
    """Standard SMTP email delivery driver."""

    def __init__(self, config: Dict[str, Any]):
        self.host = config.get("host", "127.0.0.1")
        self.port = int(config.get("port", 587))
        self.encryption = (config.get("encryption") or "").lower()
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.timeout = float(config.get("timeout", 30))

    def send(self, message: EmailMessage) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = formataddr((message.from_name or "", message.from_address or ""))
        msg["To"] = ", ".join(message.to)
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        for k, v in message.headers.items():
            msg[k] = v

        if message.body_text:
            msg.attach(MIMEText(message.body_text, "plain", "utf-8"))
        if message.body_html:
            msg.attach(MIMEText(message.body_html, "html", "utf-8"))

        for att in message.attachments:
            part = MIMEApplication(att["data"], Name=att["filename"])
            part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            msg.attach(part)

        all_recipients = list(message.to) + list(message.cc) + list(message.bcc)

        if self.encryption == "ssl" or self.port == 465:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            if self.encryption == "tls":
                server.starttls()

        try:
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(message.from_address or self.username, all_recipients, msg.as_string())
            return True
        finally:
            server.quit()
